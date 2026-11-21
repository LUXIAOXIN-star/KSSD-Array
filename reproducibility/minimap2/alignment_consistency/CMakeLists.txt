set(KSSD_ARRAY_MINIMAP2_ALIGNMENT_CONFIG
    "${CMAKE_SOURCE_DIR}/reproducibility/minimap2/alignment_consistency/config.json"
    CACHE FILEPATH "Pinned Minimap2 Supplementary alignment configuration")
set(KSSD_ARRAY_MINIMAP2_PHASE5B_OUTPUT "" CACHE PATH
    "Approved external Phase 5B output containing executables and KSSD indexes")
set(KSSD_ARRAY_MINIMAP2_ALIGNMENT_OUTPUT "" CACHE PATH
    "Explicit external output directory for formal Supplementary alignment")

if(KSSD_ARRAY_MINIMAP2_PHASE5B_OUTPUT AND KSSD_ARRAY_MINIMAP2_WORK_ROOT)
    add_custom_target(minimap2-alignment-preflight
        COMMAND ${Python3_EXECUTABLE}
            ${CMAKE_CURRENT_SOURCE_DIR}/run_alignment_consistency.py
            --preflight
            --config ${KSSD_ARRAY_MINIMAP2_ALIGNMENT_CONFIG}
            --phase5b-output ${KSSD_ARRAY_MINIMAP2_PHASE5B_OUTPUT}
            --output-dir ${KSSD_ARRAY_MINIMAP2_WORK_ROOT}/alignment-preflight
        VERBATIM
        USES_TERMINAL)
endif()

if(KSSD_ARRAY_MINIMAP2_PHASE5B_OUTPUT AND KSSD_ARRAY_MINIMAP2_ALIGNMENT_OUTPUT)
    add_custom_target(minimap2-alignment-formal
        COMMAND ${Python3_EXECUTABLE}
            ${CMAKE_CURRENT_SOURCE_DIR}/run_alignment_consistency.py
            --config ${KSSD_ARRAY_MINIMAP2_ALIGNMENT_CONFIG}
            --phase5b-output ${KSSD_ARRAY_MINIMAP2_PHASE5B_OUTPUT}
            --output-dir ${KSSD_ARRAY_MINIMAP2_ALIGNMENT_OUTPUT}
        VERBATIM
        USES_TERMINAL)
endif()
