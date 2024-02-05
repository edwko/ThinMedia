from index.tmdb import TMDB
from index.base import DB
from index.log import LOG
import glob
from guessit import guessit
from rapidfuzz import process, fuzz
import os, json
import threading 

class Indexer:
    def __init__(self) -> None:
        self.data_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
        self.config = self.load_config()
        self.use = self.config['indexer']
        self.media_extensions = ['.mp4', '.mkv', '.avi']
        self.tmdb = TMDB("", int(self.config["img_s"]), self.config["use_episode_img"])
        self.init_tmdb(self.config["tmdb_api_key"])
        self.lock = threading.Lock()
        self.is_running_awc = False
        self.is_running_rescan = False

    def init_tmdb(self, api_key) -> bool:
        self.tmdb.api_key = api_key
        if not self.tmdb.check_api_key(): 
            LOG.log("Invalid TMDB API Key, terminating application.", True)
            LOG.log(f"Check: {os.path.join(self.data_dir, 'indexer_config.json')}", True)
            exit(0)
        LOG.log("Connected to TMDB API successfully.", True)

    def load_config(self):
        try:
            with open(os.path.join(self.data_dir, 'indexer_config.json'), 'r') as f:
                return json.load(f)
        except: 
            LOG.log("Error loading config, terminating application.", True)
            LOG.log(f"Check: {os.path.join(self.data_dir, 'indexer_config.json')}", True)
            exit(0)

    def extract_title(self, title: str):
        parsed_title = guessit(title)
        
        if not parsed_title: 
            return []

        components = []
        if "title" in parsed_title: 
            components.append(parsed_title["title"])
        if "episode_title" in parsed_title: 
            components.append(parsed_title["episode_title"])

        return components

    def search_tmdb(self, search_title: str, min_match: int = 75):
        for title in self.extract_title(search_title):
            data = self.tmdb.search(title)
            if not data: 
                LOG.verbose(f"Could not find media: {title}")
                return None

            search_result = None
            for i in data["results"]:
                result_title = i["title"] if "title" in i else i["name"]
                match = fuzz.ratio(title.lower(), result_title.lower())
                if match >= min_match:
                    search_result = i
                    LOG.verbose(f"Matched media: {title} and {result_title} with {match}%")
                    break
                else:
                    LOG.verbose(f"Match % for {title} and {result_title} is too low: {match}% < {min_match}%")

            if not search_result: 
                LOG.verbose(f"Could not match media: {title}")
                continue

            LOG.verbose(f"Matched media: {title} to {search_result}")
            return search_result
        return None

    def create_tmdb_data(self, data):
        if data["media_type"] == "movie":
            return self.tmdb.create_movie_data(data["id"])
        return self.tmdb.create_tv_data(data["id"])

    def search(self, title: str):
        if self.use == "tmdb": 
            return self.search_tmdb(title)
    
    def is_media_file(self, file_path) -> bool:
        return any(file_path.lower().endswith(ext) for ext in self.media_extensions)

    def get_all_file_paths(self, folder_path) -> list[str]:
        file_paths = []
        for folder_name, _, filenames in os.walk(folder_path):
            for filename in filenames:
                file_path = os.path.join(folder_name, filename)
                if self.is_media_file(file_path):
                    file_paths.append(file_path)
        return file_paths

    def get_base_folder(self, file_path: str, base: str):
        return file_path.replace(base, "").split("/")[0]

    def get_base_paths(self, path):
        all_files = self.get_all_file_paths(path)
        return {self.get_base_folder(f, path): path for f in all_files}

    def _map_file_guess(file: str, is_key_int: bool):
        file_data = guessit(os.path.basename(file))
        if "season" not in file_data or "episode" not in file_data: 
            return "", ""
        if is_key_int:
            return file_data["season"], file_data["episode"]
        return str(file_data["season"]), str(file_data["episode"])

    def map_files(self, base: str, season: dict, media_type: str):
        files = self.get_all_file_paths(base)
        if media_type == "movie":
            for f in files:
                if self.is_media_file(f):
                    return {0: {0: f}}

        is_key_int = isinstance(list(season.keys())[0], int)

        file_map = {}
        for i in files:
            if not self.is_media_file(i): 
                continue
            
            file_season, file_episode = self._map_file_guess(i, is_key_int)

            if file_season not in season: 
                continue 
            if file_episode not in season[file_season]: 
                continue
            if file_season not in file_map: 
                file_map[file_season] = {}

            file_map[file_season][file_episode] = i

        return file_map

    def scan_and_index_current_media(self):
        with self.lock:
            if self.is_running_rescan:
                LOG.verbose("Rescan is running, exiting.")
                return None
            self.is_running_rescan = True

        get_all = DB.get_all_sql()
        if get_all:
            for i in get_all:
                yield f"Indexing: {i.title}"
                DB.update_file_map(i.title, self.map_files(i.files_base_folder, i.episodes, i.media_type))
                LOG.verbose(f"Updated file map for: {i.title}")

        with self.lock:
            self.is_running_rescan = False

    def update_media_by_indexer_id(self, media_type: str, indexer_id: str, media_path: str):
        media_data = DB.get_media_by_path(media_path)
        if not media_data: 
            return ""

        s = self.create_tmdb_data({"id": indexer_id, "media_type": media_type})
        if not s: 
            return ""

        media, seasons, img = s
        DB.update_media_data(
            media_data.id, media["type"], media["title"],
            media, seasons, self.map_files(media_path, seasons, media["type"]), img)

        LOG.verbose(f"Updated media from {media_data.title} to {media['title']}.")

        return media["title"]

    def get_matches(self, mapped: dict):
        for i in self.config['paths']:
            paths = self.get_base_paths(i)
            for p in paths:
                path = paths[p]+p
                if path not in mapped:
                    LOG.verbose(f"Indexing - folder: {p} path: {paths[p]}")
                    media = DB.get_media_by_path(path) 
                    if not media:
                        data = self.search_tmdb(p)
                        if not data: 
                            mapped[path] = None
                        else: 
                            mapped[path] = data
                    else:
                        LOG.verbose(f"Media already exists: {media.title}.")
        return mapped

    def index_media_awc(self, matches: dict):
        with self.lock:
            if self.is_running_awc: 
                LOG.verbose(f"Indexer is running, exiting.")
                return None
            self.is_running_awc = True

        for i in matches:
            s = None
            at = matches[i]

            if at["id"] and at["id_type"]:
                s = self.create_tmdb_data({"id": at["id"], "media_type": at["id_type"]})
            elif at["data"]:
                s = self.create_tmdb_data({"id": at["data"]["id"], "media_type": at["data"]["media_type"]})
            
            if not s: 
                LOG.verbose(f"Could not create media: {i}")
                continue

            media, seasons, img = s

            DB.create_and_add_media(
                media_type=media["type"], title=media["title"],
                media_data=media, episodes=seasons, 
                file_map=self.map_files(i, seasons, media["type"]), 
                img_map=img, files_base_folder=i)

            LOG.verbose(f"Added media: {media['title']}")

        with self.lock:
            self.is_running_awc = False

manager = Indexer()