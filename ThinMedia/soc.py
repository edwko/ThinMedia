from flask_socketio import SocketIO

class Soc:
    def __init__(self) -> None:
        socket = None

    def start(self, app):
        self.socket = SocketIO(app)

soc = Soc()


