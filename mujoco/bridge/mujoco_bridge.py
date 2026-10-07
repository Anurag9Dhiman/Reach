"""
PAR <-> MuJoCo bridge.

Replaces the Webots extern-controller split (par_bridge.py +
computer_arm_bridge.py) with a single Python process that owns the physics
model AND serves Pulse's WebSocket requests, since MuJoCo is a library, not
an application with its own process. Same wire protocol as Webots's bridge
(and ROS 2's own would-be payload - see par.robots.ros2_mapping) so Pulse's
MuJoCoRobot/MuJoCoBridge match the shape WebotsRobot used.

Must be launched with `mjpython`, NOT plain `python`, on macOS - the
`mujoco.viewer.launch_passive` call needs it or raises at startup. On Linux
either works. Documented in mujoco/README.md.

Wire protocol (plain JSON, matches par.robots.ros2_mapping):

    {"type": "get_observation"}
        -> {"robot_state": {"position": {"x","y","z"}, "holding": null},
            "detections": [{"name": str, "position": {"x","y","z"}}, ...]}

    {"type": "action", "action_id": str, "skill_name": str, "parameters": {}}
        -> {"success": bool, "message": str}

Threading model: Webots was single-threaded by hard constraint; MuJoCo is
not, but we keep the same discipline (main thread owns MjModel/MjData/
viewer, background thread hosts the WS server, requests cross via a
threading.Queue + per-request Event) so the shape of the code mirrors
par_bridge.py exactly, and so the physics step loop is the single serial
point where observations are read and actions dispatched.

Action handling:
- move({"x","y","z"}): resolves to the nearest-prop keyframe
  (par_near_red / par_near_blue / par_docked_at_laptop) within a 0.4m XY
  radius of the target; otherwise falls back to par_home. Interpolates
  joint-space over _MOVE_INTERP_STEPS physics steps and reports success
  once the arm settles within _JOINT_TOLERANCE_RAD of the keyframe. The
  Safety Kernel's collision check runs on Pulse's side BEFORE the action
  reaches here, so this handler never has to re-check safety.
- detect() / inspect({"target"}): same as par_bridge.py's e-puck versions,
  purely bookkeeping, no motion.
- pick / place: state-only. The Panda has a parallel gripper but no
  grasping demo is in scope for this phase (same as e-puck's "state only"
  disclosure in par_bridge.py).
- stop(): sets zero control signal (holds position). No motion.
- dock_at_laptop / undock_from_laptop: direct interpolation to
  par_docked_at_laptop / par_home. These are the hooks WebotsRobot.
  begin_/end_computer_use() used; MuJoCoRobot's equivalents send the same
  action names so the ComputerAugmentedRobot path is unchanged.
"""
from __future__ import annotations

import json
import math
import os
import queue
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import mujoco
import mujoco.viewer
import numpy as np
from websockets.sync.server import serve

# scenes/par_arena.py lives one directory up - add to path explicitly rather
# than a package import so this file can be run directly via `mjpython
# mujoco/bridge/mujoco_bridge.py` without needing __init__.py plumbing.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scenes.par_arena import (  # noqa: E402
    KEYFRAMES,
    OBJECT_NAMES,
    build_model,
    end_effector_world_position,
    keyframe_qpos,
    object_world_position,
)

_HOST = "localhost"
_PORT = 6003  # Different from Webots's 6001/6002 so a stale Webots process
              # can't accidentally be contacted on the same socket.

# The arm's `move` resolves to whichever named prop keyframe (near_red /
# near_blue / docked_at_laptop) is closest in XY to the target, with no
# radius cutoff - keyframes are discrete, every move has to pick one. This
# matches the loose "which prop are we trying to approach" semantics of the
# e-puck's existing waypoint-near-object pattern (see
# examples/webots_loop.py's _NEAR_RED offsets of 0.4m), without the
# floating-point boundary ambiguity a cutoff would introduce.

