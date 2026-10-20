# E16: Physical Safety Constraint Evaluation

Generated: 2026-10-07T11:49:29.395610+00:00

## Config

- **evaluation_method**: direct SafetyKernel.admit()/check() calls against MockRobot's and a live MuJoCoRobot's observations side by side, same scenario battery as E6
- **profile**: {'name': 'simulation', 'workspace': {'x': (-2.0, 2.0), 'y': (-2.0, 2.0), 'z': (0.0, 2.0)}, 'max_velocity': 2.0, 'action_timeout_seconds': 0.5, 'approval_required': True, 'collision_margin': 0.3}
- **n_scenarios**: 10
- **robot_interface**: par.robots.mujoco_bridge.MuJoCoRobot against a real, live MuJoCo 3.x process (mujoco/scenes/par_arena.py's Franka Panda scene) via mujoco_bridge.py - not a fake or kinematic stand-in

## Metrics

- **mock_decision_accuracy**: 1.0
- **mujoco_decision_accuracy**: 1.0
- **interfaces_agree_on_all_scenarios**: True
- **mujoco_confusion_matrix**:
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
- **task_recovery_on_real_mujoco**: True

## Notes

Re-run against MuJoCo 2026-10-07 (previously run against Webots 2026-10-01; Webots was then retired entirely). Same 10-scenario battery as E6, evaluated against two different Observation sources in the same run for a direct paired comparison, not two separate experiments compared after the fact. MockRobot's starting position is {'x': 0.0, 'y': 0.0, 'z': 0.0} and the live Franka Panda's end-effector is at {'x': 0.556115276931502, 'y': -3.680265820237325e-05, 'z': 0.6176886395721256} - different values, but distance- and collision-margin-based scenarios (workspace_violation, collision, fast_move_1/2) evaluate identically either way, which is the actual finding: the kernel's decision depends only on the Observation's shape and values, not on which concrete robot interface produced it. This finding is now cross-validated against TWO different real simulators (Webots e-puck in the earlier run, MuJoCo Franka Panda here), each with different base kinematics, different robot classes (differential-drive wheeled vs 7-DOF arm), and different reported-position semantics (base pose vs end-effector pose) - the kernel still decides the same way on the same scenarios. task_recovery (a mid-task workspace-violation denial still reaching task_complete) holds through the arm too, matching e05's MockRobot-only finding and the earlier Webots run.

Full per-trial records: `E16_physical_safety_constraint_evaluation.json`
