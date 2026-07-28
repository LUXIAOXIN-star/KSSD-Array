cmake_minimum_required(VERSION 3.16)
project(KSSDArray VERSION 1.0.0 LANGUAGES C)

include(GNUInstallDirs)
include(CTest)
include(CMakePackageConfigHelpers)

set(KSSD_ARRAY_PACKAGE_VERSION "1.0.0")

option(KSSD_ARRAY_BUILD_SHARED "Build the shared KSSD-Array library" OFF)
option(KSSD_ARRAY_BUILD_TESTS "Build KSSD-Array core tests" OFF)
option(KSSD_ARRAY_BUILD_EXAMPLES "Build KSSD-Array examples" OFF)
option(KSSD_ARRAY_BUILD_REPRODUCIBILITY
    "Build manuscript reproducibility targets" OFF)

set(KSSD_ARRAY_SOURCES src/kssd_array.c src/permutation.c)

add_library(kssd_array STATIC ${KSSD_ARRAY_SOURCES})
add_library(KSSDArray::kssd_array ALIAS kssd_array)
target_compile_features(kssd_array PUBLIC c_std_11)
target_include_directories(kssd_array
    PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>
)
target_compile_options(kssd_array PRIVATE -Wall -Wextra -Wpedantic)
set_target_properties(kssd_array PROPERTIES
    OUTPUT_NAME kssd_array
    POSITION_INDEPENDENT_CODE ON
)

if(KSSD_ARRAY_BUILD_SHARED)
    add_library(kssd_array_shared SHARED ${KSSD_ARRAY_SOURCES})
    target_compile_features(kssd_array_shared PUBLIC c_std_11)
    target_include_directories(kssd_array_shared PUBLIC
        $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
        $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>
    )
    target_compile_options(kssd_array_shared PRIVATE -Wall -Wextra -Wpedantic)
    set_target_properties(kssd_array_shared PROPERTIES OUTPUT_NAME kssd_array)
endif()

if(BUILD_TESTING AND KSSD_ARRAY_BUILD_TESTS)
    find_package(Threads REQUIRED)
    add_executable(test_kssd_array tests/test_kssd_array.c)
    target_link_libraries(test_kssd_array PRIVATE
        KSSDArray::kssd_array Threads::Threads)
    target_compile_options(test_kssd_array PRIVATE -Wall -Wextra -Wpedantic)
    add_test(NAME core_api COMMAND test_kssd_array)

    foreach(fixed_k IN ITEMS 4 8 9 16 19 21 24 31 32)
        add_executable(test_fast_parity_${fixed_k} tests/test_fast_parity.c)
        target_compile_definitions(test_fast_parity_${fixed_k}
            PRIVATE KSSD_ARRAY_FIXED_K=${fixed_k})
        target_link_libraries(test_fast_parity_${fixed_k}
            PRIVATE KSSDArray::kssd_array)
        target_compile_options(test_fast_parity_${fixed_k}
            PRIVATE -Wall -Wextra -Wpedantic)
        add_test(NAME fast_parity_k${fixed_k}
            COMMAND test_fast_parity_${fixed_k})
    endforeach()
endif()

if(KSSD_ARRAY_BUILD_EXAMPLES)
    add_executable(minimal_api examples/minimal_api.c)
    target_link_libraries(minimal_api PRIVATE KSSDArray::kssd_array)
    target_compile_options(minimal_api PRIVATE -Wall -Wextra -Wpedantic)

    add_executable(build_minimizers examples/build_minimizers.c)
    target_link_libraries(build_minimizers PRIVATE KSSDArray::kssd_array)
    target_compile_options(build_minimizers PRIVATE -Wall -Wextra -Wpedantic)
endif()

if(KSSD_ARRAY_BUILD_REPRODUCIBILITY)
    enable_language(CXX)
    add_subdirectory(reproducibility/table2)
    add_subdirectory(reproducibility/figure2)
    add_subdirectory(reproducibility/figure3)
    add_subdirectory(reproducibility/figure4)
    set(KSSD_ARRAY_NTHASH_ROOT "" CACHE PATH "Installed ntHash prefix")
    if(NOT KSSD_ARRAY_NTHASH_ROOT AND DEFINED ENV{NTHASH_ROOT})
        set(KSSD_ARRAY_NTHASH_ROOT "$ENV{NTHASH_ROOT}")
    endif()
    if(NOT KSSD_ARRAY_NTHASH_ROOT)
        set(KSSD_ARRAY_NTHASH_ROOT
            "${CMAKE_CURRENT_SOURCE_DIR}/third_party/ntHash/install")
    endif()
    find_path(KSSD_ARRAY_NTHASH_INCLUDE_DIR nthash/nthash.hpp
        PATHS "${KSSD_ARRAY_NTHASH_ROOT}/include" NO_DEFAULT_PATH)
    find_library(KSSD_ARRAY_NTHASH_LIBRARY nthash
        PATHS "${KSSD_ARRAY_NTHASH_ROOT}/lib"
              "${KSSD_ARRAY_NTHASH_ROOT}/lib64" NO_DEFAULT_PATH)
    if(KSSD_ARRAY_NTHASH_INCLUDE_DIR AND KSSD_ARRAY_NTHASH_LIBRARY)
        add_subdirectory(reproducibility/table4)
    else()
        message(STATUS
            "ntHash not prepared; skipping Table 4 target. Set KSSD_ARRAY_NTHASH_ROOT.")
    endif()
    add_subdirectory(reproducibility/minimap2)
endif()

install(TARGETS kssd_array
    EXPORT KSSDArrayTargets
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    INCLUDES DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
if(KSSD_ARRAY_BUILD_SHARED)
    install(TARGETS kssd_array_shared
        LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
        RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
endif()
install(FILES include/kssd_array.h include/kssd_array_fast.h
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})
install(EXPORT KSSDArrayTargets
    FILE KSSDArrayTargets.cmake
    NAMESPACE KSSDArray::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/KSSDArray)

configure_package_config_file(
    cmake/KSSDArrayConfig.cmake.in
    "${CMAKE_CURRENT_BINARY_DIR}/KSSDArrayConfig.cmake"
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/KSSDArray)
write_basic_package_version_file(
    "${CMAKE_CURRENT_BINARY_DIR}/KSSDArrayConfigVersion.cmake"
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion)
configure_file(
    pkgconfig/kssd-array.pc.in
    "${CMAKE_CURRENT_BINARY_DIR}/kssd-array.pc"
    @ONLY)

install(FILES
    "${CMAKE_CURRENT_BINARY_DIR}/KSSDArrayConfig.cmake"
    "${CMAKE_CURRENT_BINARY_DIR}/KSSDArrayConfigVersion.cmake"
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/KSSDArray)
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/kssd-array.pc"
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/pkgconfig)
