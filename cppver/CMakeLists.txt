cmake_minimum_required(VERSION 3.21)

project(clinsys_cpp VERSION 4.5 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

find_package(Qt6 REQUIRED COMPONENTS Widgets)

qt_add_executable(clinsys_cpp
    main.cpp
    ClinicalApp.h
    ClinicalApp.cpp
    CsvTable.h
    CsvTable.cpp
)

target_link_libraries(clinsys_cpp PRIVATE Qt6::Widgets)

if (MSVC)
    target_compile_options(clinsys_cpp PRIVATE /utf-8)
endif()

