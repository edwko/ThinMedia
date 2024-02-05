from flask import send_file, request, Blueprint, session, jsonify
from users import user_manager, watch_manager
from index.base import DB
from soc import soc
import json
from natsort import natsorted

apibp = Blueprint('apibp', __name__)

class Msg:
    def __init__(self):
        self.ok = {'code': 200, 'msg': 'OK'}
        self.created = {'code': 201, 'msg': 'Created'}
        self.bad_request = {'code': 400, 'msg': 'Bad Request'}
        self.unauthorized = {'code': 401, 'msg': 'Unauthorized'}
        self.forbidden = {'code': 403, 'msg': 'Forbidden'}
        self.not_found = {'code': 404, 'msg': 'Not Found'}
        self.internal_server_error = {'code': 500, 'msg': 'Internal Server Error'}
        self.user_not_found = "User not found."

    def custom_msg(self, code, message):
        return {'code': code, 'msg': message}

RESPONSE = Msg()

@apibp.route("/play", methods=["GET"])
def play():
    apikey = request.args.get("apikey")
    db_id = request.args.get("id")
    season = request.args.get("season")
    episode = request.args.get("episode")

    if not any([apikey, db_id, season, episode]): 
        return jsonify(RESPONSE.bad_request)

    user = user_manager.get_json_api(apikey)
    if not user: 
        return jsonify(RESPONSE.unauthorized)

    media = DB.get_media_by_id(int(db_id))
    if not media: 
        return jsonify(RESPONSE.not_found)

    playlist = []
    if season in media.file_map:
        file_season = media.file_map[season]
        ep = int(episode)
        playlist = [str(i) for i in file_season if int(i) >= ep]
        playlist = natsorted(playlist)

    soc.socket.send(
        json.dumps({
            "title": media.title, 
            "get_media_endpoint": "download-media",
            "playlist": playlist, 
            "season": str(season), 
            "episode": str(episode),
            "db_id": str(db_id),
            "watch_info": watch_manager.get_all_title_history(user["user"], media.title, media.episodes)}),
        room=apikey)

    return jsonify(RESPONSE.ok)

@apibp.route("/download-media", methods=["GET"])
def download_media():
    db_id = request.args.get("id")
    season = request.args.get("season")
    episode = request.args.get("episode")

    if not any([db_id, season, episode]):
        return jsonify(RESPONSE.bad_request)
    db_id, season, episode = int(db_id), str(season), str(episode)

    data = DB.get_media_by_id(db_id)
    if not data:
        return jsonify(RESPONSE.not_found)

    if season in data.file_map:
        if episode in data.file_map[season]:
            return send_file(
                data.file_map[season][episode], as_attachment=True)

    return jsonify(RESPONSE.not_found)

@apibp.route("/set-watched", methods=["GET"])
def set_watched():
    db_id = request.args.get("id")
    season = request.args.get("season")
    episode = request.args.get("episode")
    value = request.args.get("value")
    api_key = request.args.get("apikey")

    if not any([db_id, season, episode, value, api_key]):
        return jsonify(RESPONSE.bad_request)
    db_id, value, season, episode, api_key = int(db_id), int(value), int(season), int(episode), str(api_key)

    user = user_manager.get_json_api(api_key)
    if not user:
        return jsonify(RESPONSE.unauthorized)
    data = DB.get_media_by_id(db_id)
    if not data:
        return jsonify(RESPONSE.not_found)

    watch_manager.set_watched(user["user"], data.title, season, episode, value)

    return jsonify(RESPONSE.ok)

@apibp.route("/set-playback", methods=["GET"])
def set_playback():
    db_id = request.args.get("id")
    season = request.args.get("season")
    episode = request.args.get("episode")
    value = request.args.get("value")
    api_key = request.args.get("apikey")

    if not any([db_id, season, episode, value, api_key]): 
        return jsonify(RESPONSE.bad_request)
    db_id, value, season, episode, api_key = int(db_id), int(value), int(season), int(episode), str(api_key)

    user = user_manager.get_json_api(api_key)
    if not user: 
        return jsonify(RESPONSE.unauthorized)
    data = DB.get_media_by_id(db_id)
    if not data: 
        return jsonify(RESPONSE.not_found)

    watch_manager.set_playback(user["user"], data.title, season, episode, value)

    return jsonify(RESPONSE.ok)

@apibp.route("/set-watched-web", methods=["GET"])
def set_watched_web():
    user = session.get("user")
    if not user: 
        return jsonify(RESPONSE.unauthorized)

    db_id = request.args.get("id")
    season = request.args.get("season")
    episode = request.args.get("episode")

    if not any([db_id, season, episode]): 
        return jsonify(RESPONSE.bad_request)

    data = DB.get_media_by_id(int(db_id))
    if not data: 
        return jsonify(RESPONSE.not_found)

    watch_manager.rotate_watched(user, data.title, int(season), int(episode))

    return jsonify(RESPONSE.ok)
