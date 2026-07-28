find_package(ZLIB REQUIRED)

add_executable(table4_nthash_k21_w21
    benchmark_table4_nthash.cpp
    nthash_wrapper.cpp)
target_compile_features(table4_nthash_k21_w21 PRIVATE cxx_std_17)
target_compile_definitions(table4_nthash_k21_w21 PRIVATE K=21 W=21)
target_compile_options(table4_nthash_k21_w21 PRIVATE
    -O3 -march=native -Wall -Wextra -Wpedantic)
target_include_directories(table4_nthash_k21_w21 PRIVATE
    "${KSSD_ARRAY_NTHASH_INCLUDE_DIR}")
target_link_libraries(table4_nthash_k21_w21 PRIVATE
    KSSDArray::kssd_array "${KSSD_ARRAY_NTHASH_LIBRARY}" ZLIB::ZLIB)

add_custom_target(table4-build DEPENDS table4_nthash_k21_w21)
