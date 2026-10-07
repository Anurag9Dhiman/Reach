# E17: MuJoCo End-to-End Validation

Generated: 2026-10-07T11:50:29.529570+00:00

## Config

- **evaluation_method**: one real Runtime.run_once() sequence through ComputerAugmentedRobot(MuJoCoRobot()) against a live MuJoCo 3.x process (Franka Panda from the Menagerie), via mujoco_bridge.py - real physics, real end-effector position, not a kinematic fake
- **profile**: simulation
- **distance_tolerance_m**: 0.2

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

Re-run against MuJoCo 2026-10-07 (previously run against Webots 2026-10-01; Webots was then retired entirely). Confirms, in one real run against live MuJoCo, every mechanic that was previously only confirmed against Webots: live collision-margin denial fires against a real detected object position, live workspace-violation denial fires identically to the in-memory case, waypoint approach converges within tolerance against a 7-DOF arm whose discretized keyframe-based `move` resolves per-prop (see mujoco/scenes/par_arena.py), and emergency-stop both blocks the very next action (before it ever reaches the real robot) and still lets the task recover to task_complete once cleared. The distance tolerance here (25cm) is looser than the e-puck's 5cm because the arm snaps to discrete joint-space keyframes rather than solving IK to an arbitrary (x, y, z) target - this is explicit scope, not a measurement regression (see mujoco/README.md's 'Known limitations' section). The paper's claim that the Pulse architecture is physical-simulator-agnostic now has evidence from two completely different simulators (Webots e-puck, MuJoCo Franka Panda), not just one.

Full per-trial records: `E17_mujoco_end_to_end_validation.json`
