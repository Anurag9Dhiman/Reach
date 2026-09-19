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

- `use_computer` is `risk=HIGH`. Under PAR's `real_robot` profile
  (`approval_required: true`) it escalates to a human before anything is
  dispatched. This matters because CollectiveOS's `/robot/ws` path has no
  approval gate of its own — PAR's Safety Kernel is the only one in the round
  trip. Under the `simulation` profile it runs unattended.
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

- The bridge (`use_computer` capability, `ComputerAugmentedRobot`, per-capability
  execution timeout) is in [Pulse#7](https://github.com/Anurag9Dhiman/Pulse/pull/7),
  pending merge. Until it merges, the pinned `Pulse` commit does not include it.
  After it merges, bump the pin with `git submodule update --remote Pulse`.
- The bridge is unit-tested against a fake CollectiveOS client. A live end-to-end
  run against a running CollectiveOS has **not** been verified yet.
- Robot side is simulated (`MockRobot`); real hardware would go through Pulse's
  ROS 2 adapter.
