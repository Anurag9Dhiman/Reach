# E31: Robustness to ACS Errors

Generated: 2026-09-26T23:33:32.717018+00:00

## Config

- **acs**: fake (FaultyCollectiveOSBridge, one output type per trial)

## Metrics

- **accepted_as_success**:
  - **correct_result**: True
  - **incomplete_result**: True
  - **incorrect_result**: True
  - **ambiguous_result**: True
  - **explicit_failure**: False
- **semantic_verification_exists**: False
- **content_based_recovery_mechanisms_exist**: False

## Notes

3 of 5 output types (correct, incomplete, incorrect, ambiguous - everything except explicit_failure) are accepted as success identically, because PAR only checks the ACS's self-reported status, never the content of its answer. PAR has no clarification-request, automatic-retry, or content-based alternative-action mechanism for any of these cases today - 'choosing an alternative action' after a bad result is only possible in the sense that a planner's *next* step could react to a result.message that says something went wrong, and only for explicit_failure does the message actually say that. This is the same limitation e22's incorrect_result_accepted category and the paper's Discussion both already name; this experiment is the dedicated, systematic version of that finding across all 5 requested output types.

Full per-trial records: `E31_robustness_to_acs_errors.json`
