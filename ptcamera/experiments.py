"""Controlled experiments and numerical checks; all outputs derive from one config."""

import csv
import hashlib
import json
import platform
from pathlib import Path
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from .config import make_camera, inclusive_grid
from .model import footprint_area

plt.rcParams.update(
    {
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "savefig.dpi": 180,
    }
)


def save_csv(out, name, fields, rows):
    with (out / "data" / f"{name}.csv").open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(fields)
        w.writerows(rows)


def save_figure(out, name, fig):
    fig.tight_layout()
    fig.savefig(out / "figures" / f"{name}.png", facecolor="white")
    fig.savefig(out / "figures" / f"{name}.pdf", facecolor="white")
    plt.close(fig)


def run_experiments(cfg, out):
    out = Path(out)
    for d in ["data", "figures", "media"]:
        (out / d).mkdir(parents=True, exist_ok=True)
    canonical = json.dumps(cfg, sort_keys=True, indent=2) + "\n"
    (out / "config_used.json").write_text(canonical)
    metrics = {
        "config_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "matplotlib": matplotlib.__version__,
    }
    base = make_camera(cfg)
    targets = np.array(cfg["scene"]["targets_m"], dtype=float)
    box = (cfg["scene"]["box_lower_m"], cfg["scene"]["box_upper_m"])
    for p in targets:
        if np.all(p >= np.array(box[0])) and np.all(p <= np.array(box[1])):
            raise ValueError("scene target overlaps solid obstacle")
    z, vis = base.measure(targets, boxes=[box])
    _, infov = base.project(targets)
    save_csv(
        out,
        "scene",
        ["id", "x_m", "y_m", "z_m", "image_x_m", "image_y_m", "in_fov", "visible"],
        [[i, *p, *z[i], int(infov[i]), int(vis[i])] for i, p in enumerate(targets)],
    )
    fig, (a, b) = plt.subplots(1, 2, figsize=(9, 3.8))
    fp = base.footprint()
    closed = np.vstack([fp, fp[0]])
    a.fill(closed[:, 0], closed[:, 1], alpha=0.15, color="tab:blue")
    a.plot(closed[:, 0], closed[:, 1], color="tab:blue")
    a.scatter(
        targets[:, 0], targets[:, 1], c=np.where(vis, "tab:green", "tab:red"), s=50
    )
    a.add_patch(
        plt.Rectangle(
            box[0][:2],
            box[1][0] - box[0][0],
            box[1][1] - box[0][1],
            color="gray",
            alpha=0.7,
        )
    )
    a.plot(*base.position[:2], "^k")
    for i, p in enumerate(targets):
        a.annotate(f"T{i}", p[:2], xytext=(5, 3), textcoords="offset points")
    a.set(
        xlabel="World X (m)",
        ylabel="World Y (m)",
        title="(a) Ground footprint and scene",
    )
    a.set_aspect("equal")
    b.scatter(z[:, 0] * 1000, z[:, 1] * 1000, color="tab:green")
    for i in np.flatnonzero(vis):
        b.annotate(f"T{i}", z[i] * 1000, xytext=(5, 3), textcoords="offset points")
    b.set(
        xlim=(-18, 18),
        ylim=(-12, 12),
        xlabel="Image x (mm)",
        ylabel="Image y (mm)",
        title="(b) Available image positions",
    )
    b.grid(alpha=0.25)
    save_figure(out, "scene", fig)
    metrics["scene"] = {"in_fov": int(infov.sum()), "visible": int(vis.sum())}

    # Height only: independent nadir formula and shoelace footprint calculation.
    hc = cfg["height"]
    hrows = []
    for h in hc["values_m"]:
        c = make_camera(
            cfg, position=(0.0, 0.0, float(h)), pan=0.0, tilt=np.deg2rad(hc["tilt_deg"])
        )
        uv, _ = c.project(hc["target_m"])
        area = footprint_area(c)
        theory = c.width * c.height * h * h / c.focal**2
        expected_x = c.focal * hc["target_m"][0] / h
        hrows.append(
            [h, area, theory, uv[0, 0], expected_x, abs(area - theory) / theory]
        )
    hdata = np.array(hrows)
    save_csv(
        out,
        "height",
        [
            "height_m",
            "area_m2",
            "theory_area_m2",
            "image_x_m",
            "theory_x_m",
            "relative_area_error",
        ],
        hrows,
    )
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.4))
    dense = np.linspace(hdata[0, 0], hdata[-1, 0], 200)
    axs[0].plot(
        dense, base.width * base.height * dense**2 / base.focal**2, label="Theory"
    )
    axs[0].plot(hdata[:, 0], hdata[:, 1], "o", label="Ray intersections")
    axs[0].set(
        xlabel="Height H (m)", ylabel="Footprint area (m²)", title="(a) Nadir coverage"
    )
    axs[1].plot(dense, base.focal * hc["target_m"][0] / dense * 1000, label="Theory")
    axs[1].plot(hdata[:, 0], hdata[:, 3] * 1000, "o", label="Projection")
    axs[1].set(
        xlabel="Height H (m)", ylabel="Image x (mm)", title="(b) Target at (1, 0, 0) m"
    )
    for a in axs:
        a.legend(fontsize=9)
        a.grid(alpha=0.25)
    save_figure(out, "height", fig)
    metrics["height"] = {
        "max_relative_area_error": float(hdata[:, 5].max()),
        "max_projection_error_m": float(abs(hdata[:, 3] - hdata[:, 4]).max()),
        "area_min_m2": float(hdata[0, 1]),
        "area_max_m2": float(hdata[-1, 1]),
        "x_first_mm": float(hdata[0, 3] * 1000),
        "x_last_mm": float(hdata[-1, 3] * 1000),
    }

    # Pan only; fixed scene and fixed LOS geometry. Tilt only; no obstacles.
    pc = cfg["pan"]
    prows = []
    for angle in inclusive_grid(pc["start_deg"], pc["stop_deg"], pc["step_deg"]):
        c = make_camera(cfg, pan=np.deg2rad(angle))
        _, inside = c.project(targets)
        _, seen = c.measure(targets, boxes=[box])
        prows.append([angle, inside.sum(), seen.sum(), footprint_area(c)])
    pdata = np.array(prows)
    save_csv(out, "pan", ["pan_deg", "in_fov_count", "visible_count", "area_m2"], prows)
    tc = cfg["tilt"]
    trows = []
    for angle in inclusive_grid(tc["start_deg"], tc["stop_deg"], tc["step_deg"]):
        c = make_camera(cfg, tilt=np.deg2rad(angle))
        uv, inside = c.project(tc["target_m"])
        trows.append([angle, footprint_area(c), uv[0, 0], uv[0, 1], int(inside[0])])
    tdata = np.array(trows)
    save_csv(
        out, "tilt", ["tilt_deg", "area_m2", "ideal_x_m", "ideal_y_m", "in_fov"], trows
    )
    fig, axs = plt.subplots(1, 3, figsize=(10, 3.2))
    axs[0].step(pdata[:, 0], pdata[:, 1], where="mid", label="Inside FOV")
    axs[0].step(pdata[:, 0], pdata[:, 2], where="mid", label="After LOS")
    axs[0].set(
        xlabel="Pan (deg)", ylabel="Target count", title="(a) Pan only", yticks=range(5)
    )
    axs[0].legend(fontsize=8)
    axs[1].semilogy(tdata[:, 0], tdata[:, 1])
    axs[1].set(
        xlabel="Tilt (deg)", ylabel="Area (m², log scale)", title="(b) Tilt only"
    )
    axs[2].plot(tdata[:, 0], tdata[:, 3] * 1000, label="Ideal projection")
    axs[2].axhline(
        base.height * 500, color="tab:red", linestyle="--", label="Image boundary"
    )
    axs[2].fill_between(
        tdata[:, 0],
        -15,
        25,
        where=tdata[:, 4] == 0,
        color="gray",
        alpha=0.15,
        label="Unavailable",
    )
    axs[2].set(
        xlabel="Tilt (deg)",
        ylabel="Image y (mm)",
        title="(c) Target (0, -8, 0)",
        ylim=(-8, 20),
    )
    axs[2].legend(fontsize=7)
    for a in axs:
        a.grid(alpha=0.25)
    save_figure(out, "orientation", fig)
    metrics["pan"] = {
        "max_relative_area_change": float(
            np.max(abs(pdata[:, 3] - footprint_area(base))) / footprint_area(base)
        ),
        "visible_min": int(pdata[:, 2].min()),
        "visible_max": int(pdata[:, 2].max()),
    }
    metrics["tilt"] = {
        "area_first_m2": float(tdata[0, 1]),
        "area_last_m2": float(tdata[-1, 1]),
        "last_visible_deg": float(tdata[tdata[:, 4] == 1, 0].max()),
        "first_unavailable_deg": float(tdata[tdata[:, 4] == 0, 0].min()),
    }

    # Target only: constant-velocity line, camera fixed, obstacles absent.
    mc = cfg["target_motion"]
    times = inclusive_grid(0, mc["duration_s"], mc["dt_s"])
    path = np.array(mc["start_m"]) + times[:, None] * np.array(mc["velocity_m_s"])
    projected, inside = base.project(path)
    measurements, valid = base.measure(path)
    rows = [[t, *p, *m, int(v)] for t, p, m, v in zip(times, path, measurements, valid)]
    save_csv(
        out,
        "target_motion",
        [
            "time_s",
            "world_x_m",
            "world_y_m",
            "world_z_m",
            "image_x_m",
            "image_y_m",
            "visible",
        ],
        rows,
    )
    # For pan=0, fixed Y and Z, the x boundary follows from the known constant depth.
    phi = base.tilt
    y = path[0, 1] - base.position[1]
    zrel = path[0, 2] - base.position[2]
    depth = -np.sin(phi) * y + np.cos(phi) * zrel
    xlimit = base.width * depth / (2 * base.focal)
    entry = (-xlimit - mc["start_m"][0]) / mc["velocity_m_s"][0]
    leave = (xlimit - mc["start_m"][0]) / mc["velocity_m_s"][0]
    expected = (times >= entry - 1e-12) & (times <= leave + 1e-12)
    metrics["target_motion"] = {
        "samples": len(times),
        "visible_samples": int(valid.sum()),
        "entry_theory_s": float(entry),
        "exit_theory_s": float(leave),
        "first_visible_sample_s": float(times[valid][0]),
        "last_visible_sample_s": float(times[valid][-1]),
        "classification_mismatches": int(np.count_nonzero(valid != expected)),
        "image_speed_mm_s": float(base.focal * mc["velocity_m_s"][0] / depth * 1000),
    }

    # Environment only: vary box height, keep its horizontal extent and target fixed.
    oc = cfg["occlusion"]
    heights = inclusive_grid(
        oc["height_start_m"], oc["height_stop_m"], oc["height_step_m"]
    )
    target = np.array(oc["target_m"], dtype=float)
    # For this scene the segment exits the box y slab at lower_y; that's minimum LOS elevation.
    t_far = (box[0][1] - base.position[1]) / (target[1] - base.position[1])
    threshold = base.position[2] + t_far * (target[2] - base.position[2])
    orows = []
    for h in heights:
        upper = [box[1][0], box[1][1], float(h)]
        m, v = base.measure(target, boxes=[(box[0], upper)])
        orows.append([h, *m[0], int(v[0]), int(h < threshold - 1e-12)])
    odata = np.array(orows)
    save_csv(
        out,
        "occlusion",
        ["box_height_m", "image_x_m", "image_y_m", "visible", "theory_visible"],
        orows,
    )
    metrics["occlusion"] = {
        "critical_height_m": float(threshold),
        "classification_mismatches": int(np.count_nonzero(odata[:, 3] != odata[:, 4])),
        "sampled_first_blocked_m": float(heights[odata[:, 3] == 0][0]),
        "valid_count": int(odata[:, 3].sum()),
    }
    fig, axs = plt.subplots(2, 2, figsize=(9, 5.8))
    axs[0, 0].plot(
        times, projected[:, 0] * 1000, "--", color="gray", label="Ungated projection"
    )
    axs[0, 0].plot(
        times,
        measurements[:, 0] * 1000,
        color="tab:blue",
        label="Available measurement",
    )
    axs[0, 0].axhline(base.width * 500, color="tab:red", lw=0.8)
    axs[0, 0].axhline(-base.width * 500, color="tab:red", lw=0.8)
    axs[0, 0].set(
        xlabel="Time (s)",
        ylabel="Image x (mm)",
        title="(a) Moving target; fixed camera",
    )
    axs[0, 0].legend(fontsize=8)
    axs[0, 1].step(times, valid.astype(int), where="mid")
    axs[0, 1].axvline(
        entry, color="tab:red", linestyle="--", label="Analytic crossings"
    )
    axs[0, 1].axvline(leave, color="tab:red", linestyle="--")
    axs[0, 1].set(
        xlabel="Time (s)",
        ylabel="Availability",
        yticks=[0, 1],
        ylim=(-0.1, 1.2),
        title="(b) FOV entry and exit",
    )
    axs[0, 1].legend(fontsize=8)
    axs[1, 0].plot(
        [base.position[1], target[1]],
        [base.position[2], target[2]],
        color="black",
        label="Sight segment",
    )
    axs[1, 0].add_patch(
        plt.Rectangle(
            (box[0][1], 0),
            box[1][1] - box[0][1],
            threshold,
            facecolor="tab:blue",
            alpha=0.25,
        )
    )
    axs[1, 0].plot(box[0][1], threshold, "ro")
    axs[1, 0].annotate(
        f"Grazing height = {threshold:.1f} m",
        (box[0][1], threshold),
        xytext=(7, 12),
        textcoords="offset points",
        fontsize=8,
    )
    axs[1, 0].set(
        xlabel="World Y (m)", ylabel="World Z (m)", title="(c) Fixed target and camera"
    )
    axs[1, 1].step(heights, odata[:, 3], where="post", label="LOS implementation")
    axs[1, 1].plot(heights, odata[:, 4], "x", markersize=3, label="Analytic prediction")
    axs[1, 1].axvline(threshold, color="tab:red", linestyle="--")
    axs[1, 1].set(
        xlabel="Obstacle height (m)",
        ylabel="Availability",
        yticks=[0, 1],
        ylim=(-0.1, 1.2),
        title="(d) Environment change only",
    )
    axs[1, 1].legend(fontsize=8)
    for a in axs.flat:
        a.grid(alpha=0.25)
    save_figure(out, "motion_occlusion", fig)

    # Noise and local derivative verification are different checks.
    nc = cfg["noise"]
    rng = np.random.default_rng(nc["seed"])
    c = make_camera(cfg, tilt=np.pi)
    points = np.zeros((nc["samples"], 3))
    truth, _ = c.project(points)
    nrows = []
    for sigma in np.array(nc["sigma_mm"]) * 0.001:
        m, _ = c.measure(points, sigma=sigma, rng=rng)
        error = m - truth
        rmse = np.sqrt(np.mean(np.sum(error**2, axis=1)))
        nrows.append([sigma, rmse, np.sqrt(2) * sigma])
    ndata = np.array(nrows)
    save_csv(out, "noise", ["sigma_m", "radial_rmse_m", "population_rms_m"], nrows)
    sc = cfg["sensitivity"]
    world = np.array(sc["camera_points_m"]) @ base.rotation().T + base.position
    analytic = base.projection_jacobian(world)
    jrows = []
    for delta in sc["fd_step_m"]:
        numeric = np.empty_like(analytic)
        for axis in range(3):
            shift = np.eye(3)[axis] * delta
            numeric[:, :, axis] = (
                base.project(world + shift)[0] - base.project(world - shift)[0]
            ) / (2 * delta)
        jrows.append([delta, float(np.max(abs(numeric - analytic)))])
    jdata = np.array(jrows)
    save_csv(out, "jacobian", ["fd_step_m", "max_abs_derivative_error"], jrows)
    metrics["noise"] = {
        "samples_per_condition": nc["samples"],
        "seed": nc["seed"],
        "max_abs_rmse_difference_mm": float(
            np.max(abs(ndata[:, 1] - ndata[:, 2])) * 1000
        ),
        "sigma_max_mm": float(ndata[-1, 0] * 1000),
        "rmse_at_max_sigma_mm": float(ndata[-1, 1] * 1000),
        "max_relative_rmse_difference": float(
            np.max(abs(ndata[1:, 1] / ndata[1:, 2] - 1))
        ),
    }
    metrics["sensitivity"] = {
        "max_error_at_first_step": float(jdata[0, 1]),
        "max_error_at_last_step": float(jdata[-1, 1]),
        "last_step_m": float(jdata[-1, 0]),
        "tested_points": len(world),
    }
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.3))
    axs[0].plot(ndata[:, 0] * 1000, ndata[:, 2] * 1000, label="Population RMS")
    axs[0].plot(ndata[:, 0] * 1000, ndata[:, 1] * 1000, "o", label="Sample RMSE")
    axs[0].set(
        xlabel="Coordinate noise sigma (mm)",
        ylabel="Radial error (mm)",
        title="(a) Noise distribution check",
    )
    axs[0].legend(fontsize=8)
    axs[1].loglog(jdata[:, 0], jdata[:, 1], "o-")
    axs[1].set(
        xlabel="Central-difference step (m)",
        ylabel="Max derivative error (m/m)",
        title="(b) Projection sensitivity check",
    )
    for a in axs:
        a.grid(alpha=0.25)
    save_figure(out, "validation", fig)

    # Fail the pipeline if independent geometric predictions disagree.
    assert metrics["height"]["max_relative_area_error"] < 1e-10
    assert metrics["pan"]["max_relative_area_change"] < 1e-10
    assert metrics["target_motion"]["classification_mismatches"] == 0
    assert metrics["occlusion"]["classification_mismatches"] == 0
    assert metrics["sensitivity"]["max_error_at_last_step"] < 1e-8
    assert metrics["noise"]["max_relative_rmse_difference"] < 0.03
    metrics["experiment_checks_passed"] = 6
    (out / "summary.json").write_text(json.dumps(metrics, indent=2) + "\n")
    return metrics
