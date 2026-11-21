find_library(XXHASH_LIBRARY NAMES xxhash)
if(NOT XXHASH_LIBRARY)
    message(FATAL_ERROR "The xxhash library is required for Figure 2")
endif()

add_executable(figure2_single_thread_k21_w20
    benchmark_single_thread_realistic_kw.c)
target_compile_features(figure2_single_thread_k21_w20 PRIVATE c_std_11)
target_compile_definitions(figure2_single_thread_k21_w20 PRIVATE K=21 W=20)
target_compile_options(figure2_single_thread_k21_w20 PRIVATE
    -O3 -march=native -Wall -Wextra -Wpedantic)
target_link_libraries(figure2_single_thread_k21_w20 PRIVATE
    KSSDArray::kssd_array ${XXHASH_LIBRARY} m)

add_custom_target(figure2-build DEPENDS figure2_single_thread_k21_w20)
