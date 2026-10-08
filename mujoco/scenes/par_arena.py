"""
MJCF scene composition for the Reach/MuJoCo arena.

Programmatic (via mujoco.MjSpec) rather than a standalone .xml file for two
reasons: (1) the Panda model lives in robot_descriptions' cache directory
(not vendored into this repo), so paths are machine-specific and must be
resolved at runtime; (2) composing in Python avoids the <include>+meshdir
path dance that would otherwise be needed to add our props onto Menagerie's
own panda.xml.

The scene is coordinate-compatible with MockRobot (red_object at
(0.5, 0.2, 0.0), blue_container at (-0.3, 0.4, 0.0)) so experiments and
example tours that targeted these coordinates against the old Webots e-puck
can target them identically against the Panda's end-effector - the Safety
Kernel's collision check cares about the Observation's values and the
Action's target coordinates, not which interface produced them.

Scene elements:
- Franka Emika Panda arm (7-DOF + 2-finger gripper), base at origin
- Floor with a checker pattern, directional light + headlight
- Three Solid prop bodies: red_object (box), blue_container (cylinder),
  laptop (dark box) at coordinates reachable from the Panda base
- Four named keyframes: home, near_red, near_blue, docked_at_laptop,
  each a 9-element qpos (7 arm joints + 2 fingers), hand-picked to be
  visibly-distinct dramatic poses rather than IK-perfect targets - the
  demo's job is to show the governance+delegation story, not sub-cm
  manipulation precision (see the "average suitable" scope note in the
  session plan).
"""
from __future__ import annotations

import mujoco
import numpy as np
from robot_descriptions import panda_mj_description

# World coordinates - red_object and blue_container match MockRobot's defaults
# exactly so e05/e06/E16's existing (expected, actual) scenarios port over
# with zero coordinate changes. red_object sits a hair higher than table
# so its freejoint rests on the floor plane rather than clipping into it.
RED_OBJECT_POS = (0.5, 0.2, 0.025)
BLUE_CONTAINER_POS = (-0.3, 0.4, 0.0)
# Laptop placement differs from Webots (where it was at (1.3, -1.1),
# unreachable for an arm). Here it sits inside the Panda's ~0.85m reachable
# half-sphere so the dock-at-laptop keyframe actually looks like the
# end-effector is attending to it.
LAPTOP_POS = (0.4, -0.5, 0.03)

# Red cube is small enough to fit the Panda gripper (max opening 8cm,
# so a 2.5cm cube leaves comfortable clearance on each side) and dense
# enough that gravity doesn't throw it when the gripper closes abruptly.
_RED_HALF_SIZE = 0.025
_RED_FRICTION = (1.5, 0.03, 0.001)  # higher sliding + torsional friction so the grasp holds under acceleration

OBJECT_NAMES = ("red_object", "blue_container", "laptop")

