#include "player.h"

void player::logs::add_log(const std::string& log)
{
    std::lock_guard<std::mutex> lock(player::logs::LogMutex);
    auto now = std::chrono::system_clock::now();
    auto timePoint = std::chrono::system_clock::to_time_t(now);
    std::tm localTime = *std::localtime(&timePoint);

    std::stringstream ss;
    ss << std::put_time(&localTime, "%Y-%m-%d %H:%M:%S");

    player::logs::logs.insert(player::logs::logs.begin(), "["+ss.str()+ "] "+log);
    if (player::logs::logs.size() > 200)
    {
        player::logs::logs.erase(player::logs::logs.end());
    }
}

void logs_table()
{
    std::lock_guard<std::mutex> lock(player::logs::LogMutex);

    if (ImGui::BeginTable(
        "logs", 1, ImGuiTableFlags_ScrollY | ImGuiTableFlags_Resizable 
        | ImGuiTableFlags_Reorderable | ImGuiTableFlags_BordersH 
        | ImGuiTableFlags_Hideable, ImVec2(-1, -1)))
    {
        ImGui::TableSetupColumn("Logs", ImGuiTableColumnFlags_None);
        ImGui::TableHeadersRow();
        ImGuiListClipper clipper;
        clipper.Begin(player::logs::logs.size());
        while (clipper.Step())
        {
            for (int row = clipper.DisplayStart; row < clipper.DisplayEnd; ++row)
            {
                ImGui::TableNextRow();
                ImGui::TableSetColumnIndex(0);
                ImGui::TextWrapped("%s", player::logs::logs[row].c_str());
            }
        }
        ImGui::EndTable();
    }
}

void player::window::render_logs_window()
{
    ImGui::SetNextWindowSize(ImVec2(400, 400), ImGuiCond_FirstUseEver);
    if (ImGui::Begin("Logs", &player::window::render_logs))
    {
        logs_table();
    }
    ImGui::End();
}

void player::window::main_menu_bar()
{
    ImGui::PushStyleVar(ImGuiStyleVar_FramePadding, ImVec2(4, 6));
    if (ImGui::BeginMainMenuBar())
    {
        if (ImGui::MenuItem("Config")) {player::window::render_config = true;}

        if (!player::listen::running.load())
        {
            if (ImGui::MenuItem("Connect")) {player::listen::listen();}
        }
        else 
        {
            if (ImGui::MenuItem("Disconnect")) {player::listen::close();}
        }

        if (ImGui::MenuItem("Logs")) {player::window::render_logs = true;}

        ImGui::EndMainMenuBar();
    }
    ImGui::PopStyleVar();
}

void player::window::render_config_window()
{
    ImGui::SetNextWindowSize(ImVec2(400, 400), ImGuiCond_FirstUseEver);
    if (ImGui::Begin("Config", &player::window::render_config))
    {
        ImGui::PushItemWidth(-1);

        {
            std::lock_guard<std::mutex> lock(player::DataMutex);
            ImGui::Spacing();
            ImGui::Text("IP");
            if (ImGui::InputText("##IP", player::window::config_ip, IM_ARRAYSIZE(player::window::config_ip)))
            {
                player::config.ip = player::window::config_ip;
            }
            ImGui::Spacing();

            ImGui::Text("Port");
            if (ImGui::InputText("##Port", player::window::config_port, IM_ARRAYSIZE(player::window::config_port)))
            {
                player::config.port = player::window::config_port;
            }
            ImGui::Spacing();

            ImGui::Text("API Key");
            if (ImGui::InputText("##API Key", player::window::config_api_key, IM_ARRAYSIZE(player::window::config_api_key)))
            {
                player::config.api_key = player::window::config_api_key;
            }
            ImGui::Spacing();

            ImGui::Checkbox("Prefer English Language", &player::config.prefer_english_language);
            ImGui::Checkbox("Prefer English Subtitles", &player::config.prefer_english_subtitles);
            ImGui::Checkbox("Fullscreen", &player::config.fullscreen);
            ImGui::Checkbox("Playlist", &player::config.playlist);
            ImGui::Spacing();

            ImGui::Text("Demuxer Max Bytes");
            if (ImGui::InputInt("##Demuxer Max Bytes", &player::config.demuxer_max_bytes))
            {
                if (player::config.demuxer_max_bytes < 1)
                {
                    player::config.demuxer_max_bytes = 1;
                }
            }
        }

        ImGui::PopItemWidth();

        ImGui::Dummy(ImVec2(0, 10));

        if (ImGui::Button("Set & Save Config", ImVec2(-1, 0))) {player::save_config();}
    }
    ImGui::End();
}

void player::render()
{
    ImGui::DockSpaceOverViewport(ImGui::GetMainViewport());
    player::window::main_menu_bar();

    if (player::window::render_config) {player::window::render_config_window();}
    if (player::window::render_logs) {player::window::render_logs_window();}
}