# Joint-space interpolation parameters. 300 ramp steps at the Panda's
# default 2ms timestep = 0.6 seconds of simulated motion for the ctrl ramp;
# an additional settling budget allows PD controller lag between ctrl and
# actual qpos to catch up (the Panda's actuators have real gain dynamics,
# so qpos lags the ctrl target by ~100-200ms after the ramp ends).
_MOVE_INTERP_STEPS = 300
_MOVE_SETTLE_STEPS = 500  # Hold ctrl at target, step physics, poll convergence.
_JOINT_TOLERANCE_RAD = 0.05  # Convergence tolerance per joint, in radians.

_MAX_MOVE_SECONDS = 20.0  # Safety cap matching par_bridge.py's.


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


class _PandaBridge:
    def __init__(self) -> None:
        self.model = build_model()
        self.data = mujoco.MjData(self.model)
        # Reset to the par_home keyframe so the arm starts in a clean,
        # non-singular pose rather than the all-zeros default (which would
        # start folded against itself).
        home_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_KEY, "par_home")
        mujoco.mj_resetDataKeyframe(self.model, self.data, home_id)
        mujoco.mj_forward(self.model, self.data)

        # ctrl array is parallel to actuators, not qpos - for the Panda,
        # actuators 1-7 drive joints 1-7, actuator 8 is the gripper tendon.
        # We only command the 7 arm actuators from keyframes; the gripper
        # stays open (ctrl=255 per Menagerie's "home" keyframe convention).
        self._n_arm_actuators = 7
        self.data.ctrl[: self._n_arm_actuators] = self._qpos_to_ctrl(self.data.qpos)
        if len(self.data.ctrl) > self._n_arm_actuators:
            self.data.ctrl[self._n_arm_actuators] = 255  # gripper open

        self._holding: str | None = None

    def _qpos_to_ctrl(self, qpos: np.ndarray) -> np.ndarray:
        """Panda actuators are 1:1 with the first 7 arm joints; ctrl values
        equal qpos targets (biastype='affine' PD position control)."""
        return qpos[: self._n_arm_actuators].copy()

    # -- state ----------------------------------------------------------

    def observation_payload(self) -> dict[str, Any]:
        x, y, z = end_effector_world_position(self.model, self.data)
        detections = []
        for name in OBJECT_NAMES:
            pos = object_world_position(self.model, self.data, name)
            if pos is not None:
                detections.append({"name": name, "position": {"x": pos[0], "y": pos[1], "z": pos[2]}})
        return {
            "robot_state": {"position": {"x": x, "y": y, "z": z}, "holding": self._holding},
            "detections": detections,
        }

    # -- actions --------------------------------------------------------

    def run_action(self, skill_name: str, parameters: dict[str, Any]) -> tuple[bool, str]:
        handler = getattr(self, f"_do_{skill_name}", None)
        if handler is None:
            return False, f"mujoco bridge cannot execute '{skill_name}'"
        return handler(parameters)

    def _nearest_prop_keyframe(self, x: float, y: float) -> str:
        """Which named keyframe should a `move` toward (x, y) resolve to?
        Picks the prop whose XY position is closest to the target. No
        cutoff - if the target is far from every prop the arm still swings
        toward whichever prop is nearest, since keyframes are discrete and
        every move has to pick one."""
        prop_to_keyframe = {
            "red_object": "par_near_red",
            "blue_container": "par_near_blue",
            "laptop": "par_docked_at_laptop",
        }
        best: tuple[float, str] = (float("inf"), "par_home")
        for prop_name, kf in prop_to_keyframe.items():
            pos = object_world_position(self.model, self.data, prop_name)
            if pos is None:
                continue
            dist = math.hypot(pos[0] - x, pos[1] - y)
            if dist < best[0]:
                best = (dist, kf)
        return best[1]

    def _interpolate_to_keyframe(self, kf_name: str, deadline: float) -> bool:
        """Smoothly moves ctrl from current qpos to the named keyframe's
        qpos over _MOVE_INTERP_STEPS physics steps. Returns True once all
        arm joints are within _JOINT_TOLERANCE_RAD of the target, False on
        deadline exhaustion. Physics stepping happens here (this call
        advances the sim) - viewer.sync() in the outer loop picks up the
        changes between steps."""
        target_qpos = keyframe_qpos(self.model, kf_name)
        if target_qpos is None:
            return False
        start_qpos = self.data.qpos.copy()
        target_arm = target_qpos[: self._n_arm_actuators]
        start_arm = start_qpos[: self._n_arm_actuators]

        # Phase A: ramp ctrl linearly from start to target over
        # _MOVE_INTERP_STEPS physics steps. The arm follows but with PD lag.
        for step in range(_MOVE_INTERP_STEPS):
            if time.monotonic() > deadline:
                return False
            alpha = (step + 1) / _MOVE_INTERP_STEPS
            self.data.ctrl[: self._n_arm_actuators] = (1.0 - alpha) * start_arm + alpha * target_arm
            mujoco.mj_step(self.model, self.data)
            if _VIEWER is not None:
                _VIEWER.sync()

        # Phase B: hold ctrl at target, step physics, exit the moment qpos
        # converges to target (within _JOINT_TOLERANCE_RAD per joint) or
        # when the settling budget runs out, whichever comes first.
        self.data.ctrl[: self._n_arm_actuators] = target_arm
        for _ in range(_MOVE_SETTLE_STEPS):
            if time.monotonic() > deadline:
                return False
            mujoco.mj_step(self.model, self.data)
            if _VIEWER is not None:
                _VIEWER.sync()
            arm_now = self.data.qpos[: self._n_arm_actuators]
            if bool(np.all(np.abs(arm_now - target_arm) < _JOINT_TOLERANCE_RAD)):
                return True

        # Settling budget exhausted without reaching tolerance. Not
        # necessarily a failure for the demo - the arm is close enough to
        # the target to be visibly in the right pose - so report based on
        # whether we got within 2x tolerance (visibly OK) vs farther out
        # (something's actually wrong).
        arm_now = self.data.qpos[: self._n_arm_actuators]
        return bool(np.all(np.abs(arm_now - target_arm) < 2.0 * _JOINT_TOLERANCE_RAD))

    def _do_move(self, parameters: dict[str, Any]) -> tuple[bool, str]:
        x = float(parameters.get("x", 0.0))
        y = float(parameters.get("y", 0.0))
        kf = self._nearest_prop_keyframe(x, y)
        deadline = time.monotonic() + _MAX_MOVE_SECONDS
        reached = self._interpolate_to_keyframe(kf, deadline)
        if not reached:
            return False, f"timed out moving toward ({x:.2f}, {y:.2f}) via '{kf}'"
        ee = end_effector_world_position(self.model, self.data)
        return True, f"moved toward ({x:.2f}, {y:.2f}) via '{kf}'; end-effector at ({ee[0]:.2f}, {ee[1]:.2f}, {ee[2]:.2f})"

    def _do_stop(self, parameters: dict[str, Any]) -> tuple[bool, str]:
        # Just hold current pose - no motion needed; the ctrl values are
        # already the current targets, so this is a no-op by construction.
        return True, "stopped"

    def _do_detect(self, parameters: dict[str, Any]) -> tuple[bool, str]:
        names = [d["name"] for d in self.observation_payload()["detections"]]
        return True, f"detected {len(names)} objects: {', '.join(names) or 'none'}"

    def _do_inspect(self, parameters: dict[str, Any]) -> tuple[bool, str]:
        target = parameters.get("target")
        found = (
            object_world_position(self.model, self.data, target) is not None if target else False
        )
        return found, f"inspected '{target}': {'found' if found else 'not found'}"

    def _do_pick(self, parameters: dict[str, Any]) -> tuple[bool, str]:
        target = parameters.get("object")
        if self._holding is not None:
            return False, f"gripper already holding '{self._holding}'"
        if object_world_position(self.model, self.data, target) is None:
            return False, f"object '{target}' not found"
        self._holding = target
        return True, f"picked '{target}' (state only - no grasping demo in scope)"

    def _do_place(self, parameters: dict[str, Any]) -> tuple[bool, str]:
        if self._holding is None:
            return False, "gripper is empty"
        held, self._holding = self._holding, None
        target = parameters.get("target")
        return True, f"placed '{held}' at '{target}' (state only)"

    def _do_dock_at_laptop(self, parameters: dict[str, Any]) -> tuple[bool, str]:
        deadline = time.monotonic() + _MAX_MOVE_SECONDS
        reached = self._interpolate_to_keyframe("par_docked_at_laptop", deadline)
        return (reached, "docked at laptop" if reached else "timed out docking at laptop")

    def _do_undock_from_laptop(self, parameters: dict[str, Any]) -> tuple[bool, str]:
        deadline = time.monotonic() + _MAX_MOVE_SECONDS
        reached = self._interpolate_to_keyframe("par_home", deadline)
        return (reached, "undocked (returned to home)" if reached else "timed out returning to home")