# Hand-picked joint-space keyframes (9 elements: 7 arm joints + 2 fingers).
# Names are prefixed par_ to avoid colliding with the "home" keyframe the
# Menagerie Panda MJCF already defines (which would be an MJCF repeat-name
# error at compile time). par_home uses the same qpos as Menagerie's own
# "home" so there's no behavioral difference in the ready pose.
# Joint 0 is the base-swivel joint about Z - its angle is set per target to
# atan2(target_y, target_x), i.e. the azimuth from the Panda base to the
# object, so the arm visibly points at the right prop. Joints 1 and 3 are
# tilted/extended slightly from home to lower the end-effector into the
# approach region. Joints 5 and 6 keep a plausible wrist orientation.
KEYFRAMES: dict[str, list[float]] = {
    # home: Menagerie's own ready pose, exact match
    "par_home":             [ 0.000,  0.000,  0.000, -1.571,  0.000,  1.571, -0.785, 0.04, 0.04],
    # red_object at (+0.5, +0.2): azimuth ~ atan2(0.2, 0.5) = +0.38 rad
    "par_near_red":         [ 0.400,  0.300,  0.000, -1.400,  0.000,  1.700, -0.785, 0.04, 0.04],
    # blue_container at (-0.3, +0.4): azimuth ~ atan2(0.4, -0.3) = +2.21 rad
    "par_near_blue":        [ 2.200,  0.300,  0.000, -1.400,  0.000,  1.700, -0.785, 0.04, 0.04],
    # laptop at (+0.4, -0.5): azimuth ~ atan2(-0.5, 0.4) = -0.90 rad
    "par_docked_at_laptop": [-0.900,  0.200,  0.000, -1.300,  0.000,  1.500, -0.785, 0.04, 0.04],

    # Pick-and-place poses. Solved by full 6-DOF IK: constrains BOTH the
    # hand position (3D) and its orientation (quaternion, matching the
    # home-pose "fingertips pointing straight down" orientation), using the
    # Panda's position + rotation Jacobian with damped least squares.
    # Earlier revisions only constrained position - that solved pose but
    # the gripper came out tilted, so closing pushed the cube sideways
    # instead of pinching it. With the orientation constrained, both
    # fingertips land at the same Z (dz=0mm) and the grasp holds.
    "par_above_red":        [+0.190, +0.150, +0.191, -2.245, -0.041, +2.392, -0.377, 0.04, 0.04],
    "par_hover_red":        [+0.248, +0.506, +0.116, -2.239, -0.143, +2.739, -0.305, 0.04, 0.04],
    "par_grasp_red":        [+0.265, +0.583, +0.095, -2.216, -0.153, +2.793, -0.296, 0.04, 0.04],
    "par_above_blue":       [+0.516, -1.375, +1.456, -2.269, +1.348, +1.609, +0.597, 0.04, 0.04],
    "par_hover_blue":       [+0.461, -1.357, +1.770, -2.273, +1.532, +1.859, +0.571, 0.04, 0.04],
    "par_release_blue":     [+0.422, -1.377, +1.863, -2.243, +1.597, +1.919, +0.560, 0.04, 0.04],
}

# End-effector link name in the Panda MJCF, needed for the bridge to report
# a sensible "robot position" in get_observation payloads - the Safety
# Kernel's collision check compares this against detected-object positions.
END_EFFECTOR_BODY = "hand"


