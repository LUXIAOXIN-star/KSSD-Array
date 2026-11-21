find_library(FIGURE4_XXHASH_LIBRARY NAMES xxhash)
if(NOT FIGURE4_XXHASH_LIBRARY)
    message(FATAL_ERROR "The xxhash library is required for Figure 4")
endif()

add_executable(figure4_bucket_balance benchmark_bucket_balance.c)
target_compile_features(figure4_bucket_balance PRIVATE c_std_11)
target_compile_options(figure4_bucket_balance PRIVATE
    -O3 -march=native -Wall -Wextra -Wpedantic)
target_link_libraries(figure4_bucket_balance PRIVATE
    KSSDArray::kssd_array ${FIGURE4_XXHASH_LIBRARY} m)

add_custom_target(figure4-build DEPENDS figure4_bucket_balance)
