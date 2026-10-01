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

There are three independent ways to watch `use_computer` happen physically,
sharing the same physical tour but differing in what the digital half
actually is. All three need the e-puck's bridge; the two gantry paths
additionally need `computer_arm_bridge.py`.

**Important**: Webots holds the *entire* simulation paused at t=0 until
*every* extern-controller robot in the world has connected - with both the
e-puck and `computer_arm` present, nothing moves until both bridges are
running, not just the one you're testing.

1. Open `webots/worlds/par_arena.wbt` in Webots and press Run (▶). Both
   robots' controllers are `<extern>`, so Webots will *wait* rather than run
   anything yet.

2. In another terminal (with the env vars from Setup step 3):

   ```bash
   python3 webots/controllers/par_bridge/par_bridge.py
   ```

   It should print `PAR-Webots bridge listening on ws://localhost:6001`.

3. **For the CollectiveOS (real host screen) path**, skip to step 4. **For
   either physically-real gantry path**, also start, in a fourth terminal:

   ```bash
   python3 webots/controllers/computer_arm_bridge/computer_arm_bridge.py
   ```

   It should print `PAR-computer_arm bridge listening on ws://localhost:6002`,
   and only then should the e-puck stop waiting in Webots.

4. In another terminal, from `Pulse/`:

   ```bash
   pip install -e ".[webots]"
   python examples/webots_loop.py             # delegates to real CollectiveOS
   # or:
   python examples/simulated_arm_loop.py      # gantry, keyword-matched button choice
   # or:
   python examples/vision_guided_arm_loop.py  # gantry, Gemini-vision-chosen button
                                               # (needs GEMINI_API_KEY; spends real quota)
   ```

   Watch the Webots window: the e-puck rotates to face, then drives to, a
   waypoint near `red_object`; attempts a move directly onto `red_object`
   and gets denied (Safety Kernel collision-margin check — check the
   printed output for the denial reason); drives to a waypoint near
   `blue_container`; then delegates `use_computer` (see below for what that
   looks like in each mode); then stops.

## Three ways `use_computer` becomes physical

**`examples/webots_loop.py` (default, `CollectiveOSBridge`)** — the digital
half runs on the real host screen. The e-puck can't type, so what's
simulated is **symbolic docking**: `ComputerAugmentedRobot` calls
`WebotsRobot.begin_computer_use()`, which sends `dock_at_computer` to
`par_bridge.py` — it drives to a point ~0.30m from `computer_arm` and
lights LED `led0` for the delegation's duration; `end_computer_use()` turns
it off once CollectiveOS replies (success or failure). This runs regardless
of whether CollectiveOS is reachable — the e-puck still docks and undocks
even with no CollectiveOS instance running; only the delegated task's own
success/failure depends on that. For a *real* delegation to complete, start
CollectiveOS first (`cd CollectiveOS && uvicorn src.api:app --port 8000`)
with `COLLECTIVEOS_WS_URL`/`COLLECTIVEOS_API_TOKEN` set to match, per
`experiments/README.md`.

**`examples/simulated_arm_loop.py` (`PAR_COMPUTER_USE_MODE=simulated_arm`,
`SimulatedArmBridge`)** — physically real, not symbolic, and doesn't touch
the real host screen at all. The e-puck still docks the same way (the hooks
are unchanged), but the actual `use_computer` execution routes to
`computer_arm`'s own 2-axis (X+Z) gantry: `SimulatedArmBridge` maps the
task's text to one of three buttons (`check`/`confirm`/`clear` — keyword
matching against a small fixed vocabulary, not real vision/AI reasoning;
see that file's docstring for the intentional v1 scope), sends
`press_button` to `computer_arm_bridge.py`, which drives the gantry there,
confirms contact with a real `TouchSensor` on the plunger tip, and updates
a small scripted "kiosk" app drawn on `computer_arm`'s `Display`. Verified
end to end 2026-09-30: a real `use_computer("check whether any maintenance
alerts are open")` call produced `"pressed 'check'; kiosk now shows: 1
ALERT: LOW BATTERY"` — a real button, really pressed, really changing a
real (if small) simulated computer's displayed state.

**`examples/vision_guided_arm_loop.py` (`PAR_COMPUTER_USE_MODE=vision_guided_arm`,
`VisionGuidedArmBridge`)** — same physical gantry as above, but *which*
button to press is decided by real Gemini vision instead of keyword
matching: `computer_arm_bridge.py` exposes a `kiosk_camera` `Camera` device
(a child of `computer_arm`, framing the three-button panel) via a
`capture_camera` action; `VisionGuidedArmBridge` fetches that real JPEG,
sends it to `gemini-3.1-flash-lite` alongside the task text and a
`response_schema`-constrained prompt, and presses whichever button Gemini
names (or fails cleanly if it names `"none"`) — the same
real-vision-grounds-the-decision pattern CollectiveOS's own `nav_agent.py`
uses against the real host screen, just scoped to a 3-way choice. Verified
end to end 2026-10-01, starting from the kiosk's genuine idle `"READY"`
state (not staged): Gemini's own stated reasoning was *"The panel is in its
idle state, so the check button must be pressed to view any potential
maintenance alerts"*, it correctly named `check` (not `confirm`, which would
have been wrong from this starting state), and the gantry then pressed it
for real, changing the kiosk to `"1 ALERT: LOW BATTERY"` — confirming the
decision was actually state-grounded, not a lucky guess. Uses
`gemini-3.1-flash-lite` rather than CollectiveOS's `gemini-3.6-flash`
specifically to avoid that model's 20-requests-per-day cap (see
`experiments/README.md`); confirmed by a real call that flash-lite accepts
image input, so no fallback model was needed. This path spends real Gemini
quota (one call per `use_computer` delegation) — `simulated_arm_loop.py`
stays the free/instant alternative for repeated testing.

**Building this uncovered two real, non-obvious mechanics of the gantry
itself**, both found via live Webots runs, not from documentation:
- The originally-calculated press depth (theoretical first contact + a
  9mm overshoot) was **not** reliably enough — the `LinearMotor` has real
  steady-state error under its own weight/friction, so the actual depth
  reached at a commanded position falls short of the command. Only driving
  the joint to its exact `maxStop` reliably produced contact; verified via
  direct `Supervisor.getPosition()` queries that the *geometry* itself was
  correct (sub-5mm clearance) before concluding this was a servo-compliance
  effect, not a calculation error.
- Breaking out of the press-and-poll loop the instant the position sensor
  reports "arrived" can exit before contact force fully develops over a few
  more settling steps — fixed by running a fixed, generous step budget
  instead of exiting on early convergence. See `computer_arm_bridge.py`'s
  `_press_and_watch` docstring.

**Reused port gotcha, worth knowing before debugging something else**: a
Webots instance's connection-slot state for `<extern>` controllers can
accumulate across many relaunches on the *same* port within one working
session — manifesting as silent connection failures or a phantom
"ambiguous extern controller" name list containing robots from previous,
already-closed sessions. If a controller that was working moments ago
suddenly can't connect (or the "Available robots" list mentions a name you
don't recognize), relaunch Webots with a different `--port` rather than
debugging the controller code.

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
