"""
PAR <-> Webots bridge (extern controller).

Runs as a normal Python process outside Webots (WEBOTS_HOME must be on
PYTHONPATH so `from controller import Supervisor` resolves - see
webots/README.md). Drives the e-puck robot defined in par_arena.wbt
(controller "<extern>", supervisor TRUE) and serves it to PAR's
WebotsRobot/WebotsBridge (Pulse/src/par/robots/webots_bridge.py,
Pulse/src/par/integrations/webots.py) over a plain WebSocket.

Wire protocol (matches par.robots.ros2_mapping's payload shape exactly, so
the schema is transport-agnostic - see that module's docstring for why):

    {"type": "get_observation"}
        -> {"robot_state": {"position": {"x","y","z"}, "holding": str|null},
            "detections": [{"name": str, "position": {"x","y","z"}}, ...]}

    {"type": "action", "action_id": str, "skill_name": str, "parameters": {}}
        -> {"success": bool, "message": str}

Threading model: Webots' controller API is single-threaded by design, so one
thread (the main thread, "the physics thread" below) owns the Supervisor
object and is the only thing that ever calls into it. The WebSocket server
runs in a background thread; each connection handler puts a request onto
`_REQUESTS` and blocks on a per-request threading.Event for the physics
thread's reply, rather than touching Supervisor itself.

Not yet run against a real Webots install while writing this (none available
in the dev environment this was authored in - see the Pulse PR this ships
alongside). Device names ("left wheel motor" / "right wheel motor"), the
Supervisor field names, and the coordinate/yaw math below are all standard
for Webots' bundled E-puck sample worlds, but treat the first real run as a
debugging pass, not a guarantee.
"""
from __future__ import annotations

import json
import math
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from controller import Supervisor  # provided by WEBOTS_HOME on PYTHONPATH
from websockets.sync.server import serve

_HOST = "localhost"
_PORT = 6001

_OBJECT_NAMES = ("red_object", "blue_container")

# e-puck's real max wheel speed is slow (~0.13 m/s); fast-forwarding the
# simulation keeps a `move` maneuver from eating PAR's action timeout budget
# in wall-clock time without changing anything about the physics itself.
_RUN_IN_FAST_MODE = True

_HEADING_TOLERANCE_RAD = 0.05
_DISTANCE_TOLERANCE_M = 0.05
_TURN_SPEED = 2.0   # rad/s of wheel rotation while turning in place
_DRIVE_SPEED = 6.0  # rad/s of wheel rotation while driving straight
_MAX_MOVE_SECONDS = 30.0  # safety cap so a bad heading calc can't spin forever


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


