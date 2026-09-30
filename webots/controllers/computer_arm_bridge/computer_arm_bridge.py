"""
PAR <-> Webots computer_arm bridge (extern controller).

Sibling to par_bridge.py, same threading skeleton (physics thread owns the
Robot object; a background WebSocket thread puts requests on a queue and
blocks on a per-request Event for the physics thread's reply) - see
par_bridge.py's module docstring for why that split exists.

Drives computer_arm (webots/worlds/par_arena.wbt): a fixed 2-axis (X+Z)
gantry that presses one of three buttons on a kiosk panel, confirmed by a
TouchSensor on the plunger tip, and runs a tiny scripted "app" on the
panel's Display. A plain Robot, not Supervisor - unlike par_bridge.py, this
controller never needs to look up other objects' positions; every
coordinate it uses (button X offsets, press depth) is a fixed constant
matching what's authored in the world file.

Wire protocol:

    {"type": "get_observation"}
        -> {"screen_state": str, "gantry_position": {"x": float, "z": float}}

    {"type": "action", "action_id": str, "skill_name": "press_button",
     "parameters": {"button": "check" | "confirm" | "clear"}}
        -> {"success": bool, "message": str}

Verified against a real Webots R2025a run (2026-09-30): contact detection
requires polling the TouchSensor continuously during the downward move, not
just checking after the motor settles - the contact force is a brief
transient, not a sustained value (found via a throwaway spike before this
file was written; see git history for the spike's 1/10 vs 10/10 result).
"""
from __future__ import annotations

import json
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from controller import Robot  # provided by WEBOTS_HOME on PYTHONPATH
from websockets.sync.server import serve

_HOST = "localhost"
_PORT = 6002

_RUN_IN_FAST_MODE = True

# Button X offsets (m), matching par_arena.wbt's computer_arm exactly.
_BUTTON_X = {
    "check": -0.08,
    "confirm": 0.0,
    "clear": 0.08,
}

_Z_REST = 0.0
# Calculated first-contact point is Z~0.161 (mount height 0.30, minus the
# TouchSensor's -0.015 local offset, minus its 0.004 sphere radius, minus
# the button top at world z=0.12 - all fixed constants from the world
# file), but verified empirically against real Webots that a ~9mm overshoot
# (0.17) is NOT reliably enough - the LinearMotor has real steady-state
# error under its own weight/friction, so the actual depth reached at a
# commanded 0.17 falls short of true contact. 0.19 (maxStop itself) is
# confirmed reliable; this stays a hair under it so the joint is driven
# toward its limit, not commanded to sit exactly on it.
_Z_PRESS = 0.19

_POSITION_TOLERANCE_M = 0.003
# Fixed step budget for the press-and-settle phase - verified empirically
# (80 steps at basicTimeStep=32ms = ~2.56s simulated) rather than exiting
# the instant the position sensor converges; see _press_and_watch.
_PRESS_SETTLE_STEPS = 80
# Hard deadline for one full press_button() call (move to X, press, retract).
# SimulatedArmBridge (Pulse side) budgets its own sequential press count
# against use_computer's 180s Runtime timeout using this constant - keep
# them in sync if either changes.
_MAX_PRESS_SECONDS = 15.0


@dataclass
class _Request:
    message: dict[str, Any]
    done: threading.Event = field(default_factory=threading.Event)
    reply: dict[str, Any] = field(default_factory=dict)


_REQUESTS: "queue.Queue[_Request]" = queue.Queue()


def _ws_handler(websocket) -> None:
    for raw in websocket:
        try:
            message = json.loads(raw)
        except (TypeError, ValueError) as exc:
            websocket.send(json.dumps({"success": False, "message": f"invalid JSON: {exc}"}))
            continue

        request = _Request(message=message)
        _REQUESTS.put(request)
        request.done.wait()
        websocket.send(json.dumps(request.reply))


class _KioskApp:
    """A tiny, deterministic scripted "computer" - no AI, no real screen.
    Genuinely stateful: what's drawn depends on real button presses, not
    decoration. Deliberately simple (see plan's scope note): this stands in
    for a real OS, not a general one."""

    def __init__(self) -> None:
        self.state = "idle"

    def press(self, button: str) -> str:
        if button == "check":
            self.state = "status_shown"
        elif button == "confirm":
            self.state = "confirmed" if self.state == "status_shown" else self.state
        elif button == "clear":
            self.state = "idle"
        return self.screen_text()

    def screen_text(self) -> str:
        return {
            "idle": "READY",
            "status_shown": "1 ALERT: LOW BATTERY",
            "confirmed": "CONFIRMED",
        }[self.state]


