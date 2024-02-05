#include "player.h"
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <cstring>
#include <cstdlib>
#include <regex>
#include <mpv/client.h>
#include <random>

struct playing_media_info
{
    bool update;
    double playback;
    bool watched;
    std::string episode_endpoint;
};

struct mpv_media_info
{
    std::string title;
    std::string media_endpoint;
    std::string season;
    std::string episode;
    std::string db_id;
    std::string temp_playlist_file;
    std::vector<std::string> playlist_episodes;
    std::map<std::string, playing_media_info> url_pmi;
};

std::string create_episode_endpoint(
    const std::string& db_id, const std::string& season, const std::string& episode)
{
    return "id=" + db_id + "&season=" + season + "&episode=" + episode;
}

std::string create_download_url(
    const std::string& base_url, const std::string& download_endpoint, 
    const std::string& db_id, const std::string& season, const std::string& episode)
{
    return base_url + "/" + download_endpoint + "?" + create_episode_endpoint(db_id, season, episode);
}

size_t WriteCallback(void* contents, size_t size, size_t nmemb, std::string* s)
{
    size_t newLength = size * nmemb;
    size_t oldLength = s->size();
    try {s->resize(oldLength + newLength);}
    catch (std::bad_alloc& e) {return 0;}
    std::copy((char*)contents, (char*)contents + newLength, s->begin() + oldLength);
    return size * nmemb;
}

void set_playback(double playback, std::string episode_endpoint, std::string base_url, std::string api_key)
{
    std::string u = base_url + "/set-playback?apikey=" + api_key + "&" + episode_endpoint + "&value=" + std::to_string(static_cast<int>(playback));
    CURL* curl;
    CURLcode res;
    std::string read;
    curl = curl_easy_init();
    if (curl)
    {
        curl_easy_setopt(curl, CURLOPT_URL, u.c_str());
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &read);
        res = curl_easy_perform(curl);
        if (res != CURLE_OK) {fprintf(stderr, "Failed: %s\n", curl_easy_strerror(res));}
        curl_easy_cleanup(curl);
    }
}

void set_watched(std::string episode_endpoint, std::string base_url, std::string api_key)
{
    std::string u = base_url + "/set-watched?apikey=" + api_key + "&" + episode_endpoint + "&value=2";
    CURL* curl;
    CURLcode res;
    std::string read;
    curl = curl_easy_init();
    if (curl)
    {
        curl_easy_setopt(curl, CURLOPT_URL, u.c_str());
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &read);
        res = curl_easy_perform(curl);
        if (res != CURLE_OK) {fprintf(stderr, "Failed: %s\n", curl_easy_strerror(res));}
        curl_easy_cleanup(curl);
    }
}

void t_set_watched(std::string& episode_endpoint, std::string& base_url, std::string& api_key)
{
    std::thread(set_watched, episode_endpoint, base_url, api_key).detach();
}

void t_set_playback(double& playback, std::string& episode_endpoint, std::string& base_url, std::string& api_key)
{
    std::thread(set_playback, playback, episode_endpoint, base_url, api_key).detach();
}

static inline void check_error(int status)
{
    if (status < 0) 
    {
        printf("mpv API error: %s\n", mpv_error_string(status));
        exit(1);
    }
}

