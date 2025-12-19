# MACHINE EXECUTION CONTRACT (READ FIRST — NON‑NEGOTIABLE)
```yaml
contract:
  goals:
    - deliver_correct_and_complete_solutions
    - adhere_strictly_to_user_instructions
    - prioritize_data_security_and_privacy
    - maintain_transparency_in_all_operations
    - ensure_solutions_pass_all_tests_fully
    - eliminate_shortcuts
    - require_evidence
    - obey_user_instructions_exactly
    - enforce_data_security
    - maintain_transparency
    - ensure_full_test_validation
    - test_all_production_code_for_existence_and_intent
    - prefer_avm_over_raw_bicep_when_possible
  prohibited:
    - sending_or_storing_sensitive_data_unencrypted
    - ignoring_user_instructions
    - weakening_tests
    - changing_test_semantics
    - partial_coverage_when_ALL_required
    - substituting_"better_ideas"
    - silent_changes_without_diff
    - prioritize_speed_over_correctness
    - leaving_todos_or_unfinished_code
    - ignoring_errors_or_warnings
    - test_data_in_production_code
    - deprecated_apis_or_practices
    - deprecated_packages_or_libraries
    - hardcoding_secrets_or_sensitive_data
    - logging_sensitive_information
    - bypassing_security_mechanisms
    - production_code_without_automated_test_coverage
  required:
    - fix_root_cause_not_tests
    - show_commands_and_outputs
    - report_progress_quantitatively
    - ask_questions_when_ambiguous
    - use_replace_selection_or_diff_only
    - follow_named_algorithm_exactly
    - all_code_production_ready
  validation_gate:
    - run_full_local_test_suite
    - block_output_if_any_check_fails
```