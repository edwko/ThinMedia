import mpv
import json
import socketio
import threading
import time
import requests
import os
import sys
from dataclasses import dataclass

@dataclass
class Episode:
    base: str
    playback: float
    watched: bool
    opened: bool = False

def restart():
    """
    This might not be needed for all users.
    This function restarts the current Python script.
    It's useful when the libmpv doesn't clean or keep at certain size 
    its cache and RAM after termination.
    """
    print("Restarting...")
    os.execv(sys.executable, ['python'] + sys.argv)

class Run:
    def __init__(self, host_url: str, api_key: str, data: dict):
        self.mpv = mpv.MPV(
            osc=True, 
            input_default_bindings=True, 
            input_vo_keyboard=True
        )

        self.lock = threading.Lock()

        self._set_properties()
        self._observe_properties()

        self.data = data
        self.host_url = host_url
        self.api_key = api_key
        self.base_endpoint = self._make_base_endpoint()
        self.playlist = self.make_playlist()
        self.playing = list(self.playlist.keys())[0]

        self.run_seek = True
        self.seek_time = self.playlist[self.playing].playback

        self.start()

    def _set_properties(self):
        self.mpv._set_property('demuxer-max-back-bytes', '15M')
        self.mpv._set_property('demuxer-max-bytes', '15M')
        self.mpv._set_property('fullscreen', 'yes')

    def _observe_properties(self):
        self.mpv.observe_property('time-pos', self.time_observer)
        self.mpv.observe_property('path', self.path)

    def _make_base_endpoint(self):
        return "?id=" + self.data['db_id'] + "&season=" + self.data['season'] + "&episode="

    def seek(self, value):
        self.mpv.seek(value, reference='absolute', precision='exact')

    def _make_playlist_base(self, id, season, episode):
        return f"?id={id}&season={season}&episode={episode}"

    def _make_playlist_url(self, base):
        return self.host_url + f"/{self.data['get_media_endpoint']}" + base

    def make_playlist(self):
        playlist = {}
        for i in self.data["playlist"]:
            if int(i) >= int(self.data['episode']):
                base = self._make_playlist_base(self.data['db_id'], self.data['season'], i)
                url = self._make_playlist_url(base)
                playlist[url] = Episode(
                    base = base, 
                    playback = self.data["watch_info"][self.data['season']][i]["playback"], 
                    watched = self.data["watch_info"][self.data['season']][i]["watched"]
                )
                self.mpv.playlist_append(url)
        playlist[list(playlist.keys())[0]].opened = True
        self.mpv.playlist_pos = 0 
        return playlist

    def get(self, url):
        requests.get(url)

    def set_watched(self, m):
        url = self.host_url + f"/set-watched" + self.playlist[m].base + "&apikey=" + self.api_key
        url += "&value=1"
        threading.Thread(target=self.get, args=(url,), daemon=True).start()

    def set_playback(self, m):
        if not self.playlist[m].playback: 
            return None
        url = self.host_url + f"/set-playback" + self.playlist[m].base + "&apikey=" + self.api_key
        url += "&value=" + str(int(self.playlist[m].playback))
        threading.Thread(target=self.get, args=(url,), daemon=True).start()

    def update_playback(self):
        for m in self.playlist:
            if self.playlist[m].opened:
                url = self.host_url + f"/set-playback" + self.playlist[m].base + "&apikey=" + self.api_key
                url += "&value=" + str(int(self.playlist[m].playback))
                self.get(url)

    def time_observer(self, _name, value):
        if value:
            with self.lock:
                if self.run_seek:
                    self.seek(self.seek_time)
                    self.run_seek = False
                    return None

            self.playlist[self.playing].playback = value
        
    def path(self, _name, value):
        if value:
            if self.playing != value:
                with self.lock:
                    self.run_seek = True
                    self.seek_time = self.playlist[value].playback
                
                self.playlist[value].opened = True
                self.playing = value
                self.set_playback(value)
                self.set_watched(value)
    
    def terminate(self):
        self.update_playback()
        print("Exiting MPV...")
        self.mpv.terminate()
        del self.mpv

    def start(self):
        self.set_watched(self.playing)
        self.mpv.wait_for_shutdown()
        self.terminate()

class Listen:
    def __init__(self, api_key: str, host_url) -> None:
        self.api_key = api_key
        self.host_url = host_url
        self.sio = socketio.Client()
        self.sio.on("connect", self.connect)
        self.sio.on("disconnect", self.disconnect)
        self.sio.on("message", self.message)
        self.running = False
        self.lock = threading.Lock()
        self.start_socket()

    def connect(self):
        print("Connected to server.")
        self.sio.emit('join', {'apikey': self.api_key})

    def disconnect(self):
        print("Disconnect to server.")
        self.sio.emit('leave', {'apikey': self.api_key})

    def start(self, data):
        with self.lock: 
            if self.running:
                print("Player already running.")
                return 0
            self.running = True

        r = Run(self.host_url, self.api_key, data)
        del r

        with self.lock: 
            self.running = False

        restart()

    def message(self, data):
        data = json.loads(data)
        self.start(data)

    def start_socket(self):
        self.sio.connect(self.host_url)
        self.sio.wait()

Listen(
    api_key="Your-ThinMedia-API-Key-Here",
    host_url="http://127.0.0.1:5000"
)