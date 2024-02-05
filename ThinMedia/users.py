from sqlalchemy import create_engine, Column, Integer, String, JSON, Boolean
from sqlalchemy.orm import sessionmaker, scoped_session, declarative_base
from hashlib import sha512
import random
import string
import uuid
import os
import json
import time

UserBase = declarative_base()
WatchBase = declarative_base()

class WatchInfo(WatchBase):
    __tablename__ = "watch_info"

    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=False)
    last_watched = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    season = Column(Integer, nullable=False)
    episode = Column(Integer, nullable=False)
    watched = Column(Boolean, nullable=False)
    playback = Column(Integer, nullable=False)

class UserData(UserBase):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    password = Column(String, nullable=False)
    api = Column(String, nullable=False)
    role = Column(String, nullable=False)

    mapped = Column(JSON, nullable=False)

class Users:
    def __init__(self) -> None:
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.engine = create_engine(
            'sqlite:///' + os.path.join(self.base_dir, 'data', 'users.db'))
        UserBase.metadata.create_all(self.engine)
        self.maker = sessionmaker(bind=self.engine)
        self.sco = scoped_session(self.maker)

    def to_json(self, n: dict):
        return json.loads(json.dumps(n))

    def update_mapped(self, name: str, data: dict) -> None:
        with self.sco() as session:
            user = session.query(UserData).filter(UserData.name == name).first()
            user.mapped = data
            session.commit()

    def get_mapped(self, name: str) -> dict:
        with self.sco() as session:
            user = session.query(UserData).filter(UserData.name == name).first()
            return user.mapped

    def generate_random_string(self, length):
        letters = string.ascii_lowercase + string.digits
        result_str = ''.join(random.choice(letters) for i in range(length))
        return result_str
    
    def create_api_key(self) -> str:
        return uuid.uuid4().hex.lower() + self.generate_random_string(32)
        
    def add(self, name: str, password: str, role: str) -> None:
        new = UserData(
            name = name, 
            password = sha512(password.encode("utf-8")).hexdigest().lower(),
            api = self.create_api_key(),
            role = role, mapped = {}
        )

        with self.sco() as session:
            session.add(new)
            session.commit()

    def get_json(self, name: str):
        with self.sco() as session:
            user = session.query(UserData).filter(UserData.name == name).first()
            return {'user': user.name, 'password': user.password, 'api': user.api, 'role': user.role}

    def get_json_api(self, api: str):
        with self.sco() as session:
            user = session.query(UserData).filter(UserData.api == api).first()
            if not user: 
                return None
            return {'user': user.name, 'password': user.password, 'api': user.api, 'role': user.role}

    def get_all(self):
        with self.sco() as session:
            return session.query(UserData).all()

    def get_all_map(self) -> dict:
        with self.sco() as session:
            all = session.query(UserData).all()
            return {i.name: i for i in all}

    def get(self, name: str) -> UserData:
        with self.sco() as session:
            return session.query(UserData).filter(UserData.name == name).first()

    def login(self, name: str, password: str) -> bool:
        user = self.get_json(name)
        if user:
            password = sha512(password.encode("utf-8")).hexdigest().lower()
            if user['password'] == password:
                return True
        return False

    def change_api(self, name) -> None:
        with self.sco() as session:
            data = session.query(UserData).filter(UserData.name == name).first()
            data.api = self.create_api_key()
            session.commit()

    def user_size(self):
        with self.sco() as session:
            return session.query(UserData).count()

class WatchInfoManager:
    def __init__(self) -> None:
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.engine = create_engine(
            'sqlite:///' + os.path.join(self.base_dir, 'data', 'watch_info.db'))
        WatchBase.metadata.create_all(self.engine)
        self.maker = sessionmaker(bind=self.engine)
        self.sco = scoped_session(self.maker)
    
    def search_watch_info(self, username: str, title: str, season: int, episode: int) -> WatchInfo:
        with self.sco() as session:
            return session.query(WatchInfo).filter(
                WatchInfo.username == username,
                WatchInfo.title == title,
                WatchInfo.season == season,
                WatchInfo.episode == episode
            ).first()
    
    def create_default_watch_info(self, username: str, title: str, season: int, episode: int) -> None:
        with self.sco() as session:
            session.add(WatchInfo(
                username = username, last_watched = 0,
                title = title, season = season, episode = episode,
                watched = False, playback = 0))
            session.commit()

    def init_media_history(self, username: str, episodes: dict, title: str):
        for i in episodes:
            for ep in episodes[i]:
                self.create_default_watch_info(username, title, i, ep)

    def get_watch_info_in_dict(self, username: str, title: str, season: int, episode: int) -> dict:
        info = self.search_watch_info(username, title, season, episode)
        return {
            "id": info.id, 
            "username": info.username, 
            "last_watched": info.last_watched, 
            "title": info.title, 
            "season": info.season, 
            "episode": info.episode, 
            "watched": info.watched, 
            "playback": info.playback
        }
    
    def set_watched(self, username: str, title: str, season: int, episode: int, watched: int) -> None:
        with self.sco() as session:
            info = session.query(WatchInfo).filter(
                WatchInfo.username == username,
                WatchInfo.title == title,
                WatchInfo.season == season,
                WatchInfo.episode == episode).first()

            if watched in [1, 2]:
                info.watched = True
                if watched == 2:
                    info.last_watched = time.time()
            else:
                info.watched = False 
           
            session.commit()

    def rotate_watched(self, username: str, title: str, season: int, episode: int) -> None:
        with self.sco() as session:
            info = session.query(WatchInfo).filter(
                WatchInfo.username == username,
                WatchInfo.title == title,
                WatchInfo.season == season,
                WatchInfo.episode == episode).first()
            info.watched = not info.watched
            session.commit()

    def get_all_user_title_history(self, username: str, title: str):
        with self.sco() as session:
            return session.query(WatchInfo).filter(
                WatchInfo.username == username, WatchInfo.title == title).all()

    def get_all_title_history(self, username: str, title: str, episodes: dict) -> dict:
        all_info = self.get_all_user_title_history(username, title)
        if not all_info: 
            self.init_media_history(username, episodes, title)
            all_info = self.get_all_user_title_history(username, title)

        info = {}
        for i in all_info:
            if i.season not in info: info[i.season] = {}
            info[i.season][i.episode] = {
                "watched": i.watched, "playback": i.playback, "last_watched": i.last_watched
            }

        return info

    def get_all_title_history_str_key(self, username: str, title: str, episodes: dict) -> dict:
        all_info = self.get_all_user_title_history(username, title)
        if not all_info: 
            self.init_media_history(username, episodes, title)
            all_info = self.get_all_user_title_history(username, title)

        info = {}
        for i in all_info:
            season = str(i.season)

            if season not in info: 
                info[season] = {}

            info[season][str(i.episode)] = {
                "watched": i.watched, "playback": i.playback, "last_watched": i.last_watched
            }

        return info
    
    def set_playback(self, username: str, title: str, season: int, episode: int, playback: int) -> None:
        with self.sco() as session:
            info = session.query(WatchInfo).filter(
                WatchInfo.username == username,
                WatchInfo.title == title,
                WatchInfo.season == season,
                WatchInfo.episode == episode).first()
            info.playback = playback
            session.commit()

    def set_last_watched(self, username: str, title: str, season: int, episode: int, last_watched: int) -> None:
        with self.sco() as session:
            info = self.search_watch_info(username, title, season, episode)
            info.last_watched = last_watched
            session.commit()

user_manager = Users()

watch_manager = WatchInfoManager()
