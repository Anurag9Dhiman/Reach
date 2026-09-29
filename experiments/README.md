# Reach experiments

Implements the 33-experiment evaluation plan for Reach (delivered as
`reach_experiments.pdf`), validating the PAR↔ACS delegation architecture
beyond the single manual live-delegation test the project had before this.

## Setup

```bash
cd Pulse && pip install -e ".[dev,llm,gemini,computer,webots]"
```

Real-ACS experiments (see table below) need `GEMINI_API_KEY` — either export
it, or drop it in a gitignored `experiments/.env` (loaded automatically via
`par.env.load_env()`, same mechanism Pulse's own examples use) — and
CollectiveOS running and reachable (`cd CollectiveOS && uvicorn src.api:app
--port 8000`) with `COLLECTIVEOS_WS_URL`/`COLLECTIVEOS_API_TOKEN` set to
match. Fake-ACS experiments need neither — they run entirely offline against
`harness/fault_bridge.py` or `harness/fake_acs_server.py`.

Run any experiment directly: `python e01_end_to_end_delegation_reliability.py`
(from this directory). Each writes `results/E<NN>_<slug>.json` (full raw
trial records) and `results/E<NN>_<slug>.md` (short summary).

## Why some experiments use a fake ACS instead of the real one

Several experiments' whole research question is about *PAR's own
resilience* to a bad, slow, or flaky ACS — timeouts, malformed replies,
dropped connections, auth failures. You cannot get a real network to drop
packets or a real LLM to return garbage on demand and repeatably, so those
experiments use a controllable double (`harness/fault_bridge.py` for
in-process fault injection, `harness/fake_acs_server.py` for real-WebSocket-
level conditions like latency and concurrent connections) — the same
reasoning chaos-engineering tests use a controlled fault injector rather
than waiting for a real outage. Every result below is labeled **real ACS**
or **fake ACS** so this is never ambiguous.

## Gemini free-tier quota: two separate pools, easy to conflate

Discovered the hard way while running this suite. There are **two
independent quota pools**, not one:

- **`gemini-3.1-flash-lite`** (PAR's own `GeminiPlanner`, used by E1-E3,
  E9-E10, E19, E29) — a **per-minute** limit (observed: 15 req/min). Hitting
  it produces a `429` that clears within a minute; `harness/rate_limit.py`
  paces calls (~4.5s apart) and retries with backoff so a transient hit
  doesn't crash a whole experiment.
- **`gemini-3.6-flash`** (CollectiveOS's `VISION_MODEL`, used internally by
  the real ACS for every delegation) — a **hard 20-requests-PER-DAY** cap on
  the free tier (confirmed from the API's own error response: `quotaId:
  GenerateRequestsPerDayPerProjectPerModel-FreeTier, quotaValue: 20`). This
  is nowhere near what `docs/nav_agent_plan.md`'s "1000 req/day" figure
  suggested — that number doesn't apply to this specific model. A handful of
  real delegation attempts (each involving several perceive/plan/ground/
  verify iterations internally) exhausts it for the rest of the day, and
  CollectiveOS's own retry-with-backoff will spin uselessly on a daily cap
  that a few seconds of waiting can't fix.

**Workaround used for the real-ACS experiments below**: the local test
harness server (not CollectiveOS's committed config) overrides
`VISION_MODEL` to `gemini-3.1-flash-lite` for its own process only, since
that model was empirically handling real traffic fine. This is a real,
disclosed methodological change — real-ACS results below were produced
against a different vision model than CollectiveOS's own configured
default, not `gemini-3.6-flash`. A real deployment hitting this daily cap
would need a paid tier or a similar model swap.

## Status (33 experiments)

Legend: ✅ implemented and run · ⚠️ run, but see caveat · 🚫 blocked (see reason)

**28 of 33 complete** (29 counting E8's automated part separately from its
blocked human-timing sub-part). Every experiment that doesn't require a
Webots install or a real human operator is done. The remaining 5 are
genuinely blocked, not skipped:

| ID | Title | ACS | Status |
|---|---|---|---|
| E1 | End-to-End Delegation Reliability | real | ✅ 12 real trials; failure-cause breakdown found a real intermittent CollectiveOS bug (screenshot capture race, ~1/5 attempts) alongside timeouts and expected `max_iter` outcomes — zero unexplained (see results/E1_*.md) |
| E2 | Mixed Physical-Digital Task Benchmark | real | ✅ 13 real tasks across all 6 categories/3 difficulty levels; 30.8% overall success (single-trial-per-task coverage run, not a reliability study — see E1 for that) |
| E3 | Comparison with a Robot-Only System | fake ACS, real Gemini planner | ✅ |
| E4 | Comparison with Uncontrolled Computer Delegation | fake | ✅ |
| E5 | Safety Kernel Ablation | fake | ✅ |
| E6 | Evaluation of the Four Safety Outcomes | fake | ✅ |
| E7 | Emergency-Stop Safety | n/a | ✅ |
| E8 | Risk-Based Human Escalation | none (direct kernel eval) | ✅ automated part (finds `use_computer` has one fixed risk tag, not content-sensitive — see results/E8_*.md) · 🚫 human-timing part |
| E9 | LLM Delegation Decision | fake ACS, real Gemini planner | ✅ DelegationPrecision=1.0, DelegationRecall=1.0 across 10 scored tasks (3 errored on transient rate limits) |
| E10 | Delegation Decision Ablation | none (single-shot classification) | ✅ conditions 2-4 (observation + capabilities + risk info) are identical in every decision — only adding the observation itself changed anything |
| E11 | Failure Recovery | fake | ✅ (finds a genuine execution failure is terminal within one `run_task()` call by design — recovery only happens via a fresh retry) |
| E12 | Communication Robustness | fake (WS server) | ✅ |
| E13 | Latency Breakdown | fake | ✅ (PAR-side stages only — ACS-internal perceive/plan/ground/verify needs instrumenting CollectiveOS itself, out of scope) |
| E14 | Task Complexity Scaling | fake ACS, scripted planner | ✅ (pipeline scaling only — planner-reasoning-at-scale is E9/E10/E19's job) |
| E15 | Multiple Delegation Cycles | fake ACS, scripted planner | ✅ (empirically confirms task failure probability compounds with delegation count) |
| E16 | Physical Safety Constraint Evaluation (Webots) | — | 🚫 no Webots install |
| E17 | Webots End-to-End Validation | — | 🚫 no Webots install |
| E18 | Physical–Digital Task Execution in Simulation (Webots) | — | 🚫 no Webots install |
| E19 | Planner Comparison | fake ACS, real Gemini + rule-based planners | ✅ rule_based: 0% task success (can't parse natural-language goals or emit task_complete); gemini: 69% — a stark, real finding on planner dependency |
| E20 | ACS Interoperability | fake x2 | ✅ |
| E21 | Capability Abstraction Evaluation | fake | ✅ (structural comparison only — live planner comparison needs quota) |
| E22 | Failure Taxonomy Analysis | fake | ✅ (10 PDF categories collapse to 6 distinguishable from PAR's side; surfaces a new one — PAR accepts incorrect ACS results as success) |
| E23 | Human-in-the-Loop Usability | — | 🚫 needs a real human operator |
| E24 | Multi-Robot Scalability | fake (WS server) | ✅ (100% success, clean scaling through 8 concurrent clients) |
| E25 | Authentication and Request Isolation | fake (WS server) | ✅ (3/6 PDF scenarios not representable — single shared secret, no per-robot identity; confirms a valid token is replayable) |
| E26 | Demonstration Data Generation | real | ✅ 44 real attempts recorded, 14 demonstrations saved (6 done + 8 max_iter); action-type diversity and trajectory-length data in results/E26_*.md |
| E27 | Imitation Learning from Delegated Demonstrations | real data (14 demos) | ✅ small proof-of-concept, per original scope decision — a toy nearest-neighbor lookup over the 14 real demos correctly predicted the held-out task's action type |
| E28 | Demonstration Quality Analysis | real data (14 demos) | ✅ 5 successful-and-efficient, 7 failed (max_iter), 2 unknown (approximate demo↔nav_run cross-reference) |
| E29 | Generalization Across Task Domains | real | ⚠️ inconclusive — 4/5 domains hit a sustained `gemini-3.1-flash-lite` outage (503, persisted across 3 attempts with backoff up to 90s); 1/5 reached a real delegation. See results/E29_*.md — this is an external-service-degradation finding, not a generalization result |
| E30 | Robustness to Observation Noise | none (direct kernel eval) | ✅ (collision check is purely position-based — mislabeling doesn't fool it, but missing/corrupted position data does) |
| E31 | Robustness to ACS Errors | fake | ✅ (PAR accepts incorrect/incomplete/ambiguous ACS results as success identically to a correct one — no semantic verification exists) |
| E32 | End-to-End Robustness Under Combined Failures | fake | ✅ (surfaces a real gap: an all-denials task exhausts `max_steps` stuck at `PLANNING`, neither `DONE` nor `FAILED`) |
| E33 | Overall Systems Benchmark | mixed | ✅ aggregates all 32 others — 28/33 complete, 5/33 blocked, 0 not-yet-run as of this snapshot |

**Blocked (5): E16, E17, E18 need a real Webots install; E23 and E8's
human-timing sub-part need a real human operator running trials personally.
Nothing else in the 33-experiment plan remains to attempt with what's
available in this environment.**

Full experiment specs (research question, design, metrics) are in memory:
[[reach-experiments-overview]] and its five topic files, not duplicated here.
