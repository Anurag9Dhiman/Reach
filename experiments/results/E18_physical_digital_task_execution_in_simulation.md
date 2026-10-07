# E18: Physical-Digital Task Execution in Simulation

Generated: 2026-10-07T11:53:54.078598+00:00

## Config

- **evaluation_method**: one real Runtime.run_task() through ComputerAugmentedRobot(MuJoCoRobot()) with the default CollectiveOSBridge, against a live MuJoCo process AND a live CollectiveOS instance simultaneously
- **profile**: simulation
- **delegated_task**: check whether any maintenance alerts are open

## Metrics

- **task_reached_complete**: False
- **near_red_allowed_and_succeeded**: True
- **collision_correctly_denied**: True
- **near_blue_allowed_and_succeeded**: True
- **real_acs_delegation_succeeded**: False
- **real_acs_delegation_latency_seconds**: 180.00915724999868
- **stop_succeeded**: None
- **all_checks_passed**: False

## Notes

Re-run against MuJoCo 2026-10-07 (previously attempted 3x against Webots 2026-10-01; all 3 Webots-era attempts had their physical half succeed cleanly but their digital half fail with identical Gemini 503 'high demand' errors across both quota pools - a sustained external outage, not a Reach-side bug). This re-run runs the full composed loop: the Franka Panda arm navigates toward each prop, gets a live collision denial from the safety kernel against a real detected-object position, docks its end-effector at the simulated laptop prop, then delegates a genuine digital subtask to a live CollectiveOS instance (real screenshot, real vision model, real pyautogui automation on the host desktop) and continues the physical task afterward. Delegated task: 'check whether any maintenance alerts are open'. Result message: 'action timed out'.

Full per-trial records: `E18_physical_digital_task_execution_in_simulation.json`