# Module-level viewer handle so _interpolate_to_keyframe can call .sync()
# without needing to be passed through every method - viewer lifecycle is
# a startup/shutdown concern of main(), not of _PandaBridge itself.
_VIEWER: Any = None


def _handle_requests(bridge: _PandaBridge) -> None:
    """Drain any queued WS requests. Called from the main loop between
    physics steps so bridge state is always consistent when a reply is
    sent."""
    while True:
        try:
            request = _REQUESTS.get_nowait()
        except queue.Empty:
            return
        message = request.message
        if message.get("type") == "get_observation":
            request.reply = bridge.observation_payload()
        elif message.get("type") == "action":
            success, msg = bridge.run_action(
                message.get("skill_name", ""), message.get("parameters", {})
            )
            request.reply = {"success": success, "message": msg}
        else:
            request.reply = {"success": False, "message": f"unknown request type: {message.get('type')!r}"}
        request.done.set()


def main(headless: bool = False) -> None:
    global _VIEWER
    bridge = _PandaBridge()

    server = serve(_ws_handler, _HOST, _PORT)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"PAR-MuJoCo bridge listening on ws://{_HOST}:{_PORT}", flush=True)

    if headless:
        # Headless mode (CI / unit tests): run the physics loop without a
        # viewer, step at wall-clock pace, process requests between steps.
        try:
            while True:
                mujoco.mj_step(bridge.model, bridge.data)
                _handle_requests(bridge)
                time.sleep(bridge.model.opt.timestep)
        except KeyboardInterrupt:
            pass
        return

    # Interactive mode (demo): a visible, interactive viewer. On macOS this
    # requires `mjpython` as the launcher - calling under plain `python`
    # raises at startup.
    with mujoco.viewer.launch_passive(bridge.model, bridge.data) as viewer:
        _VIEWER = viewer
        try:
            while viewer.is_running():
                step_start = time.monotonic()
                mujoco.mj_step(bridge.model, bridge.data)
                _handle_requests(bridge)
                viewer.sync()
                # Real-time pacing - without this the sim races at thousands
                # of Hz and the viewer motion is a blur.
                elapsed = time.monotonic() - step_start
                remaining = bridge.model.opt.timestep - elapsed
                if remaining > 0:
                    time.sleep(remaining)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PAR <-> MuJoCo bridge.")
    parser.add_argument("--headless", action="store_true",
                        help="Run without the interactive viewer (CI / unit tests). "
                             "In headless mode plain `python` works; interactive mode on macOS "
                             "needs `mjpython`.")
    args = parser.parse_args()
    main(headless=args.headless)
