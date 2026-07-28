set(KSSD_ARRAY_MINIMAP2_SOURCE_DIR "" CACHE PATH
    "Clean minimap2 2.30 checkout used by optional integration targets")
set(KSSD_ARRAY_MINIMAP2_WORK_ROOT "" CACHE PATH
    "External output root used by optional minimap2 integration targets")
set(KSSD_ARRAY_MINIMAP2_JOBS "2" CACHE STRING
    "Compiler jobs used by optional minimap2 integration targets")

find_package(Python3 COMPONENTS Interpreter REQUIRED)

if(KSSD_ARRAY_MINIMAP2_SOURCE_DIR AND KSSD_ARRAY_MINIMAP2_WORK_ROOT)
    add_custom_target(minimap2-verify-build
        COMMAND ${CMAKE_COMMAND} -E env
            JOBS=${KSSD_ARRAY_MINIMAP2_JOBS}
            ${CMAKE_CURRENT_SOURCE_DIR}/verify_build.sh
            --build-only
            ${KSSD_ARRAY_MINIMAP2_SOURCE_DIR}
            ${CMAKE_SOURCE_DIR}
            ${KSSD_ARRAY_MINIMAP2_WORK_ROOT}/build-verification
        VERBATIM
        USES_TERMINAL)
    add_custom_target(minimap2-smoke
        COMMAND ${CMAKE_COMMAND} -E env
            JOBS=${KSSD_ARRAY_MINIMAP2_JOBS}
            ${CMAKE_CURRENT_SOURCE_DIR}/verify_build.sh
            --smoke
            ${KSSD_ARRAY_MINIMAP2_SOURCE_DIR}
            ${CMAKE_SOURCE_DIR}
            ${KSSD_ARRAY_MINIMAP2_WORK_ROOT}/smoke
        VERBATIM
        USES_TERMINAL)
else()
    message(STATUS
        "Minimap2 integration targets disabled; set KSSD_ARRAY_MINIMAP2_SOURCE_DIR and KSSD_ARRAY_MINIMAP2_WORK_ROOT")
endif()

add_subdirectory(indexing)
add_subdirectory(alignment_consistency)
