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

CollectiveOS's free-tier `GEMINI_API_KEY` has a real daily quota (~1000
req/day). More importantly: several experiments' whole research question is
about *PAR's own resilience* to a bad, slow, or flaky ACS — timeouts,
malformed replies, dropped connections, auth failures. You cannot get a real
network to drop packets or a real LLM to return garbage on demand and
repeatably, so those experiments use a controllable double
(`harness/fault_bridge.py` for in-process fault injection,
`harness/fake_acs_server.py` for real-WebSocket-level conditions like
latency and concurrent connections) — the same reasoning chaos-engineering
tests use a controlled fault injector rather than waiting for a real outage.
Every result below is labeled **real ACS** or **fake ACS** so this is never
ambiguous.

## Status (33 experiments)

Legend: ✅ implemented and run · ⚠️ run, but see caveat · ⏳ not yet implemented · 🚫 blocked (see reason)

**Quota caveat (2026-09-27): the shared free-tier `GEMINI_API_KEY` ran out
mid-run** during E1 (7/12 delegations hit hard `429 RESOURCE_EXHAUSTED`, 4
hit transient `503`, 1 timed out — zero were unexplained). Every
real-ACS/real-Gemini-planner experiment below not yet run is blocked on the
daily quota resetting (or a different key). Fake-ACS and no-ACS experiments
are unaffected and make up most of the list.

| ID | Title | ACS | Status |
|---|---|---|---|
| E1 | End-to-End Delegation Reliability | real | ⚠️ ran; 0/12 task success, 100% attributable to free-tier quota exhaustion/transient overload (see results/E1_*.md) — needs a clean re-run once quota resets for a real reliability signal |
| E2 | Mixed Physical-Digital Task Benchmark | real | 🚫 blocked on quota reset |
| E3 | Comparison with a Robot-Only System | fake ACS, real Gemini planner | ✅ |
| E4 | Comparison with Uncontrolled Computer Delegation | fake | ✅ |
| E5 | Safety Kernel Ablation | fake | ✅ |
| E6 | Evaluation of the Four Safety Outcomes | fake | ✅ |
| E7 | Emergency-Stop Safety | n/a | ✅ |
| E8 | Risk-Based Human Escalation | none (direct kernel eval) | ✅ automated part (finds `use_computer` has one fixed risk tag, not content-sensitive — see results/E8_*.md) · 🚫 human-timing part |
| E9 | LLM Delegation Decision | fake ACS, real Gemini planner | 🚫 blocked on quota reset |
| E10 | Delegation Decision Ablation | fake ACS, real Gemini planner | 🚫 blocked on quota reset |
| E11 | Failure Recovery | fake | ⏳ |
| E12 | Communication Robustness | fake (WS server) | ⏳ |
| E13 | Latency Breakdown | fake | ⏳ |
| E14 | Task Complexity Scaling | fake | ⏳ |
| E15 | Multiple Delegation Cycles | fake | ⏳ |
| E16 | Physical Safety Constraint Evaluation (Webots) | — | 🚫 no Webots install |
| E17 | Webots End-to-End Validation | — | 🚫 no Webots install |
| E18 | Physical–Digital Task Execution in Simulation (Webots) | — | 🚫 no Webots install |
| E19 | Planner Comparison | fake ACS, real Gemini planner | 🚫 blocked on quota reset (GeminiPlanner vs RuleBasedPlanner only — no second LLM key available) |
| E20 | ACS Interoperability | fake x2 | ⏳ |
| E21 | Capability Abstraction Evaluation | fake | ⏳ |
| E22 | Failure Taxonomy Analysis | fake | ⏳ |
| E23 | Human-in-the-Loop Usability | — | 🚫 needs a real human operator |
| E24 | Multi-Robot Scalability | fake (WS server) | ⏳ |
| E25 | Authentication and Request Isolation | fake (WS server) | ⏳ |
| E26 | Demonstration Data Generation | real | 🚫 blocked on quota reset |
| E27 | Imitation Learning from Delegated Demonstrations | real (data) | 🚫 blocked on quota reset (small proof-of-concept only, per scope decision — needs E26's data first) |
| E28 | Demonstration Quality Analysis | real (data) | 🚫 blocked on quota reset (needs E26's data first) |
| E29 | Generalization Across Task Domains | real | 🚫 blocked on quota reset |
| E30 | Robustness to Observation Noise | fake | ⏳ |
| E31 | Robustness to ACS Errors | fake | ⏳ |
| E32 | End-to-End Robustness Under Combined Failures | fake | ⏳ |
| E33 | Overall Systems Benchmark | mixed | ⏳ (aggregates the above — run last) |

**Done so far: 7/33 fully run (E3, E4, E5, E6, E7, E8-automated), 1/33 run
with a documented caveat (E1), 4/33 blocked on Webots/human (E16, E17, E18,
E23), 6/33 blocked on today's quota (E2, E9, E10, E19, E26, E29 — plus E27,
E28 which also need E26's output). 15/33 not yet started, all fake-ACS/no-ACS
(no quota dependency) — next up.**

Full experiment specs (research question, design, metrics) are in memory:
[[reach-experiments-overview]] and its five topic files, not duplicated here.
