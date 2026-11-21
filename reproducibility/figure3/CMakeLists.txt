find_package(OpenMP REQUIRED COMPONENTS C)
find_package(ZLIB REQUIRED)
find_library(FIGURE3_XXHASH_LIBRARY NAMES xxhash)
if(NOT FIGURE3_XXHASH_LIBRARY)
    message(FATAL_ERROR "The xxhash library is required for Figure 3")
endif()

add_executable(figure3_multithread_k21_w20 benchmark_multithread_k21.c)
target_compile_features(figure3_multithread_k21_w20 PRIVATE c_std_11)
target_compile_definitions(figure3_multithread_k21_w20 PRIVATE K=21 W=20)
target_compile_options(figure3_multithread_k21_w20 PRIVATE
    -O3 -march=native -Wall -Wextra -Wpedantic)
target_link_libraries(figure3_multithread_k21_w20 PRIVATE
    KSSDArray::kssd_array OpenMP::OpenMP_C
    "${FIGURE3_XXHASH_LIBRARY}" ZLIB::ZLIB m)

add_custom_target(figure3-build DEPENDS figure3_multithread_k21_w20)