class _EpuckBridge:
    def __init__(self) -> None:
        self.robot = Supervisor()
        self.timestep = int(self.robot.getBasicTimeStep())

        self.left_motor = self.robot.getDevice("left wheel motor")
        self.right_motor = self.robot.getDevice("right wheel motor")
        for motor in (self.left_motor, self.right_motor):
            motor.setPosition(float("inf"))
            motor.setVelocity(0.0)

        self.self_node = self.robot.getSelf()
        self._holding: str | None = None

        if _RUN_IN_FAST_MODE:
            self.robot.simulationSetMode(Supervisor.SIMULATION_MODE_FAST)

    # -- state ----------------------------------------------------------

    def _position(self) -> tuple[float, float, float]:
        x, y, z = self.self_node.getPosition()
        return x, y, z

    def _yaw(self) -> float:
        # 3x3 rotation matrix, row-major; yaw about Z for an ENU (Z-up) world.
        r = self.self_node.getOrientation()
        return math.atan2(r[3], r[0])

    def _object_position(self, name: str) -> tuple[float, float, float] | None:
        # par_arena.wbt names these Solid nodes via their `name` field, not a
        # DEF identifier, so this looks them up by that field rather than
        # via getFromDef().
        root = self.robot.getRoot().getField("children")
        for i in range(root.getCount()):
            node = root.getMFNode(i)
            name_field = node.getField("name")
            if name_field is not None and name_field.getSFString() == name:
                x, y, z = node.getPosition()
                return x, y, z
        return None

    def observation_payload(self) -> dict[str, Any]:
        x, y, z = self._position()
        detections = []
        for name in _OBJECT_NAMES:
            position = self._object_position(name)
            if position is not None:
                detections.append({"name": name, "position": {"x": position[0], "y": position[1], "z": position[2]}})
        return {
            "robot_state": {"position": {"x": x, "y": y, "z": z}, "holding": self._holding},
            "detections": detections,
        }

    # -- actions ----------------------------------------------------------

    def run_action(self, skill_name: str, parameters: dict[str, Any]) -> tuple[bool, str]:
        handler = getattr(self, f"_do_{skill_name}", None)
        if handler is None:
            return False, f"webots bridge cannot execute '{skill_name}'"
        return handler(parameters)

    def _set_wheel_velocity(self, left: float, right: float) -> None:
        self.left_motor.setVelocity(left)
        self.right_motor.setVelocity(right)

    def _do_stop(self, parameters: dict[str, Any]) -> tuple[bool, str]:
        self._set_wheel_velocity(0.0, 0.0)
        return True, "stopped"

    def _do_move(self, parameters: dict[str, Any]) -> tuple[bool, str]:
        target_x = float(parameters.get("x", 0.0))
        target_y = float(parameters.get("y", 0.0))
        deadline = time.monotonic() + _MAX_MOVE_SECONDS

        while time.monotonic() < deadline:
            x, y, _ = self._position()
            dx, dy = target_x - x, target_y - y
            distance = math.hypot(dx, dy)
            if distance < _DISTANCE_TOLERANCE_M:
                self._set_wheel_velocity(0.0, 0.0)
                return True, f"reached ({target_x:.2f}, {target_y:.2f})"

            heading_error = _wrap_angle(math.atan2(dy, dx) - self._yaw())
            if abs(heading_error) > _HEADING_TOLERANCE_RAD:
                turn = _TURN_SPEED if heading_error > 0 else -_TURN_SPEED
                self._set_wheel_velocity(-turn, turn)
            else:
                self._set_wheel_velocity(_DRIVE_SPEED, _DRIVE_SPEED)

            if self.robot.step(self.timestep) == -1:
                return False, "Webots simulation stopped mid-move"

        self._set_wheel_velocity(0.0, 0.0)
        return False, f"timed out driving toward ({target_x:.2f}, {target_y:.2f})"

    def _do_detect(self, parameters: dict[str, Any]) -> tuple[bool, str]:
        names = [d["name"] for d in self.observation_payload()["detections"]]
        return True, f"detected {len(names)} objects: {', '.join(names) or 'none'}"

    def _do_inspect(self, parameters: dict[str, Any]) -> tuple[bool, str]:
        target = parameters.get("target")
        found = self._object_position(target) is not None if target else False
        return found, f"inspected '{target}': {'found' if found else 'not found'}"

    def _do_pick(self, parameters: dict[str, Any]) -> tuple[bool, str]:
        target = parameters.get("object")
        if self._holding is not None:
            return False, f"gripper already holding '{self._holding}'"
        if self._object_position(target) is None:
            return False, f"object '{target}' not found"
        self._holding = target
        return True, f"picked '{target}' (state only - e-puck has no gripper)"

    def _do_place(self, parameters: dict[str, Any]) -> tuple[bool, str]:
        if self._holding is None:
            return False, "gripper is empty"
        held, self._holding = self._holding, None
        target = parameters.get("target")
        return True, f"placed '{held}' at '{target}' (state only - e-puck has no gripper)"


def _wrap_angle(angle: float) -> float:
    return (angle + math.pi) % (2 * math.pi) - math.pi


def main() -> None:
    bridge = _EpuckBridge()

    server = serve(_ws_handler, _HOST, _PORT)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"PAR-Webots bridge listening on ws://{_HOST}:{_PORT}", flush=True)

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
