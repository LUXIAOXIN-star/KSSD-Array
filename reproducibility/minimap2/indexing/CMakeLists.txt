set(KSSD_ARRAY_MINIMAP2_INDEXING_CONFIG
    "${CMAKE_SOURCE_DIR}/reproducibility/minimap2/indexing/config.json"
    CACHE FILEPATH "Pinned Minimap2 Supplementary indexing configuration")
set(KSSD_ARRAY_MINIMAP2_INDEXING_OUTPUT "" CACHE PATH
    "Explicit external output directory for formal Supplementary indexing")

if(KSSD_ARRAY_MINIMAP2_SOURCE_DIR AND KSSD_ARRAY_MINIMAP2_WORK_ROOT)
    add_custom_target(minimap2-indexing-preflight
        COMMAND ${Python3_EXECUTABLE}
            ${CMAKE_CURRENT_SOURCE_DIR}/run_supplementary_indexing.py
            --preflight
            --config ${KSSD_ARRAY_MINIMAP2_INDEXING_CONFIG}
            --upstream-source ${KSSD_ARRAY_MINIMAP2_SOURCE_DIR}
            --output-dir ${KSSD_ARRAY_MINIMAP2_WORK_ROOT}/indexing-preflight
        VERBATIM
        USES_TERMINAL)
endif()

if(KSSD_ARRAY_MINIMAP2_SOURCE_DIR AND KSSD_ARRAY_MINIMAP2_INDEXING_OUTPUT)
    add_custom_target(minimap2-indexing-formal
        COMMAND ${Python3_EXECUTABLE}
            ${CMAKE_CURRENT_SOURCE_DIR}/run_supplementary_indexing.py
            --config ${KSSD_ARRAY_MINIMAP2_INDEXING_CONFIG}
            --upstream-source ${KSSD_ARRAY_MINIMAP2_SOURCE_DIR}
            --output-dir ${KSSD_ARRAY_MINIMAP2_INDEXING_OUTPUT}
        VERBATIM
        USES_TERMINAL)
endif()
