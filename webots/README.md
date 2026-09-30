# Webots arena for PAR

Lets PAR (Pulse) drive a real physically-simulated robot (a Webots e-puck)
instead of `MockRobot`, so `move` and the Safety Kernel's collision-margin
denial can be watched live. See [Pulse#10](https://github.com/Anurag9Dhiman/Pulse/pull/10)
for the `WebotsRobot`/`WebotsBridge` adapter this connects to.

**Verified end to end against a real Webots R2025a install on 2026-09-30**:
`par_arena.wbt` loads (after adding the `EXTERNPROTO` declarations below —
R2025a no longer resolves those node types implicitly), `par_bridge.py`
connects to the running e-puck, and a real `dock_at_computer` action drove
the physical simulation from `(0, 0)` to `(1.15, -0.97)` — matching the
computed dock point ~0.15m from the `laptop` prop at `(1.3, -1.1)` — with
`undock_from_computer` confirmed working immediately after. See "Known
unknowns" below for the couple of things still untested (mainly cosmetic
texture downloads, which fail over this network but don't affect physics).

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

## Verified against a real install (2026-09-30)

Everything that was previously an open "known unknown" here has now actually
been run and confirmed against Webots R2025a on macOS/arm64:

- **E-puck PROTO field names** (`controller`, `supervisor`), general node
  structure, **motor device names** (`"left wheel motor"` /
  `"right wheel motor"`), **LED device name** (`"led0"`),
  **`coordinateSystem "ENU"`**, and **`Supervisor.SIMULATION_MODE_FAST`** —
  all resolved without needing a single code change; the real
  differential-drive control loop converged and drove the robot to the
  correct real-world coordinates.
- The one thing that *did* need a fix: R2025a requires explicit
  `EXTERNPROTO` declarations for `TexturedBackground`,
  `TexturedBackgroundLight`, `RectangleArena`, `Parquetry`, and `E-puck` —
  see the top of `par_arena.wbt`. Whatever Webots version this file was
  originally authored against must have resolved these implicitly; R2025a
  does not, and says so clearly in its own error output (which is also
  where the exact `EXTERNPROTO` URLs came from).

**Known limitation, not a bug**: cosmetic texture downloads (floor wood
grain, e-puck plastic/copper materials, the gctronic logo decal) fail with
"Connection closed" in this environment — likely an outbound-HTTPS
restriction on `raw.githubusercontent.com` for large binary assets
specifically, since the `EXTERNPROTO` *declarations* themselves (also
fetched from the same host) succeeded. The simulation renders with flat
colors instead of full textures; physics, motors, the LED, and the
WebSocket bridge are all unaffected.

This also confirmed `Pulse/tests/test_webots_bridge.py`'s fake-bridge tests
were accurately modeling the real thing: no gap was found between what the
fake predicted and what the real controller did.
