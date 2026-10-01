# E16: Physical Safety Constraint Evaluation

Generated: 2026-10-01T02:47:49.430689+00:00

## Config

- **evaluation_method**: direct SafetyKernel.admit()/check() calls against MockRobot's and a live WebotsRobot's observations side by side, same scenario battery as E6
- **profile**: {'name': 'simulation', 'workspace': {'x': (-2.0, 2.0), 'y': (-2.0, 2.0), 'z': (0.0, 2.0)}, 'max_velocity': 2.0, 'action_timeout_seconds': 0.5, 'approval_required': True, 'collision_margin': 0.3}
- **n_scenarios**: 10
- **robot_interface**: par.robots.webots_bridge.WebotsRobot against a real, live Webots R2025a process (par_arena.wbt) via par_bridge.py - not a fake or kinematic stand-in

## Metrics

- **mock_decision_accuracy**: 1.0
- **webots_decision_accuracy**: 1.0
- **interfaces_agree_on_all_scenarios**: True
- **webots_confusion_matrix**:
  - **allow**:
    - **allow**: 3
    - **modify**: 0
    - **deny**: 0
    - **escalate**: 0
  - **modify**:
    - **allow**: 0
    - **modify**: 2
    - **deny**: 0
    - **escalate**: 0
  - **deny**:
    - **allow**: 0
    - **modify**: 0
    - **deny**: 3
    - **escalate**: 0
  - **escalate**:
    - **allow**: 0
    - **modify**: 0
    - **deny**: 0
    - **escalate**: 2
- **task_recovery_on_real_webots**: True

## Notes

Unblocked 2026-10-01 (previously blocked: no Webots install). Same 10-scenario battery as E6, evaluated against two different Observation sources in the same run for a direct paired comparison, not two separate experiments compared after the fact. MockRobot's starting position is {'x': 0.0, 'y': 0.0, 'z': 0.0} and the real e-puck's is {'x': 0.0, 'y': 1.7815474619152864e-11, 'z': -6.391454876137487e-05} - close enough that distance- and collision-margin-based scenarios (workspace_violation, collision, fast_move_1/2) evaluate identically either way, which is the actual finding: the kernel's decision depends only on the Observation's shape and values, not on which concrete robot interface produced it - confirming E17's Pulse-side finding (test_webots_bridge.py's fake accurately modeled the real controller) also holds at the safety-kernel decision layer, not just the transport layer. task_recovery (a mid-task workspace-violation denial still reaching task_complete) holds through a real physical interface too, matching e05's MockRobot-only finding.

Full per-trial records: `E16_physical_safety_constraint_evaluation.json`
