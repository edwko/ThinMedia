#pragma once
#include <iostream>
#include <thread>
#include <chrono>
#include <string>
#include <vector>
#include <map>
#include <atomic>
#include <mutex>
#include <memory> 
#include <functional>
#include <sys/socket.h>
#include <sys/un.h>
#include <sio_socket.h>
#include <sio_client.h>
#include <sstream>
#include <iomanip>
#include <nlohmann/json.hpp>
#include <curl/curl.h>
#include <cereal/archives/binary.hpp>
#include <cereal/types/vector.hpp>
#include <cereal/types/string.hpp>
#include <fstream> 
#include "imgui/imgui.h"

using json = nlohmann::json;

struct Config
{
    std::string url = "";
    std::string ip = "";
    std::string port = "";
    std::string api_key = "";
    bool prefer_english_language = true;
    bool prefer_english_subtitles = true;
    bool fullscreen = true;
    bool playlist = true;
    int demuxer_max_bytes = 25;

    template <class Archive>
    void serialize(Archive & archive)
    {
        archive(
            ip, port, api_key, prefer_english_language, prefer_english_subtitles,
            fullscreen, demuxer_max_bytes, playlist
        );
    }
};

namespace player
{
    void render();
    int backend();
    void dark();

    inline std::string working_directory = "";

    std::string encode_string(const std::string& input);
    std::string decode_string(const std::string& input);

    inline json media_data;
    inline std::mutex DataMutex;

    inline Config config;

    void set_config_url();
    void load_config();
    void save_config();

    namespace logs
    {
        inline std::mutex LogMutex;
        inline std::vector<std::string> logs;
        void add_log(const std::string& log);
    } // logs

    namespace window
    {
        void render_logs_window();
        inline bool render_config = false;
        inline bool render_logs = false;
        void render_config_window();
        void main_menu_bar();

        inline char config_ip[128] = "";
        inline char config_port[128] = "";
        inline char config_api_key[512] = "";
        inline char config_custom_config[512] = "";
    } // window

    namespace listen 
    {
        inline std::atomic_bool running = false;
        inline std::shared_ptr<sio::client> sio_client = std::make_shared<sio::client>();
        void listen(); 
        void close();
    } // listen

    namespace mpv 
    {
        inline std::atomic_bool running = false;
        void start(json data);
    } // mpv

} // player
