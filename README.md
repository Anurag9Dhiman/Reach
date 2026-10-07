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

Pulse and CollectiveOS are included as git submodules, pinned to `main`.

| Repo | Role |
|---|---|
| [Pulse](https://github.com/Anurag9Dhiman/Pulse) | **PAR — Physical Agent Runtime.** The governing framework: `Observation → Agent → Skill → Safety → Action`. Decides whether a computer step is allowed and dispatches it. |
| [CollectiveOS](https://github.com/Anurag9Dhiman/CollectiveOS) | **Autonomous Computer System.** Its Navigation Agent performs screen-level computer tasks (perceive → plan → act) and records each run as a demonstration. |

`mujoco/` (in this repo, not a submodule) is an MJCF scene builder + bridge
giving PAR a real physically-simulated robot (a Franka Emika Panda arm via
the MuJoCo Menagerie) to drive instead of an in-memory mock — see "Robot
simulation" below.

## How PAR and CollectiveOS connect

PAR exposes computer use to the robot's planner as one more capability,
`use_computer`. When the planner picks it, PAR sends the task to CollectiveOS's
`/robot/ws` WebSocket, blocks until the Navigation Agent finishes, and feeds the
text result back into the loop so the robot can continue its physical task.

- `use_computer` is `risk=HIGH`, so it escalates for human approval whenever
  the active PAR profile has `approval_required: true`. This matters because
  CollectiveOS's `/robot/ws` path has no approval gate of its own — PAR's
  Safety Kernel is the only one in the round trip.
- Each run is recorded to CollectiveOS's `data/demonstrations/`, which is the
  data trail for the robot *learning* to use a computer.
- **Verified with a real run**: PAR delegated a read-only task ("which
  application is in the foreground?") to CollectiveOS's real Navigation Agent
  (Gemini). The correct answer came back through PAR. Not yet verified: PAR's
  LLM planner choosing `use_computer` on its own (tested with a scripted
  planner so far), and a task where the Navigation Agent actually clicks or
  types.

## Robot simulation

`MockRobot` (Pulse's default) is an in-memory stand-in with no physics or
rendering — useful for the loop's logic, useless for watching whether `move`
or the Safety Kernel's collision-margin denial does something sensible. So
PAR can also drive a real physically-simulated robot: a Franka Emika Panda
arm in MuJoCo, bridged in over a plain WebSocket
(`mujoco/bridge/mujoco_bridge.py`, connects to Pulse's `MuJoCoRobot`). This
reuses Pulse's ROS 2 JSON mapping schema unchanged, over WebSocket instead
of ROS 2 topics — this machine has no ROS 2 (no official macOS/arm64
build), which is why it isn't `ROS2Robot` directly.

MuJoCo was picked over Webots (the earlier integration, retired 2026-10-07)
because its `pip install mujoco` works out of the box on this macOS/arm64
machine, textures and materials actually render (Webots couldn't load its
own PBR textures in this environment), and a 7-DOF Franka arm swinging
dramatically between props reads as a real robotics demo in a way a
two-wheeled e-puck did not. See `mujoco/README.md` for setup, run steps,
and the explicit scope choices (joint-space keyframes instead of IK, no
grasping).

## Quickstart

```bash
git clone --recurse-submodules https://github.com/Anurag9Dhiman/Reach.git
cd Reach
```

**Computer-use bridge** — start CollectiveOS (set `API_TOKEN` and
`GEMINI_API_KEY` in its `.env`; also set `VISION_MODEL=gemini-3.6-flash` —
the default `gemini-2.0-flash` returned 404 "no longer available to new
users" for a new key when this was tested):

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

**Robot simulation** — see `mujoco/README.md`, then:

```bash
cd Pulse
pip install -e ".[mujoco]"
# Terminal A - bridge + viewer (mjpython required on macOS for the window):
mjpython ../mujoco/bridge/mujoco_bridge.py
# Terminal B - run the demo:
python examples/mujoco_loop.py
```

## Status

- Computer-use bridge (`use_computer`, `ComputerAugmentedRobot`) — merged,
  verified live.
- MuJoCo bridge (`MuJoCoRobot`, `mujoco/`) — merged, verified live against
  a real MuJoCo installation (Franka Panda Menagerie model, full
  physical-tour-+-delegation end to end).
- Robot side has two options now: `MockRobot` (default, no physics) or
  `MuJoCoRobot` (real physics + viewer). Real hardware would go through
  Pulse's ROS 2 adapter — not available on this dev machine.
