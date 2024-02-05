import index.indexer
import index.base
import index.tmdb
import index.log

from flask import Flask
from flask_socketio import join_room, leave_room

from soc import soc
from home import homebp
from api import apibp
import hp

app = Flask(__name__)
app.secret_key = "Your-Secret-Key-Here"
soc.start(app)

@soc.socket.on("join")
def on_join(data):
    api = data["apikey"]
    if api: join_room(api)

@soc.socket.on("leave")
def on_leave(data):
    api = data["apikey"]
    if api: leave_room(api)

app.jinja_env.globals.update(encode_string=hp.encode_string)
app.jinja_env.globals.update(decode_string=hp.decode_string)

app.register_blueprint(homebp)
app.register_blueprint(apibp)

if __name__ == '__main__':
    soc.socket.run(app, host="0.0.0.0", port="5000", allow_unsafe_werkzeug=True)