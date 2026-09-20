# Reach

**Robot Learning to Use a Computer.** Reach simulates a normal robot that gains
the ability to use a computer as one more tool. The robot still sees and acts in
the physical world; when a task needs a computer — reading a machine's
software, entering a measurement into an application, opening a webpage,
submitting a report — it asks **PAR** to invoke a separate **Autonomous Computer
System**. PAR connects the two and manages execution and feedback.

```
Robot sees physical world
        ↓
Robot needs computer
        ↓
PAR calls Autonomous Computer System
        ↓
Computer performs the digital task
        ↓
Result comes back through PAR
        ↓
Robot continues its physical task
```

We are not training the robot to become a computer agent from scratch. We give
it computer-use capability through PAR, which governs when and how the digital
world is integrated into the physical one.

## Repositories

Both are included as git submodules, pinned to `main`.

| Repo | Role |
|---|---|
| [Pulse](https://github.com/Anurag9Dhiman/Pulse) | **PAR — Physical Agent Runtime.** The governing framework: `Observation → Agent → Skill → Safety → Action`. Decides whether a computer step is allowed and dispatches it. |
| [CollectiveOS](https://github.com/Anurag9Dhiman/CollectiveOS) | **Autonomous Computer System.** Its Navigation Agent performs screen-level computer tasks (perceive → plan → act) and records each run as a demonstration. |

## How they connect

PAR exposes computer use to the robot's planner as one more capability,
`use_computer`. When the planner picks it, PAR sends the task to CollectiveOS's
`/robot/ws` WebSocket, blocks until the Navigation Agent finishes, and feeds the
text result back into the loop so the robot can continue its physical task.

- `use_computer` is `risk=HIGH`. Whenever the active PAR profile has
  `approval_required: true` it escalates to a human before anything is
  dispatched. This matters because CollectiveOS's `/robot/ws` path has no
  approval gate of its own — PAR's Safety Kernel is the only one in the round
  trip. With `approval_required: false` (the stock `simulation` profile) it
  runs unattended.
- Each run is recorded to CollectiveOS's `data/demonstrations/`, which is the
  data trail for the robot *learning* to use a computer.

## Quickstart

```bash
git clone --recurse-submodules https://github.com/Anurag9Dhiman/Reach.git
cd Reach
```

Start CollectiveOS (set `API_TOKEN` in its `.env`, plus whichever model key its
Navigation Agent needs):

```bash
cd CollectiveOS
pip install -r requirements.txt
cp .env.example .env
uvicorn src.api:app --port 8000
```

In another shell, run PAR against it:

```bash
cd Pulse
pip install -e ".[llm,computer]"
export ANTHROPIC_API_KEY=...
export COLLECTIVEOS_WS_URL=ws://localhost:8000/robot/ws
export COLLECTIVEOS_API_TOKEN=...   # same value as CollectiveOS's API_TOKEN
python examples/computer_use_loop.py
```

## Status

Two PRs need to merge before the quickstart works from a fresh clone:

- [Pulse#7](https://github.com/Anurag9Dhiman/Pulse/pull/7) adds the bridge
  (`use_computer` capability, `ComputerAugmentedRobot`, per-capability
  execution timeout).
- [CollectiveOS#119](https://github.com/Anurag9Dhiman/CollectiveOS/pull/119)
  fixes `/robot/ws`, which raised `NameError` on every connection.

Until both merge, the pinned submodule commits don't include them. After they
merge, bump the pins with `git submodule update --remote` and commit.

Verified so far:

- The bridge is unit-tested against a fake CollectiveOS client.
- A live round trip works over a real local socket: PAR's runtime and
  WebSocket client against CollectiveOS's real `/robot/ws` route, with only the
  Navigation Agent call stubbed.

Not verified yet: the real Navigation Agent (Gemini + desktop control) and the
LLM planner choosing `use_computer` on its own. The robot side is simulated
(`MockRobot`); real hardware would go through Pulse's ROS 2 adapter.
