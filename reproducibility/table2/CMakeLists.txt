add_executable(table2_exhaustive_9mer test_exhaustive_9mer.c)
target_compile_features(table2_exhaustive_9mer PRIVATE c_std_11)
target_compile_options(table2_exhaustive_9mer PRIVATE
    -Wall -Wextra -Wpedantic -Wconversion -Werror)
target_link_libraries(table2_exhaustive_9mer PRIVATE KSSDArray::kssd_array)

add_test(NAME table2_exhaustive_9mer_full COMMAND table2_exhaustive_9mer)
add_test(NAME table2_exhaustive_9mer_smoke
    COMMAND table2_exhaustive_9mer --limit 4096)
set_tests_properties(table2_exhaustive_9mer_full PROPERTIES LABELS "table2;full")
set_tests_properties(table2_exhaustive_9mer_smoke
    PROPERTIES LABELS "table2;smoke")

add_custom_target(table2-validation
    COMMAND $<TARGET_FILE:table2_exhaustive_9mer>
    DEPENDS table2_exhaustive_9mer
    USES_TERMINAL)
add_custom_target(table2-validation-smoke
    COMMAND $<TARGET_FILE:table2_exhaustive_9mer> --limit 4096
    DEPENDS table2_exhaustive_9mer
    USES_TERMINAL)
