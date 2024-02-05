cmake_minimum_required (VERSION 3.20)

project("player")

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

set(IMGUI_DIR ${CMAKE_CURRENT_SOURCE_DIR}/imgui)

file(GLOB IMGUI_CPP_SOURCES "${IMGUI_DIR}/*.cpp")
file(GLOB IMGUI_H_SOURCES "${IMGUI_DIR}/*.h")

if(UNIX OR APPLE)
    list(REMOVE_ITEM IMGUI_CPP_SOURCES "${IMGUI_DIR}/imgui_impl_dx11.cpp")
    list(REMOVE_ITEM IMGUI_H_SOURCES "${IMGUI_DIR}/imgui_impl_dx11.h")
    list(REMOVE_ITEM IMGUI_CPP_SOURCES "${IMGUI_DIR}/imgui_impl_sdl2.cpp")
    list(REMOVE_ITEM IMGUI_H_SOURCES "${IMGUI_DIR}/imgui_impl_sdl2.h")
endif()

set(IMGUI_SOURCES ${IMGUI_CPP_SOURCES} ${IMGUI_H_SOURCES})

find_package(PkgConfig REQUIRED)
pkg_search_module(mpv REQUIRED mpv)

find_package(nlohmann_json CONFIG REQUIRED)
find_package(sioclient CONFIG REQUIRED)
find_package(CURL CONFIG REQUIRED)
find_package(cereal CONFIG REQUIRED)

if(UNIX OR APPLE)
    find_package(Vulkan REQUIRED)
    find_package(glfw3 CONFIG REQUIRED)
    find_package(glm CONFIG REQUIRED)
endif()

if(WIN32)
    find_package(SDL2 CONFIG REQUIRED)
endif()

set(CMAKE_CXX_STANDARD 20)

add_executable(player 
    "main.cpp"
    "player.cpp"
    "player.h"
    "backend.cpp"
    "listen.cpp"
    "mpv.cpp"
    "themes.cpp"
)

target_link_libraries(player PRIVATE nlohmann_json::nlohmann_json)
target_link_libraries(player PRIVATE sioclient::sioclient sioclient::sioclient_tls)
target_link_libraries(player PRIVATE CURL::libcurl)
target_link_libraries(player PRIVATE cereal::cereal)

if(UNIX OR APPLE)
    target_link_libraries(player PRIVATE Vulkan::Vulkan)
    target_link_libraries(player PRIVATE glfw)
    target_link_libraries(player PRIVATE glm::glm)
endif()

if(WIN32)
    target_link_libraries(player PRIVATE SDL2::SDL2 SDL2::SDL2main)
endif()

target_sources(player PRIVATE ${IMGUI_SOURCES})
target_link_libraries(player PRIVATE mpv)