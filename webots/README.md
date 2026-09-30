# Webots arena for PAR

Lets PAR (Pulse) drive a real physically-simulated robot (a Webots e-puck)
instead of `MockRobot`, so `move` and the Safety Kernel's collision-margin
denial can be watched live. See [Pulse#10](https://github.com/Anurag9Dhiman/Pulse/pull/10)
for the `WebotsRobot`/`WebotsBridge` adapter this connects to.

**Webots itself is now installed and launches** (R2025a, verified 2026-09-30 —
see Setup step 1 for exactly how). `par_arena.wbt` has not yet been opened in
it and `par_bridge.py` has not yet been run against a real session — see
"Known unknowns" below for what's still unverified. The Python control logic
(differential-drive convergence, object lookup, the WebSocket protocol) is
verified against a fake Webots API that simulates real robot kinematics.

## Setup

1. Install Webots. Homebrew's `webots` cask is disabled (fails Gatekeeper as
   of 2026-09-01), so install directly from the project's GitHub releases
   instead of the cask or the marketing site's download page:

   ```bash
   curl -L -o webots.dmg https://github.com/cyberbotics/webots/releases/download/R2025a/webots-R2025a.dmg
   MOUNT=$(hdiutil attach webots.dmg -nobrowse -plist | plutil -extract 'system-entities.0.mount-point' raw -)
   cp -R "$MOUNT/Webots.app" /Applications/
   hdiutil detach "$MOUNT" -quiet
   xattr -cr /Applications/Webots.app
   rm webots.dmg
   ```

   The last step matters: the `.dmg`'s `Webots.app` is ad-hoc signed, not
   notarized (`codesign -dv` shows `Signature=adhoc`, `TeamIdentifier=not
   set`), so `spctl -a -vv /Applications/Webots.app` will report `rejected`
   regardless — that check alone looks scarier than it is. What actually
   gates a normal launch is the `com.apple.quarantine` extended attribute
   Gatekeeper stamps on anything downloaded via a browser or `curl`;
   `xattr -cr` strips it, and `open /Applications/Webots.app` (or
   double-clicking it in Finder) then launches normally without a
   confirmation dialog — verified working this way on macOS 15.5/arm64. If
   your Mac still blocks it, the fallback is System Settings → Privacy &
   Security → **Open Anyway** (appears after the first blocked attempt).

2. `pip install websockets` into whatever Python will run `par_bridge.py`
   (a plain venv is fine — this script does not need the rest of Pulse
   installed).

3. Set `WEBOTS_HOME` so `from controller import Supervisor` resolves:

   ```bash
   export WEBOTS_HOME=/Applications/Webots.app
   export PYTHONPATH="$WEBOTS_HOME/Contents/lib/controller/python:$PYTHONPATH"
   ```

   (Verified 2026-09-30 against the real R2025a install: the controller
   Python package lives under `Contents/lib/controller/python`, not directly
   under `lib/` as originally guessed here — `Contents/` is where everything
   in a macOS `.app` bundle actually lives. `python3 -c "from controller
   import Supervisor"` succeeds with this path set.)

## Run

1. Open `webots/worlds/par_arena.wbt` in Webots and press Run (▶). The
   e-puck's controller is set to `<extern>`, so Webots will *wait* rather
   than run anything yet.

2. In another terminal (with the env vars from Setup step 3):

   ```bash
   python3 webots/controllers/par_bridge/par_bridge.py
   ```

   It should print `PAR-Webots bridge listening on ws://localhost:6001` and
   the e-puck should stop waiting in Webots.

3. In a third terminal, from `Pulse/`:

   ```bash
   pip install -e ".[webots]"
   python examples/webots_loop.py
   ```

   Watch the Webots window: the e-puck should rotate to face, then drive to,
   a waypoint near `red_object`; then attempt a move directly onto
   `red_object` and get denied (Safety Kernel collision-margin check —
   check the printed output for the denial reason); then drive to a waypoint
   near `blue_container`; then **drive to the `laptop` prop, light its LED,
   and hold there while a real `use_computer` delegation to CollectiveOS
   runs** (see "Physical simulation of the computer-use delegation" below);
   then stop.

## Physical simulation of the computer-use delegation

The `laptop` Solid in `par_arena.wbt` is a stand-in for "the computer" PAR
delegates to via `use_computer`. The e-puck has no arm, so it cannot
literally type on it — what's simulated is **symbolic docking**, not
manipulation: when `ComputerAugmentedRobot` (wrapping `WebotsRobot`) executes
a `use_computer` action, `par_bridge.py`'s `_do_dock_at_computer` drives the
robot to a point ~0.15m from the laptop and lights LED `led0` for the
delegation's duration; `_do_undock_from_computer` turns it off once
CollectiveOS replies (success or failure). This is the whole point of adding
it: without it, the digital half of a mixed physical+digital task is
invisible in the simulation — just a WebSocket call happening off to the
side while the robot body does nothing. With it, "the robot delegates to the
computer" is something you can watch the robot body do (approach, wait,
leave), even though the actual screen-operation happens on the host
machine's real desktop via CollectiveOS's Navigation Agent, not inside
Webots' physics.

This dock/undock step runs regardless of whether CollectiveOS is actually
reachable — `examples/webots_loop.py` will still drive to the laptop and
light the LED even with no CollectiveOS instance running; only the delegated
task's own success/failure depends on that. If you want to see a *real*
delegation complete (not just the physical approach), start CollectiveOS
first (`cd CollectiveOS && uvicorn src.api:app --port 8000`) with
`COLLECTIVEOS_WS_URL`/`COLLECTIVEOS_API_TOKEN` set to match, per
`experiments/README.md`.

## Known unknowns (flag these back if the first run fails here)

Written mostly without a Webots install available (the app itself was
verified 2026-09-30 — see Setup — but `par_arena.wbt` has not yet been
opened in it), so these are still best-effort and each is an easy fix once
Webots' own error message points at it:

- **E-puck PROTO field names** (`controller`, `supervisor`) and the world's
  general node structure (`RectangleArena`, `TexturedBackground`,
  `PBRAppearance`) — standard Webots node/PROTO names, not verified against
  this specific installed version.
- **Motor device names** `"left wheel motor"` / `"right wheel motor"` — the
  standard names in Webots' bundled e-puck samples; if `getDevice()` raises,
  check the e-puck PROTO's device list in Webots' documentation browser.
- **LED device name** `"led0"` — also standard for the bundled e-puck PROTO
  (`led0`-`led7`), used only as a "computer in use" indicator during dock/
  undock. Lower stakes than the motors: `getDevice()` returning `None` for a
  wrong name degrades to "docks silently, no visible light" rather than
  crashing the bridge (see `_EpuckBridge.__init__` and the dock handlers).
- **`coordinateSystem "ENU"`** (Z-up) — chosen to match PAR's existing
  `(x, y)` = ground plane, `z` = height convention. If Webots opens the
  world with unexpected orientation, this is the first thing to check.
- **`Supervisor.SIMULATION_MODE_FAST`** constant name — used once at startup
  to fast-forward the sim; if this raises `AttributeError`, check the
  installed version's `Supervisor` API for the actual constant name and fix
  `par_bridge.py`'s one reference to it.

None of these affect `Pulse/tests/test_webots_bridge.py` (which tests the
Pulse-side adapter against a fake bridge, not real Webots) or the two
scratch verifications run while writing this (differential-drive control
loop convergence against simulated kinematics; the WebSocket
request/response threading end to end against the real `websockets`
library) — both passed before this was written up, using a fake
`controller` module in place of Webots itself.
