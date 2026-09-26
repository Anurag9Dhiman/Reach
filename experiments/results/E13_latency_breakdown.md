# E13: Latency Breakdown

Generated: 2026-09-26T23:26:40.793525+00:00

## Config

- **acs**: fake (FaultyCollectiveOSBridge with a known injected delay, to sanity-check measurement accuracy)
- **n_trials_per_skill**: 10
- **injected_acs_delay_seconds**: 0.5
- **scope_note**: ACS-internal stages (perception/planning/GUI execution/verification) are not measurable from PAR's side - see module docstring

## Metrics

- **use_computer**:
  - **planner_decision**:
    - **n**: 10
    - **mean**: 0.014724024999304674
    - **stdev**: 0.000774826612998768
    - **ci95_low**: 0.014243782489101848
    - **ci95_high**: 0.015204267509507501
    - **p95**: 0.015082292011356913
    - **p99**: 0.015082292011356913
  - **safety_admission**:
    - **n**: 10
    - **mean**: 8.074170036707074e-05
    - **stdev**: 3.090880357483386e-05
    - **ci95_low**: 6.158422543381373e-05
    - **ci95_high**: 9.989917530032775e-05
    - **p95**: 0.00012495899864006788
    - **p99**: 0.00012495899864006788
  - **safety_policy**:
    - **n**: 10
    - **mean**: 8.62079905346036e-06
    - **stdev**: 2.268660079529744e-06
    - **ci95_low**: 7.214668968209866e-06
    - **ci95_high**: 1.0026929138710854e-05
    - **p95**: 1.141701068263501e-05
    - **p99**: 1.141701068263501e-05
  - **network_and_acs**:
    - **n**: 10
    - **mean**: 0.5067227251041914
    - **stdev**: 0.003995082817759466
    - **ci95_low**: 0.5042465471197471
    - **ci95_high**: 0.5091989030886356
    - **p95**: 0.5101873330131639
    - **p99**: 0.5101873330131639
  - **result_processing**:
    - **n**: 10
    - **mean**: 1.1999960406683386e-06
    - **stdev**: 1.7035813792834373e-06
    - **ci95_low**: 1.4410536242291635e-07
    - **ci95_high**: 2.2558867189137607e-06
    - **p95**: 5.915993824601173e-06
    - **p99**: 5.915993824601173e-06
  - **total**:
    - **n**: 10
    - **mean**: 0.5215373125989572
    - **stdev**: 0.004376376135050309
    - **ci95_low**: 0.5188248065680219
    - **ci95_high**: 0.5242498186298925
    - **p95**: 0.5253164169989759
    - **p99**: 0.5253164169989759
- **detect_physical_only**:
  - **planner_decision**:
    - **n**: 10
    - **mean**: 0.01390024170250399
    - **stdev**: 0.0018314381566939737
    - **ci95_low**: 0.012765104572600902
    - **ci95_high**: 0.015035378832407078
    - **p95**: 0.015026042005047202
    - **p99**: 0.015026042005047202
  - **safety_admission**:
    - **n**: 10
    - **mean**: 5.0670899508986625e-05
    - **stdev**: 1.829807836842036e-05
    - **ci95_low**: 3.93296330370873e-05
    - **ci95_high**: 6.201216598088595e-05
    - **p95**: 9.06249915715307e-05
    - **p99**: 9.06249915715307e-05
  - **safety_policy**:
    - **n**: 10
    - **mean**: 6.0707985539920625e-06
    - **stdev**: 9.95563506996951e-07
    - **ci95_low**: 5.453741899450815e-06
    - **ci95_high**: 6.68785520853331e-06
    - **p95**: 7.70798942539841e-06
    - **p99**: 7.70798942539841e-06
  - **network_and_acs**:
    - **n**: 10
    - **mean**: 1.5904201427474617e-05
    - **stdev**: 7.419871603704504e-06
    - **ci95_low**: 1.130531736158697e-05
    - **ci95_high**: 2.0503085493362264e-05
    - **p95**: 3.4374999813735485e-05
    - **p99**: 3.4374999813735485e-05
  - **result_processing**:
    - **n**: 10
    - **mean**: 3.0829833121970294e-07
    - **stdev**: 4.034834181524158e-08
    - **ci95_low**: 2.8329016987005644e-07
    - **ci95_high**: 3.3330649256934944e-07
    - **p95**: 3.7500285543501377e-07
    - **p99**: 3.7500285543501377e-07
  - **total**:
    - **n**: 10
    - **mean**: 0.013973195900325664
    - **stdev**: 0.0018230428065962782
    - **ci95_low**: 0.01284326226232297
    - **ci95_high**: 0.015103129538328357
    - **p95**: 0.01513025000167545
    - **p99**: 0.01513025000167545

## Notes

network_and_acs dominates total latency for use_computer (as expected, given a 0.5s injected delay vs single-digit-millisecond planner/safety overhead), and the measured network_and_acs mean tracks the injected delay closely, which is the accuracy check this was designed to provide. For detect (a pure physical skill with no network component), network_and_acs is ~0 and total latency is dominated by the simulated planner 'thinking time' (10ms, a stand-in for what would be a real LLM call's latency in production). This does not include CollectiveOS's own internal perceive/plan/ground/verify breakdown - that requires instrumenting CollectiveOS directly, out of scope here.

Full per-trial records: `E13_latency_breakdown.json`
