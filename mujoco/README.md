# Reach / MuJoCo physical simulation

A Franka Emika Panda arm (via the MuJoCo Menagerie) stands in for a physical
robot so Pulse's `move`, Safety Kernel behavior, and real `use_computer`
delegations to CollectiveOS can all be watched live - replacing the earlier
Webots e-puck integration (deleted 2026-10-07 for both cleaner visuals and
one less install dependency on this macOS/arm64 development machine).

## What's in here

- `scenes/par_arena.py` - Programmatic MJCF scene builder (via
  `mujoco.MjSpec`). Composes the Menagerie Panda with a floor, lights, and
  three named props (`red_object`, `blue_container`, `laptop`) at
  coordinates matching `MockRobot`'s defaults, plus four named joint-space
  keyframes for scripted motion (`par_home`, `par_near_red`, `par_near_blue`,
  `par_docked_at_laptop`). Scene is Python-first, not an .xml file, because
  the Panda MJCF lives in the `robot_descriptions` cache rather than
  being vendored into this repo.
- `bridge/mujoco_bridge.py` - the WebSocket server + physics-step loop that
  Pulse's `MuJoCoBridge`/`MuJoCoRobot` talk to. Single Python process (no
  extern-controller split like Webots had); background thread hosts the WS
  server, main thread owns `MjModel`/`MjData` and (in interactive mode)
  the viewer.

## Setup

```bash
cd ../Pulse
pip install -e ".[dev,mujoco]"
```

That brings in `mujoco>=3.2` and `robot_descriptions>=1.11`. The first time
you import `robot_descriptions.panda_mj_description`, it clones the whole
MuJoCo Menagerie repo into `~/.cache/robot_descriptions/` (~2 minutes,
one-time, happens automatically). After that, cold starts are instant.

Nothing else to install - no Homebrew cask, no Gatekeeper dance, no second
language, no system-level dependencies.

## Run

Two independent processes, same split Webots used:

1. **The MuJoCo bridge** (physics + viewer):

   ```bash
   # Interactive (opens a window - what you want for the demo):
   mjpython mujoco/bridge/mujoco_bridge.py

   # Headless (CI / unit tests - no window):
   python mujoco/bridge/mujoco_bridge.py --headless
   ```

   Note the `mjpython` for the interactive case. On macOS,
   `mujoco.viewer.launch_passive` requires the `mjpython` launcher shipped
   with the `mujoco` wheel - plain `python` raises at startup. On Linux,
   either works. Both forms print
   `PAR-MuJoCo bridge listening on ws://localhost:6003` once ready.

2. **Pulse** (any script that uses `MuJoCoRobot`), from `Pulse/`:

   ```bash
   python examples/mujoco_loop.py
   ```

   Watch the viewer window: the arm detects three props, swings its
   end-effector toward a waypoint near `red_object` (allowed), attempts a
   move directly onto `red_object` and gets denied (Safety Kernel collision-
   margin check - check the printed output for the denial reason), swings
   toward `blue_container`, then delegates `use_computer` (which drives the
   end-effector to the laptop prop via `MuJoCoRobot.begin_computer_use`).
   Whether the delegated computer-use task itself succeeds depends on
   whether CollectiveOS is reachable - the physical dock-at-laptop happens
   either way.

   For a *real* use_computer delegation, start CollectiveOS first (`cd
   ../CollectiveOS && uvicorn src.api:app --port 8000`) with
   `COLLECTIVEOS_WS_URL`/`COLLECTIVEOS_API_TOKEN` set to match -
   `examples/mujoco_loop.py` uses the default `CollectiveOSBridge`.

## How `use_computer` becomes physical (one path, down from three)

