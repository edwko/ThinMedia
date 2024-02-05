from flask import send_file, redirect, render_template, url_for, request, Blueprint, session, jsonify, Response
from users import user_manager, watch_manager
from index.base import DB
from index.indexer import manager
from natsort import natsorted
import os
import hp

homebp = Blueprint('homebp', __name__)

def get_user():
    if session.get("user"): return session["user"]
    return None

# ---------------------------------------------------------------- #
# ------------------------ HOME ROUTES --------------------------- #
# ---------------------------------------------------------------- #

@homebp.route("/", methods=["GET", "POST"])
def home():
    user = get_user()
    if user:
        if request.method == "POST":
            max_pages = request.form.get("max_pages")
            if max_pages: 
                session["current_page"] = int(max_pages) 
        return render_template(
            "index.html", user=user_manager.get_json(user), update_search_on_input=True)

    create_admin = True if user_manager.user_size() == 0 else False
    return render_template("sign.html", create_admin=create_admin)

@homebp.route("/create-admin-account", methods=["POST"])
def create_admin_account():
    if user_manager.user_size() == 0:
        name = str(request.form.get("name"))
        password = str(request.form.get("password"))
        user_manager.add(name, password, "admin")
        session["user"] = name
    return redirect(url_for("homebp.home"))

@homebp.route("/login", methods=["POST"])
def login():
    if not session.get("user"):
        name = str(request.form.get("name"))
        password = str(request.form.get("password"))
        if user_manager.login(name, password):
            session["user"] = name
    return redirect(url_for("homebp.home")) 

@homebp.route("/home-media-html")
def home_media_html():
    if get_user():
        max_media_to_show = 100
        data = DB.get_all()

        search = request.args.get("search", "") 
        genres = session.get("genres", [])
        media_type = session.get("media_type", "all")

        max_pages = len(data) // max_media_to_show
        session["max_pages"] = max_pages
        page = session.get("current_page", 0)

        data = DB.apply_filters(data, search, genres, media_type)
        if not search:
            get_page = list(data.keys())[page * max_media_to_show: (page + 1) * max_media_to_show]
            data = {i: data[i] for i in get_page}

        return render_template("index_media.html", data=data)
    return ""
    
@homebp.route('/images/<dir>')
def serve_image(dir):
    dir = hp.decode_string(str(dir))
    base = os.path.dirname(os.path.abspath(__file__))
    return send_file(base+dir)

@homebp.route("/unique-genres-html")
def unique_genres_html():
    if get_user():
        return render_template("unique_genres.html", unique_genres=DB.get_unique_genres())
    return ""

@homebp.route("/set-media-type")
def set_media_type():
    if get_user():
        media_type = request.args.get("type")
        if media_type:
            session["media_type"] = DB.get_media_type(int(media_type))
    return ""

@homebp.route("/set-media-filter")
def set_media_filter():
    if get_user():
        filter = request.args.get("filter")
        if filter:
            filter = hp.decode_string(filter)
            genres = session.get("genres", [])
            if filter in genres: 
                genres.remove(filter)
            else: 
                genres.append(filter)
            session["genres"] = genres
    return ""

@homebp.route("/clear-all-genres")
def clear_all_genres():
    if get_user(): session["genres"] = []
    return ""

# ---------------------------------------------------------------- #
# ------------------------ MEDIA ROUTES -------------------------- #
# ---------------------------------------------------------------- #

@homebp.route("/media/<title>")
def media(title):
    if get_user() and title:
        media = DB.get_media(hp.decode_string(str(title)))
        if media:
            return render_template("media.html", media=media, title=title)
    return ""

@homebp.route("/media-data-html/<title>")
def media_data_html(title):
    user = get_user()
    if user:
        media = DB.get_media(hp.decode_string(str(title)))
        if media:
            return render_template(
                "media_data.html", media=media, user=user_manager.get_json(user),
                watch_info=watch_manager.get_all_title_history_str_key(user, media.title, media.episodes))
    return ""

@homebp.route("/media/edit/<db_id>", methods=["GET", "POST"])
def media_edit(db_id):
    user = get_user()
    if user:
        media = DB.get_media_by_id(int(db_id))

        if request.method == "POST":
            media_type = request.form.get("media_type")
            indexer_id = request.form.get("id")

            if media_type and indexer_id:
                new_titile = manager.update_media_by_indexer_id(str(media_type), str(indexer_id), media.files_base_folder)
                return redirect(url_for("homebp.media", title=hp.encode_string(new_titile)))

        if media:
            return render_template("media_edit.html", media=media, user=user_manager.get_json(user))
    return ""

@homebp.route("/media/files/<db_id>")
def media_get_files(db_id):
    user = get_user()
    if user and db_id:
        media = DB.get_media_by_id(int(db_id)) 
        if media:
            new = {}
            for i in natsorted([i for i in media.file_map]):
                new[i] = {e: media.file_map[i][e] for e in natsorted(list(media.file_map[i].keys()))}
            media.file_map = new            
            return render_template("media_files.html", media=media)
    return ""

# ---------------------------------------------------------------- #
# ---------------------- SETTINGS ROUTES ------------------------- #
# ---------------------------------------------------------------- #

@homebp.route("/settings")
def settings():
    user = get_user()
    if user:
        return render_template("settings.html", user=user_manager.get_json(user))
    return ""

def event_stream():
    for msg in manager.scan_and_index_current_media():
        yield f"data: {msg}\n\n"
    yield "data: done\n\n"

@homebp.route("/index-media")
def index_media():
    user = get_user()
    if user:
        if user_manager.get_json(user)["role"] == "admin":
            return Response(event_stream(), mimetype="text/event-stream")
    return "Insufficient permissions"

@homebp.route("/index-media-awc", methods=["GET", "POST"])
def index_media_awc():
    user = get_user()
    if user and user_manager.get_json(user)["role"] == "admin":
        if request.method == "POST":
            matches = user_manager.get_mapped(user)
            if matches:
                mapped = {}
                for i in matches:
                    id = None
                    id_type = None
                    custom_id = request.form.get(i)
                    custom_id_type = request.form.get(f"media_type-{i}")
                    if custom_id and custom_id_type:
                        id = str(custom_id).strip()
                        id_type = str(custom_id_type)

                    mapped[i] = {"data": matches[i], "id": id, "id_type": id_type}
                
                user_manager.update_mapped(user, {})
                manager.index_media_awc(mapped)
            return redirect(url_for("homebp.settings"))

        else:
            matches = manager.get_matches(user_manager.get_mapped(user))
            user_manager.update_mapped(user, matches)
            return render_template("index_media_awc.html", matches=matches)

    return "Insufficient permissions"
