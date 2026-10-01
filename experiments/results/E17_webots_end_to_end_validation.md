# E17: Webots End-to-End Validation

Generated: 2026-10-01T02:50:34.206438+00:00

## Config

- **evaluation_method**: one real Runtime.run_task()/run_once() sequence through ComputerAugmentedRobot(WebotsRobot()) against a live Webots R2025a process (par_arena.wbt), via par_bridge.py - real differential-drive convergence, not a fake
- **profile**: simulation

## Metrics

- **task_reached_complete**: True
- **near_red_allowed_succeeded_and_converged**: True
- **collision_correctly_denied**: True
- **near_blue_allowed_succeeded_and_converged**: True
- **workspace_violation_correctly_denied**: True
- **estop_blocks_next_action**: True
- **estop_recovers_after_clear**: True
- **all_checks_passed**: True

## Notes

Unblocked 2026-10-01 (previously blocked: no Webots install). Confirms, in one real run against live Webots, every mechanic test_webots_bridge.py's fake previously only modeled: real waypoint navigation and target approach both converge (move latencies are real wall-clock seconds, not instant like MockRobot - see per-phase latency_seconds above, typically ~0.1-0.3s per real move vs MockRobot's ~0.001s), a live collision-margin denial fires against a real detected object position, a live workspace-violation denial fires identically to the in-memory case, and emergency-stop both blocks the very next action (before it ever reaches the real robot) and still lets the task recover to task_complete once cleared. No gap was found between the fake's predictions and the real controller's behavior, extending webots/README.md's prior get_observation/execute-level finding to the full physical/safety integration.

Full per-trial records: `E17_webots_end_to_end_validation.json`