The paper's architecture couples a `use_computer` delegation to a visible
physical gesture via the optional `begin_computer_use`/`end_computer_use`
hooks on the robot interface. `MuJoCoRobot` implements them: before the
delegation, the arm's end-effector interpolates to the `par_docked_at_laptop`
keyframe (visibly reaching the laptop prop); after the delegation returns,
it interpolates back to `par_home`. This replaces the earlier three-mode
system (`PAR_COMPUTER_USE_MODE=collectiveos|simulated_arm|vision_guided_arm`)
with one default path - the paper's governance+delegation story is cleaner
without the gantry/keyword-matching/vision-guided-button-choice variants
that used to live alongside, and the arm's dock-at-laptop keyframe makes
the hand-off visibly physical in a way the e-puck's LED+symbolic docking
couldn't.

## Why MuJoCo (and not Webots any more)

- **Visuals**: Webots in this environment couldn't load its own PBR
  textures (floor appeared flat grey, Panda-equivalent would've looked
  worse); MuJoCo renders cleanly on this exact machine with real materials,
  shadow casting, and a usable free camera out of the box.
- **Install path**: Webots needed a GitHub-release `.dmg` download +
  manual `xattr -cr` Gatekeeper clearance (Homebrew cask is disabled since
  2026-09); MuJoCo is `pip install mujoco`, native arm64 wheel, zero sudo.
- **Architecture**: Webots's extern-controller model forced two separate
  controller processes to connect before the simulation would even step;
  MuJoCo is a library, so the bridge is a single Python process - fewer
  moving parts, no "neither bridge connected yet" footgun.
- **Visual fidelity for a research-paper demo**: a 7-DOF Franka arm
  dramatically swinging between props and docking at a laptop reads as a
  real robotics demo in a way a 2-wheeled e-puck + a decorative colored
  box arena did not.

## Known limitations / honest caveats

- The arm's `move` resolves to one of four named joint-space keyframes
  (home, near_red, near_blue, docked_at_laptop) rather than solving IK to
  an arbitrary end-effector target. This is explicit scope - keyframes are
  authored once in `scenes/par_arena.py` and all `move` calls snap to the
  nearest one. The Safety Kernel's collision check still fires correctly
  against the real end-effector position vs. real detected-object positions
  (that logic is interface-agnostic by design - see Pulse's
  `ros2_mapping.py`), it's only the physical reach that's discretized.
- No grasping. The `pick`/`place` skills return success as pure state
  bookkeeping, matching the e-puck's own disclosed scope in the earlier
  Webots integration.
- `use_computer` in interactive mode: CollectiveOS's nav loop can run
  longer than Pulse's 180s `use_computer` timeout for complex tasks, which
  Runtime then reports as `action timed out`. The ACS itself still
  completes its own loop and saves a demonstration - this is a Pulse-side
  timeout, not an ACS failure. Three ways to get a reliably-successful demo:
  (a) pick a short real task (e.g. "which application is currently in the
  foreground?" finishes in ~30s against Gemini and returns a correct answer
  - verified live 2026-10-08); (b) set `UITARS_BASE_URL` in CollectiveOS's
  `.env` to point at a local UI-TARS vLLM server (faster per-step than
  Gemini, no per-day quota cap); (c) edit the `use_computer` capability's
  `execution_timeout_seconds` in `par.skills.computer_use` to raise the
  180s budget.

## Pick-and-place manipulation

A `pick_and_place({object, target})` skill is wired for the `red_object` ->
`blue_container` pair: the arm approaches the cube from above (via two
hover keyframes to keep the descent close to a straight vertical line in
Cartesian space, since joint-space interpolation between distant poses can
sweep the gripper sideways through the cube), closes the gripper, lifts,
carries over to the bowl, lowers, opens the gripper, and verifies the
cube landed inside the bowl's XY bounds before reporting success. The
keyframes were solved by full 6-DOF IK (position + orientation) against
the Panda's position-and-rotation Jacobian - earlier revisions used only
position IK and the resulting tilted gripper pushed the cube out when
closing. The red cube's `density=400` and `friction=(1.5, 0.03, 0.001)`
are tuned so the grasp holds under lift acceleration without tweaking the
Panda's actuator gains.
