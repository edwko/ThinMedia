from sqlalchemy import Column, Integer, String, Text, JSON, create_engine
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
import os, json, re
from natsort import natsorted
from rapidfuzz import process 

DECBASE = declarative_base()

class Media(DECBASE):
    """
    Media class represents the media table in the database.
    It contains information about different types of media.
    """

    __tablename__ = 'media' 

    id = Column(Integer, primary_key=True)
    media_type = Column(String, nullable=False)
    title = Column(String, nullable=False)

    # Media data contains title, year, vote, vote count, info, type and genres
    media_data = Column(JSON, nullable=False)

    # Episodes contains season number and episode details
    episodes = Column(JSON, nullable=False)

    # Files base folder and file map for media files
    files_base_folder = Column(String, nullable=False)
    file_map = Column(JSON, nullable=False)

    # Image map contains base, header and seasons images
    img_map = Column(JSON, nullable=False)

class Base:
    def __init__(self) -> None:
        self.engine = create_engine(
                'sqlite:///' + os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                    'data', 'media.db'))
        DECBASE.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.sco = scoped_session(self.Session)
        self.media_type_map = {0: "all", 1: "tv", 2: "movie"}

    def to_json(self, item: dict) -> dict:
        return json.loads(json.dumps(item))

    def get_all(self) -> dict:
        with self.sco() as session:
            all_media = session.query(Media).all()
            if all_media:
                d = {i.title: i for i in all_media}
                return {i: d[i] for i in natsorted(list(d.keys()))}
            return {}

    def get_all_sql(self) -> list[Media]:
        with self.sco() as session:
            return session.query(Media).all()

    def search(self, search: str, data: dict) -> dict:
        search = search.lower()
        r = {k.lower(): k for k in list(data.keys())}
        res = [r[i[0]] for i in process.extract(search, list(r.keys()), limit=20) if i[1] > 40]
        return {i: data[i] for i in res}

    def apply_filters(self, data: dict, search: str, genres: list[str], media_type: str):
        if media_type != "all":
            data = {i: data[i] for i in data if data[i].media_type == media_type}
        if search:
            data = self.search(search, data)
        if genres:
            data = {i: data[i] for i in data if any(g in data[i].media_data["genres"] for g in genres)}
        return data

    def get_unique_genres(self) -> list:
        genres = set()
        data = self.get_all_sql()
        for i in data:
            for g in i.media_data["genres"]: genres.add(g)
        return natsorted(list(genres))

    def get_media(self, title: str) -> Media:
            with self.sco() as session:
                return session.query(Media).filter_by(title=title).first()

    def get_media_by_path(self, path: str) -> Media:
        with self.sco() as session:
            return session.query(Media).filter_by(files_base_folder=path).first()

    def get_media_by_id(self, id: int) -> Media:
        with self.sco() as session:
            return session.query(Media).filter_by(id=id).first()

    def update_file_map(self, title: str, file_map: dict):
        with self.sco() as session:
            media = session.query(Media).filter_by(title=title).first()
            media.file_map = self.to_json(file_map)
            session.commit()
    
    def add_media(self, media: Media):
        with self.sco() as session:
            if not self.get_media(media.title):
                session.add(media)
                session.commit()

    def create_and_add_media(self, media_type: str, title: str, media_data: dict, 
            episodes: dict, file_map: dict, img_map: dict, files_base_folder: str):
        self.add_media(Media(
            media_type=media_type, title=title, media_data=media_data, 
            episodes=episodes, file_map=file_map, img_map=img_map, 
            files_base_folder=files_base_folder))

    def update_media_data(self, db_id: int, media_type: str, title: str, media_data: dict, 
            episodes: dict, file_map: dict, img_map: dict):
        with self.sco() as session:
            data = session.query(Media).filter_by(id=db_id).first()
            data.media_type = media_type
            data.title = title
            data.media_data = media_data
            data.episodes = episodes
            data.file_map = file_map
            data.img_map = img_map
            session.commit()

    def clean_title(self, title):
        return " ".join(re.sub(r'[^\w\s]', '', title).split())

    def create_media_data_dict(self, title: str, year: int, vote: float, 
            vote_count: int, info: str, media_type: str, genres: list) -> dict:
        return {
            'title': title, 
            'clean_title': self.clean_title(title), 
            'year': year, 
            'vote': vote, 
            'vote_count': vote_count, 
            'info': info, 
            'type': media_type, 
            'genres': genres
        }

    def create_episodes_dict(self, season: int, episode: int, title: str, info: str) -> dict:
        return {'season': season, 'episode': episode, 'title': title, 'info': info}

    def create_base_img_dict(self, base: str, header: str) -> dict:
        return {'base': base, 'header': header}

    def get_media_type(self, media_type: int):
        return self.media_type_map[media_type]

DB = Base()