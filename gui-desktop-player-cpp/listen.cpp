#include "player.h"

std::string player::encode_string(const std::string& input) 
{
    std::stringstream ss;
    for (unsigned char c : input) 
    {
        ss << std::hex << std::setw(2) << std::setfill('0') << (int)c;
    }
    return ss.str();
}

std::string player::decode_string(const std::string& input) 
{
    std::string output;
    std::stringstream ss(input);
    while (!ss.eof()) 
    {
        std::string part;
        ss >> std::setw(2) >> part;
        if (!part.empty()) 
        {
            std::istringstream converter(part);
            int value;
            converter >> std::hex >> value;
            output += static_cast<char>(value);
        }
    }
    return output;
}

void on_connected()
{
    auto data = sio::object_message::create();
    std::string apikey = "";
    {
        std::lock_guard<std::mutex> lock(player::DataMutex);
        apikey = player::config.api_key;
    }

    data->get_map()["apikey"] = sio::string_message::create(apikey);
    player::listen::sio_client->socket()->emit("join", data);
    player::logs::add_log("Connected to server.");
}

void on_close(sio::client::close_reason const& reason)
{
    auto data = sio::object_message::create();
    std::string apikey = "";
    {
        std::lock_guard<std::mutex> lock(player::DataMutex);
        apikey = player::config.api_key;
    }
    data->get_map()["apikey"] = sio::string_message::create(apikey);
    
    player::listen::sio_client->socket()->emit("leave", data);
    player::logs::add_log("Connection to the server closed.");
}

void on_fail()
{
    player::logs::add_log("Failed to connect the server closed.");
}

void message_event(sio::event& ev)
{
    std::string data = ev.get_message()->get_string();
    json json_data = nlohmann::json::parse(data);
    std::string msg = json_data["title"];
    player::logs::add_log("Got play request: " + msg);
    std::thread start_mpv(player::mpv::start, json_data);
    start_mpv.detach();
}

void player::listen::listen()
{
    player::listen::running.store(true);

    // Bind events
    player::listen::sio_client->set_open_listener(std::bind(&on_connected));
    player::listen::sio_client->set_close_listener(std::bind(&on_close, std::placeholders::_1));
    player::listen::sio_client->set_fail_listener(std::bind(&on_fail));
    player::listen::sio_client->socket()->on("message", &message_event);

    // Connect to the server
    std::string url = "";
    {
        std::lock_guard<std::mutex> lock(player::DataMutex);
        url = player::config.url;
    }
    player::listen::sio_client->connect(url);
}

void player::listen::close()
{
    player::listen::sio_client->close();
    player::listen::running.store(false);
}

void player::set_config_url()
{
    player::config.url = "http://" + player::config.ip + ":" + player::config.port;
}

void player::load_config()
{
    std::lock_guard<std::mutex> lock(player::DataMutex);
    std::string path = player::working_directory + "/config.bin";
    std::ifstream is(path, std::ios::binary);
    if (is.is_open())
    {
        cereal::BinaryInputArchive iarchive(is);
        iarchive(player::config);

        strcpy(player::window::config_ip, player::config.ip.c_str());
        strcpy(player::window::config_port, player::config.port.c_str());
        strcpy(player::window::config_api_key, player::config.api_key.c_str());

        player::set_config_url();
    }
}

void player::save_config()
{
    std::lock_guard<std::mutex> lock(player::DataMutex);
    std::string path = player::working_directory + "/config.bin";
    std::ofstream os(path, std::ios::binary);
    if (os.is_open())
    {
        cereal::BinaryOutputArchive oarchive(os);
        oarchive(player::config);
        player::set_config_url();
    }
}
