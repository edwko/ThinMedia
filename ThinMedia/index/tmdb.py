import requests
import threading
import time
import re
import multiprocessing
import os
from index.log import LOG
from PIL import Image
from io import BytesIO
from index.base import DB
from dateutil.parser import parse

class TMDB:
    def __init__(self, api_key: str, img_s: int, use_episode_img: bool) -> None:
        self.use_episode_img = use_episode_img
        self.api_valid = False
        self.api_key = api_key
        self.max_tokens = 30
        self.img_s = img_s
        self.tokens = self.max_tokens
        self.lock = threading.Lock()
        self.lock_condition = threading.Condition(self.lock)
        self.base = "https://api.themoviedb.org/3/"
        threading.Thread(target=self.token_limiter, daemon=True).start()

    def token_limiter(self):
        while True:
            with self.lock:
                self.tokens = self.max_tokens
                self.lock_condition.notify_all()
            time.sleep(1)

    def consume_token(self, size):
        with self.lock:
            while self.tokens < size:
                self.lock_condition.wait()
            self.tokens -= size

    def run_tasks(self, func, args: list):
        num_cpus = multiprocessing.cpu_count() 
        tasks = []
        for i in args:
            f = threading.Thread(target=func, args=tuple(i))
            f.start()
            tasks.append(f)
            if len(tasks) >= num_cpus:
                for t in tasks: t.join()
                tasks = []
        if tasks:
            for t in tasks: t.join()

    def _process_image(self, img_data: bytes, s: int) -> Image:
        img = Image.open(BytesIO(img_data))
        width, height = img.size
        new_width = int(s * width / height)
        return img.resize((new_width, s))
        
    def download_image(self, link, save_path, s):
        if not link or link == "None": 
            LOG.verbose(f"Image link is None: {link}")
            return 1
        
        url = f"https://image.tmdb.org/t/p/original{link}"
        self.consume_token(1)

        response = requests.get(url)
        if response.status_code != 200:
            LOG.verbose(f"Image download failed: {url}")
            return 1

        img = self._process_image(response.content, s)
        img.save(save_path)  
            
        LOG.verbose(f"Image saved: {save_path}")

        return 0
    
    def get(self, url: str, headers: dict = {}):
        self.consume_token(1)
        response = requests.get(url, headers=headers)
        if response.status_code == 200: 
            return response.json()
        return None
    
    def search(self, name):
        url = f"{self.base}search/multi?include_adult=true&page=1"
        url += f"&query={name}&api_key={self.api_key}"
        return self.get(url, {"accept": "application/json"})

    def get_movie_data(self, id):
        return self.get(f"{self.base}movie/{id}?api_key={self.api_key}")
    
    def get_tv_data(self, id):
        return self.get(f"{self.base}tv/{id}?api_key={self.api_key}")

    def get_season_data(self, id: str, season: int):
        return self.get(f"{self.base}tv/{id}/season/{season}?api_key={self.api_key}")
    
    def get_year(self, date):
        try: return parse(date).year
        except: return 0

    def create_img_path(self, title, dir, img, img_type='jpg'):
        dir_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "img", title, dir)
        os.makedirs(dir_path, exist_ok=True)
        return os.path.join(dir_path, f"{img}.{img_type}")

    def create_movie_data(self, id):
        base = self.get_movie_data(id)
        if not base: 
            return None

        media = DB.create_media_data_dict(
            title = base['title'], 
            year = self.get_year(base['release_date']),
            vote = round(base['vote_average'], 1), 
            vote_count = base['vote_count'],
            info = base['overview'], 
            genres = [i['name'] for i in base['genres']],
            media_type = "movie"
        )
        episode = DB.create_episodes_dict(
            season=0, episode=0, title=base['title'], info=base['overview']
        )

        seasons = {0: {0: episode}}

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if base["backdrop_path"] and base["backdrop_path"] != "None":
            img_path = self.create_img_path(media['clean_title'], 'base', 'base')
            self.download_image(base["backdrop_path"], img_path, self.img_s)
            img = DB.create_base_img_dict(base=img_path.replace(base_dir, ""), header=None)        
            img['seasons'] = {0: {0: img_path.replace(base_dir, "")}}
        else:
            img['seasons'] = {0: {0: ""}}

        return media, seasons, img

    def create_tv_data(self, id):
        base = self.get_tv_data(id)
        if not base: 
            return None
        
        media = DB.create_media_data_dict(
            title = base['name'], 
            year = self.get_year(base['first_air_date']),
            vote = round(base['vote_average'],1), 
            vote_count = base['vote_count'],
            info = base['overview'], 
            genres = [i['name'] for i in base['genres']],
            media_type = "tv")
        
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if base["backdrop_path"] and base["backdrop_path"] != "None":
            img_path = self.create_img_path(media['clean_title'], 'base', 'base')
            self.download_image(base["backdrop_path"], img_path, self.img_s)
            img = DB.create_base_img_dict(base=img_path.replace(base_dir, ""), header=None)     
        else:
            img = DB.create_base_img_dict(base="", header=None)     

        img["seasons"] = {}
        
        seasons, tasks = {}, []
        for i in base['seasons']:
            season_number = i['season_number']
            img['seasons'][season_number] = {}
                
            seasons[season_number] = {}
            season_data = self.get_season_data(id, season_number)
            if not season_data: 
                continue
            
            for ep in season_data['episodes']:
                ep_number = ep['episode_number']
                seasons[season_number][ep_number] = DB.create_episodes_dict(
                    season=season_number, episode=ep_number,
                    title=ep['name'], info=ep['overview'])

                if ep['still_path'] and ep['still_path'] != "None" and self.use_episode_img:
                    img_path = self.create_img_path(
                        media['clean_title'], f"S{season_number}E{ep_number}", "base")
                    tasks.append([ep['still_path'], img_path, self.img_s])
                    img['seasons'][season_number][ep_number] = img_path.replace(base_dir, "")
                else:
                    img['seasons'][season_number][ep_number] = ""

        if tasks:
            self.run_tasks(self.download_image, tasks)

        return media, seasons, img
            
    def check_api_key(self):
        req = self.get("https://api.themoviedb.org/3/authentication?api_key="+self.api_key)
        if req:
            if req["success"]: 
                self.api_valid = True
        return self.api_valid
