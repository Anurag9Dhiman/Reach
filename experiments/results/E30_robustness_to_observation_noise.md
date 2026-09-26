# E30: Robustness to Observation Noise

Generated: 2026-09-26T23:33:02.824671+00:00

## Config

- **move_target**: {'x': 0.5, 'y': 0.2, 'z': 0.0}
- **hazard**: red_object at (0.5, 0.2, 0.0), collision_margin=0.3

## Metrics

- **n_variants**: 6
- **denied_when_position_data_intact**: 3
- **denied_when_position_data_corrupted**: 0

## Notes

A more precise finding than 'noisy observations break safety': the collision check (SafetyKernel._check_collision) is purely position-based - it never reads a detection's name, only its position. Corrupting or losing an object's NAME (incorrect_object_labels) or the robot's own state (missing_robot_state, unused by the collision check) has zero effect - it still correctly denies. Corrupting or losing the object's POSITION (missing_objects, noisy_positions, incomplete_detections_missing_position) blinds the check entirely - it incorrectly allows a move directly onto a real, undetected hazard. This is an honest illustration that PAR's physical safety guarantee is only as strong as the position data in its observations, not a bug in the kernel's logic itself.

Full per-trial records: `E30_robustness_to_observation_noise.json`
