# E12: Communication Robustness

Generated: 2026-09-26T23:25:49.201399+00:00

## Config

- **acs**: fake, real WebSocket server (harness/fake_acs_server.py)
- **n_trials_per_condition**: 6
- **conditions**: ['normal', 'increased_latency', 'acs_response_delay', 'packet_loss_approx', 'temporary_disconnection', 'reconnection_after_failure']

## Metrics

- **normal**:
  - **condition**: normal
  - **message_delivery_rate**: 1.0
  - **task_completion_rate**: 1.0
  - **timeout_rate**: 0.0
  - **latency_seconds**:
    - **n**: 6
    - **mean**: 0.002891340166873609
    - **stdev**: 0.004714387547913105
    - **ci95_low**: -0.0008809555208849017
    - **ci95_high**: 0.00666363585463212
- **increased_latency**:
  - **condition**: increased_latency
  - **message_delivery_rate**: 1.0
  - **task_completion_rate**: 1.0
  - **timeout_rate**: 0.0
  - **latency_seconds**:
    - **n**: 6
    - **mean**: 1.0132088198321678
    - **stdev**: 0.002297434520985437
    - **ci95_low**: 1.0113704893495037
    - **ci95_high**: 1.015047150314832
- **acs_response_delay**:
  - **condition**: acs_response_delay
  - **message_delivery_rate**: 1.0
  - **task_completion_rate**: 1.0
  - **timeout_rate**: 0.0
  - **latency_seconds**:
    - **n**: 6
    - **mean**: 3.0118092013314404
    - **stdev**: 0.0017349594033068806
    - **ci95_low**: 3.0104209446790087
    - **ci95_high**: 3.013197457983872
- **packet_loss_approx**:
  - **condition**: packet_loss_approx (~50% connections dropped)
  - **message_delivery_rate**: 0.5
  - **task_completion_rate**: 0.5
- **temporary_disconnection**:
  - **condition**: temporary_disconnection
  - **message_delivery_rate**: 0.0
  - **task_completion_rate**: 0.0
  - **timeout_rate**: 0.0
  - **latency_seconds**:
    - **n**: 6
    - **mean**: 0.0020010975010033385
    - **stdev**: 0.00047354944540835823
    - **ci95_low**: 0.001622179027988716
    - **ci95_high**: 0.002380015974017961
- **reconnection_after_failure**:
  - **condition**: reconnection_after_failure
  - **first_attempt_success**: False
  - **retry_success**: True
  - **recovered**: True

## Notes

'packet_loss_approx' is a per-connection drop probability, not real TCP-level packet loss. 'increased_latency' and 'acs_response_delay' are mechanistically identical from CollectiveOSBridge's point of view (it cannot distinguish network latency from ACS processing time) - kept as two conditions at different magnitudes (1s vs 3s) to match the PDF's naming. reconnection_after_failure confirms recovery is possible, but only because a fresh connection attempt was made against a healthy server - CollectiveOSBridge.run_task() itself makes exactly one attempt and never retries on its own.

Full per-trial records: `E12_communication_robustness.json`
