"""Records a short animated GIF of the Pulse-driven arena tour: home ->
near_red (ALLOW) -> [onto_red DENIED by Safety Kernel, no arm motion] ->
near_blue -> docked_at_laptop -> home. Standalone (does not need the
mujoco_bridge or a Pulse Runtime running); produces one artifact for the
paper and for quick visual verification.

Run with:
    python scripts/record_demo_video.py             # writes paper/figures/tour.gif
    python scripts/record_demo_video.py --out X.gif # custom path
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import mujoco
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mujoco"))
from scenes.par_arena import KEYFRAMES, build_model  # noqa: E402

# 25 fps (= one rendered frame per 20 physics steps at MuJoCo's default
# 2 ms timestep). High enough to look smooth; low enough to keep the GIF
# small for the paper.
_FRAME_EVERY_N_STEPS = 20
_FRAME_MS = 40  # 1000 / 25 = 40 ms per frame

# Each tour step: (label, target_keyframe, physics_steps_to_interpolate).
# Non-moving beats (DENIED, HOLD) advance physics with ctrl held at the
# previous target, so the viewer gets a visible pause instead of a jump.
_TOUR: list[tuple[str, str | None, int]] = [
    ("home (initial)",                "par_home",             200),
    ("hold at home",                  None,                   100),
    ("move near red_object",          "par_near_red",         500),
    ("hold near red",                 None,                   100),
    ("[DENIED by Safety Kernel]",     None,                   150),  # no motion - this IS the governance
    ("move near blue_container",      "par_near_blue",        700),
    ("hold near blue",                None,                   100),
    ("dock at laptop (use_computer)", "par_docked_at_laptop", 600),
    ("hold at laptop (delegating)",   None,                   200),
    ("undock to home",                "par_home",             500),
]

_WIDTH, _HEIGHT = 960, 540
_N_ARM_ACTUATORS = 7


def main() -> None:
    parser = argparse.ArgumentParser()
    default_out = Path(__file__).resolve().parent.parent / "paper" / "figures" / "tour.gif"
    parser.add_argument("--out", default=str(default_out))
    args = parser.parse_args()

    model = build_model()
    data = mujoco.MjData(model)

    # Start at par_home.
    home_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_KEY, "par_home")
    mujoco.mj_resetDataKeyframe(model, data, home_id)
    data.ctrl[:_N_ARM_ACTUATORS] = KEYFRAMES["par_home"][:_N_ARM_ACTUATORS]
    if len(data.ctrl) > _N_ARM_ACTUATORS:
        data.ctrl[_N_ARM_ACTUATORS] = 255  # gripper open
    mujoco.mj_forward(model, data)

    renderer = mujoco.Renderer(model, height=_HEIGHT, width=_WIDTH)
    frames: list[Image.Image] = []

    for label, target_keyframe, n_steps in _TOUR:
        print(f"  {label} ({n_steps} steps)...")
        start_ctrl = data.ctrl[:_N_ARM_ACTUATORS].copy()
        if target_keyframe is not None:
            target_arm = np.array(KEYFRAMES[target_keyframe][:_N_ARM_ACTUATORS])
        else:
            target_arm = start_ctrl.copy()  # hold - no change

        for step in range(n_steps):
            if target_keyframe is not None:
                alpha = (step + 1) / n_steps
                data.ctrl[:_N_ARM_ACTUATORS] = (1.0 - alpha) * start_ctrl + alpha * target_arm
            mujoco.mj_step(model, data)
            if step % _FRAME_EVERY_N_STEPS == 0:
                renderer.update_scene(data, camera=-1)
                frames.append(Image.fromarray(renderer.render()))

    print(f"\nRendered {len(frames)} frames; writing GIF to {args.out}")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        args.out,
        save_all=True,
        append_images=frames[1:],
        duration=_FRAME_MS,
        loop=0,
        optimize=False,
    )
    size_mb = Path(args.out).stat().st_size / (1024 * 1024)
    print(f"Done. {len(frames)} frames, ~{size_mb:.1f} MB")


if __name__ == "__main__":
    main()
