"""Shared parameter loading; display degrees are converted exactly once."""

import json
from pathlib import Path
import numpy as np
from .model import Camera

ROOT = Path(__file__).resolve().parents[1]


def load_config(path=None):
    with Path(path or ROOT / "config/experiments.json").open() as f:
        cfg = json.load(f)
    make_camera(cfg)  # validate basic optics
    for section, key in [("target_motion", "dt_s"), ("media", "fps")]:
        if cfg[section][key] <= 0:
            raise ValueError(f"{section}.{key} must be positive")
    # The analytic comparisons below intentionally use these reference geometries.
    # Fail explicitly rather than silently report invalid analytic predictions.
    c = cfg["camera"]
    if c["pan_deg"] != 0 or c["position_m"][:2] != [0, 0]:
        raise ValueError("reference experiments require base pan=0 and Cx=Cy=0")
    if cfg["height"]["tilt_deg"] != 180 or cfg["height"]["target_m"][2] != 0:
        raise ValueError(
            "height-area reference requires a nadir view and ground target"
        )
    m = cfg["target_motion"]
    if (
        m["velocity_m_s"][1:] != [0, 0]
        or m["velocity_m_s"][0] <= 0
        or m["start_m"][2] != 0
    ):
        raise ValueError("target reference is a ground line moving in positive world X")
    return cfg


def make_camera(cfg, **overrides):
    c = cfg["camera"]
    args = dict(
        position=tuple(c["position_m"]),
        pan=np.deg2rad(c["pan_deg"]),
        tilt=np.deg2rad(c["tilt_deg"]),
        focal=c["focal_m"],
        width=c["image_width_m"],
        height=c["image_height_m"],
    )
    args.update(overrides)
    return Camera(**args)


def inclusive_grid(start, stop, step):
    count = int(round((stop - start) / step))
    if step <= 0 or count < 0 or not np.isclose(start + count * step, stop):
        raise ValueError(
            "grid endpoints must be separated by an integer number of positive steps"
        )
    return np.linspace(start, stop, count + 1)