int open_mpv_player(Config& config, mpv_media_info& info)
{
    std::string playing = create_download_url(config.url, info.media_endpoint, info.db_id, info.season, info.episode);
    std::map<std::string, playing_media_info>& pmi = info.url_pmi;
    pmi[playing].update = true;
    pmi[playing].watched = true;

    t_set_watched(pmi[playing].episode_endpoint, config.url, config.api_key);

    bool seek = false;
    double seek_to = 0.0;

    int val = 1;

    mpv_handle *ctx = mpv_create();
    if (!ctx) {return 1;}
    
    check_error(mpv_set_option_string(ctx, "input-default-bindings", "yes"));
    mpv_set_option_string(ctx, "input-vo-keyboard", "yes");
    check_error(mpv_set_option(ctx, "osc", MPV_FORMAT_FLAG, &val));

    int start_time = static_cast<int>(pmi[playing].playback);
    mpv_set_option_string(ctx, "start", std::to_string(start_time).c_str());

    if (config.fullscreen)
    {
        mpv_set_option_string(ctx, "fullscreen", "yes");
    }

    if (config.prefer_english_language)
    {
        mpv_set_option_string(ctx, "alang", "en,eng,english");
    }

    if (config.prefer_english_subtitles)
    {
        mpv_set_option_string(ctx, "slang", "en,eng,english");
    }

    if (config.demuxer_max_bytes > 0)
    {
        std::string max_bytes = std::to_string(config.demuxer_max_bytes) + "M";
        mpv_set_option_string(ctx, "demuxer-max-back-bytes", max_bytes.c_str());
        mpv_set_option_string(ctx, "demuxer-max-bytes", max_bytes.c_str());
    }
    
    if (config.playlist)
    {
        mpv_observe_property(ctx, 0, "path", MPV_FORMAT_NONE);
    }

    mpv_observe_property(ctx, 0, "playback-time", MPV_FORMAT_DOUBLE);

    check_error(mpv_initialize(ctx));

    if (config.playlist && info.temp_playlist_file.size() > 1)
    {
        const char *cmd[] = {"loadlist", info.temp_playlist_file.c_str(), NULL};
        check_error(mpv_command(ctx, cmd));
    }
    else
    {
        const char *cmd[] = {"loadfile", playing.c_str(), NULL};
        check_error(mpv_command(ctx, cmd));
    }

    while (true) 
    {
        mpv_event *event = mpv_wait_event(ctx, 10000);
        if (seek && event->event_id == MPV_EVENT_PLAYBACK_RESTART)
        {
            mpv_set_property(ctx, "time-pos", MPV_FORMAT_DOUBLE, &seek_to);
            seek = false;
        }
        if (event->event_id == MPV_EVENT_PROPERTY_CHANGE) 
        {
            mpv_event_property *prop = (mpv_event_property *)event->data;
            if (config.playlist)
            {
                if (strcmp(prop->name, "path") == 0) {
                    char *data = nullptr;
                    if (mpv_get_property(ctx, prop->name, MPV_FORMAT_OSD_STRING, &data) < 0) {} 
                    else 
                    {
                        std::string path = data;
                        if (playing != path) 
                        {
                            playing = path;
                            seek = true;
                            seek_to = pmi[playing].playback;
                            pmi[playing].update = true;
                            t_set_watched(pmi[playing].episode_endpoint, config.url, config.api_key);
                        }
                        mpv_free(data);
                    }
                }
            }

            if (strcmp(prop->name, "playback-time") == 0 && prop->format == MPV_FORMAT_DOUBLE) 
            {
                pmi[playing].playback = *static_cast<double*>(prop->data);
            }
        }
        
        if (event->event_id == MPV_EVENT_SHUTDOWN) {break;}
    }

    mpv_terminate_destroy(ctx);
    
    return 0;
}

void player::mpv::start(json data)
{
    std::string wd = "";
    Config config_copy;
    {
        std::lock_guard<std::mutex> lock(player::DataMutex);
        config_copy = player::config;
        wd = player::working_directory;
    }

    mpv_media_info info;
    info.title = data["title"].get<std::string>();
    info.media_endpoint = data["get_media_endpoint"].get<std::string>();
    info.season = data["season"].get<std::string>();
    info.episode = data["episode"].get<std::string>();
    info.db_id = data["db_id"].get<std::string>();

    for (auto& e : data["playlist"]) {info.playlist_episodes.push_back(e.get<std::string>());}

    if (config_copy.playlist) 
    {
        info.temp_playlist_file = wd + "/temp_playlist_" + std::to_string(
            std::chrono::duration_cast<std::chrono::microseconds>(
                std::chrono::high_resolution_clock::now().time_since_epoch()).count()) + ".m3u";
        std::ofstream file(info.temp_playlist_file);
        for (auto& e : info.playlist_episodes)
        {
            std::string url = create_download_url(config_copy.url, info.media_endpoint, info.db_id, info.season, e);
            playing_media_info pmi;
            pmi.update = false;
            pmi.playback = static_cast<double>(data.at("watch_info").at(info.season).at(e).at("playback").get<int>());
            pmi.watched = data.at("watch_info").at(info.season).at(e).at("watched").get<bool>();
            pmi.episode_endpoint = create_episode_endpoint(info.db_id, info.season, e);
            info.url_pmi[url] = pmi;
            file << url << std::endl;
        } 
    }
    else
    {
        std::string url = create_download_url(config_copy.url, info.media_endpoint, info.db_id, info.season, info.episode);
        playing_media_info pmi;
        pmi.update = false;
        pmi.playback = static_cast<double>(data.at("watch_info").at(info.season).at(info.episode).at("playback").get<int>());
        pmi.watched = data.at("watch_info").at(info.season).at(info.episode).at("watched").get<bool>();
        pmi.episode_endpoint = create_episode_endpoint(info.db_id, info.season, info.episode);
        info.url_pmi[url] = pmi;
    }

    open_mpv_player(config_copy, info);

    if (config_copy.playlist) 
    {
        std::remove(info.temp_playlist_file.c_str());
    }

    for (auto& e : info.url_pmi)
    {
        playing_media_info& info = e.second;
        if (info.update)
        {
            t_set_playback(info.playback, info.episode_endpoint, config_copy.url, config_copy.api_key);
        }
    }
    player::logs::add_log("MPV player closed.");
}
