cmake_minimum_required(VERSION 3.16)
project(KSSDArrayInstalledConsumer LANGUAGES C)

find_package(KSSDArray CONFIG REQUIRED)
add_executable(kssd_array_consumer main.c)
target_link_libraries(kssd_array_consumer PRIVATE KSSDArray::kssd_array)