class _ComputerArmBridge:
    def __init__(self) -> None:
        self.robot = Robot()
        self.timestep = int(self.robot.getBasicTimeStep())

        self.x_motor = self.robot.getDevice("gantry_x_motor")
        self.x_sensor = self.robot.getDevice("gantry_x_position")
        self.x_sensor.enable(self.timestep)
        self.z_motor = self.robot.getDevice("gantry_z_motor")
        self.z_sensor = self.robot.getDevice("gantry_z_position")
        self.z_sensor.enable(self.timestep)
        self.touch = self.robot.getDevice("plunger_tip")
        self.touch.enable(self.timestep)
        self.display = self.robot.getDevice("kiosk_screen")

        self.kiosk = _KioskApp()
        self._draw_screen()

        if _RUN_IN_FAST_MODE and hasattr(self.robot, "simulationSetMode"):
            # Robot (not Supervisor) may not expose simulation-mode control
            # in every Webots version - best effort, not load-bearing.
            try:
                self.robot.simulationSetMode(Robot.SIMULATION_MODE_FAST)
            except AttributeError:
                pass

    # -- display -----------------------------------------------------------

    def _draw_screen(self) -> None:
        self.display.setColor(0x111111)
        self.display.fillRectangle(0, 0, self.display.getWidth(), self.display.getHeight())
        self.display.setColor(0x30FF30)
        self.display.drawText(self.kiosk.screen_text(), 4, 4)

    # -- state ---------------------------------------------------------------

    def observation_payload(self) -> dict[str, Any]:
        return {
            "screen_state": self.kiosk.state,
            "screen_text": self.kiosk.screen_text(),
            "gantry_position": {"x": self.x_sensor.getValue(), "z": self.z_sensor.getValue()},
        }

    # -- actions ---------------------------------------------------------------

    def run_action(self, skill_name: str, parameters: dict[str, Any]) -> tuple[bool, str]:
        handler = getattr(self, f"_do_{skill_name}", None)
        if handler is None:
            return False, f"computer_arm bridge cannot execute '{skill_name}'"
        return handler(parameters)

    def _move_axis(self, motor, sensor, target: float, deadline: float) -> bool:
        motor.setPosition(target)
        while time.monotonic() < deadline:
            if self.robot.step(self.timestep) == -1:
                return False
            if abs(sensor.getValue() - target) < _POSITION_TOLERANCE_M:
                return True
        return False

    def _press_and_watch(self, deadline: float) -> float:
        """Descends to _Z_PRESS, polling the TouchSensor every step (not
        just after settling - see module docstring), then retracts.

        Deliberately does NOT break out early the moment the position
        sensor reaches _Z_PRESS within tolerance: verified empirically
        against real Webots that contact force can take a few more steps to
        fully develop after the servo first reports "arrived" (settling/
        compression), and exiting right on convergence missed it. Runs a
        fixed, generous step budget instead, bounded by the deadline as a
        safety net, not by early convergence."""
        self.z_motor.setPosition(_Z_PRESS)
        peak_contact = 0.0
        steps = 0
        while time.monotonic() < deadline and steps < _PRESS_SETTLE_STEPS:
            if self.robot.step(self.timestep) == -1:
                break
            peak_contact = max(peak_contact, self.touch.getValue())
            steps += 1
        self._move_axis(self.z_motor, self.z_sensor, _Z_REST, deadline)
        return peak_contact

    def _do_press_button(self, parameters: dict[str, Any]) -> tuple[bool, str]:
        button = parameters.get("button")
        if button not in _BUTTON_X:
            return False, f"unknown button '{button}' - must be one of {sorted(_BUTTON_X)}"

        deadline = time.monotonic() + _MAX_PRESS_SECONDS
        if not self._move_axis(self.x_motor, self.x_sensor, _BUTTON_X[button], deadline):
            return False, f"timed out moving gantry to '{button}'"

        peak_contact = self._press_and_watch(deadline)
        if peak_contact <= 0:
            return False, f"pressed toward '{button}' but no contact was registered"

        screen_text = self.kiosk.press(button)
        self._draw_screen()
        return True, f"pressed '{button}'; screen now shows: {screen_text}"

    def _do_home(self, parameters: dict[str, Any]) -> tuple[bool, str]:
        deadline = time.monotonic() + _MAX_PRESS_SECONDS
        ok_x = self._move_axis(self.x_motor, self.x_sensor, 0.0, deadline)
        ok_z = self._move_axis(self.z_motor, self.z_sensor, _Z_REST, deadline)
        return (ok_x and ok_z), "homed" if (ok_x and ok_z) else "timed out homing gantry"


def main() -> None:
    bridge = _ComputerArmBridge()

    server = serve(_ws_handler, _HOST, _PORT)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"PAR-computer_arm bridge listening on ws://{_HOST}:{_PORT}", flush=True)

    while bridge.robot.step(bridge.timestep) != -1:
        try:
            request = _REQUESTS.get_nowait()
        except queue.Empty:
            continue

        message = request.message
        if message.get("type") == "get_observation":
            request.reply = bridge.observation_payload()
        elif message.get("type") == "action":
            success, msg = bridge.run_action(message.get("skill_name", ""), message.get("parameters", {}))
            request.reply = {"success": success, "message": msg}
        else:
            request.reply = {"success": False, "message": f"unknown request type: {message.get('type')!r}"}
        request.done.set()


if __name__ == "__main__":
    main()