def build_model() -> mujoco.MjModel:
    """Loads the Panda spec from robot_descriptions, adds floor, lights,
    props, and keyframes, and compiles. Deterministic - called once at
    bridge startup."""
    spec = mujoco.MjSpec.from_file(panda_mj_description.MJCF_PATH)
    # Bump the offscreen framebuffer so Renderer() calls can request larger
    # images (default is 640x480; a cleaner demo resolution is 1280x720).
    spec.visual.global_.offwidth = 1280
    spec.visual.global_.offheight = 720

    # Visual quality upgrade over the vanilla Panda model: a proper skybox,
    # a checker-pattern floor material, and a directional light. Matches
    # the look of Menagerie's own scene.xml (which we don't include because
    # we want to control the floor and lights ourselves).
    spec.add_texture(
        name="skybox", type=mujoco.mjtTexture.mjTEXTURE_SKYBOX, builtin=mujoco.mjtBuiltin.mjBUILTIN_GRADIENT,
        rgb1=[0.3, 0.5, 0.7], rgb2=[0.0, 0.0, 0.0], width=512, height=3072,
    )
    spec.add_texture(
        name="groundplane", type=mujoco.mjtTexture.mjTEXTURE_2D, builtin=mujoco.mjtBuiltin.mjBUILTIN_CHECKER,
        mark=mujoco.mjtMark.mjMARK_EDGE, rgb1=[0.2, 0.3, 0.4], rgb2=[0.1, 0.2, 0.3],
        markrgb=[0.8, 0.8, 0.8], width=300, height=300,
    )
    spec.add_material(
        name="groundplane", textures=["", "", "groundplane"], texuniform=True,
        texrepeat=[5, 5], reflectance=0.2,
    )

    worldbody = spec.worldbody
    worldbody.add_light(
        pos=[0, 0, 2.0], dir=[0, 0, -1], type=mujoco.mjtLightType.mjLIGHT_DIRECTIONAL,
    )
    worldbody.add_geom(
        name="floor", type=mujoco.mjtGeom.mjGEOM_PLANE, size=[0, 0, 0.05], material="groundplane",
    )

    # red_object: freejoint-equipped graspable cube. The Panda's gripper
    # closes on it and lifts it in the pick-and-place sequence. Non-colliding
    # with the Panda in the home keyframe. Mass + friction tuned so grasp
    # holds under lift acceleration without the cube squirting out.
    red = worldbody.add_body(name="red_object", pos=list(RED_OBJECT_POS))
    red.add_freejoint()
    red.add_geom(
        type=mujoco.mjtGeom.mjGEOM_BOX,
        size=[_RED_HALF_SIZE, _RED_HALF_SIZE, _RED_HALF_SIZE],
        rgba=[0.8, 0.1, 0.1, 1.0],
        friction=list(_RED_FRICTION),
        density=400,  # light enough for the gripper's 100N forcerange to hold reliably
    )

    # blue_container: shallow open bowl built from a floor + 4 thin walls, so
    # the red cube can actually be DROPPED INTO it rather than placed on top.
    # Internal footprint ~10cm x 10cm, walls 4cm tall.
    blue = worldbody.add_body(name="blue_container", pos=list(BLUE_CONTAINER_POS))
    _blue_color = [0.1, 0.2, 0.8, 1.0]
    blue.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, size=[0.055, 0.055, 0.004], pos=[0, 0, 0.004], rgba=_blue_color)
    blue.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, size=[0.055, 0.004, 0.025], pos=[0, 0.055, 0.025], rgba=_blue_color)
    blue.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, size=[0.055, 0.004, 0.025], pos=[0, -0.055, 0.025], rgba=_blue_color)
    blue.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, size=[0.004, 0.055, 0.025], pos=[0.055, 0, 0.025], rgba=_blue_color)
    blue.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, size=[0.004, 0.055, 0.025], pos=[-0.055, 0, 0.025], rgba=_blue_color)

    laptop = worldbody.add_body(name="laptop", pos=list(LAPTOP_POS))
    # Laptop base
    laptop.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, size=[0.12, 0.08, 0.005], rgba=[0.15, 0.15, 0.17, 1.0])
    # Laptop screen (tilted up at ~110 degrees)
    screen = laptop.add_body(pos=[-0.11, 0, 0.065], euler=[0, -0.35, 0])
    screen.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, size=[0.005, 0.08, 0.06], rgba=[0.15, 0.15, 0.17, 1.0])
    screen.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, size=[0.001, 0.075, 0.055], pos=[0.007, 0, 0],
                    rgba=[0.1, 0.3, 0.5, 1.0])

    # Keyframes - these are joint-space poses; `qpos` is 9 elements matching
    # the Panda's 9 DOF (7 arm + 2 finger).
    for name, qpos in KEYFRAMES.items():
        spec.add_key(name=name, qpos=qpos)

    return spec.compile()


def end_effector_world_position(model: mujoco.MjModel, data: mujoco.MjData) -> tuple[float, float, float]:
    """World position of the Panda's hand - used by the bridge as the
    'robot position' in get_observation payloads, so the Safety Kernel's
    collision check compares against something physically meaningful (the
    thing that would actually collide with an object), not the base's
    stationary pose."""
    body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, END_EFFECTOR_BODY)
    pos = data.xpos[body_id]
    return float(pos[0]), float(pos[1]), float(pos[2])


def object_world_position(
    model: mujoco.MjModel, data: mujoco.MjData, name: str
) -> tuple[float, float, float] | None:
    """None if the named body doesn't exist, matching par_bridge.py's
    _object_position contract."""
    body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
    if body_id < 0:
        return None
    pos = data.xpos[body_id]
    return float(pos[0]), float(pos[1]), float(pos[2])


def keyframe_qpos(model: mujoco.MjModel, name: str) -> np.ndarray | None:
    """None if the named keyframe doesn't exist."""
    key_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, name)
    if key_id < 0:
        return None
    return model.key_qpos[key_id].copy()
