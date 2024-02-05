import logging, multiprocessing, threading, time
from datetime import datetime

logging.basicConfig(level=logging.INFO)

class Log:
    def __init__(self) -> None:
        self.enabled = True
        self.enabled_verbose = True
        self.lock = threading.Lock()

        self.menabled = self.enabled
        self.menabled_verbose = self.enabled_verbose
        self.mlock = multiprocessing.Lock()

    def seconds_to_date(self):
        return datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d %H:%M:%S")

    def log(self, msg, must: bool = False):
        with self.lock:
            if self.enabled or must:
                logging.info(f"[{self.seconds_to_date()}] {str(msg)}")

    def verbose(self, msg):
        with self.lock:
            if self.enabled_verbose:
                logging.info(f"[{self.seconds_to_date()}] {str(msg)}")

    def mlog(self, msg, must: bool = False):
        with self.mlock:
            if self.menabled or must:
                logging.info(f"[{self.seconds_to_date()}] {str(msg)}")

    def mverbose(self, msg):
        with self.mlock:
            if self.menabled_verbose:
                logging.info(f"[{self.seconds_to_date()}] {str(msg)}")

LOG = Log()