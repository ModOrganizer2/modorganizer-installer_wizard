cmake_minimum_required(VERSION 3.16)

project(installer_wizard LANGUAGES NONE)

# find_package(mo2-cmake CONFIG REQUIRED)

include(${CMAKE_CURRENT_LIST_DIR}/../cmake_common/mo2.cmake)

add_subdirectory(src)
