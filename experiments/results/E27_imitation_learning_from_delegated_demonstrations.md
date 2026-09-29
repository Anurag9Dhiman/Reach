# E27: Imitation Learning from Delegated Demonstrations

Generated: 2026-09-27T16:32:44.032227+00:00

## Config

- **policy**: nearest-neighbor task-text lookup (toy POC, not a trained model)
- **min_demos_required**: 3

## Metrics

- **n_demonstrations_available**: 14
- **n_training**: 13
- **held_out_task**: Log the reading 42.8 from the red_object.
- **held_out_actual_first_action**:
  - **action**: spotlight
  - **text**: log.txt
  - **reason**: Opening the log file on the desktop.
- **toy_policy_prediction**:
  - **predicted_first_action**:
    - **action**: spotlight
    - **text**: log
    - **reason**: Opening the log application to locate the red_object entry.
  - **matched_training_task**: Log the reading 'X-982' from the red_object.
  - **word_overlap**: 5
- **note**: illustrative proof-of-concept only - see module docstring

## Notes

This is a proof-of-concept illustrating the pipeline shape (collect demonstrations -> hold one out -> predict its first action from the rest), not a real imitation-learning result - a real E27 needs orders of magnitude more demonstrations and an actual model architecture (e.g. a small vision-language-action model fine-tuned on screenshot+action pairs), which is a dedicated ML project beyond this experiment's scope, per the original scope decision.

Full per-trial records: `E27_imitation_learning_from_delegated_demonstrations.json`
