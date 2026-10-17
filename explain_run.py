"""Readable experiment entry point: python explain_run.py"""
import os
os.environ.setdefault('MPLCONFIGDIR', '/tmp/pt-camera-mpl')
os.environ.setdefault('XDG_CACHE_HOME', '/tmp/pt-camera-cache')
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from camera import Camera

OUT = Path(__file__).resolve().parent / 'results'
OUT.mkdir(exist_ok=True)
TARGETS = np.array([[-2, -5, 0], [0, -8, 0], [3, -10, 0], [1, -4, 0]])
BOX = ((-1, -5, 0), (1, -3, 4))


def scene_experiment():
    camera = Camera()
    measurements, visible = camera.measure(TARGETS, boxes=[BOX])
    footprint = camera.footprint()
    footprint = np.vstack([footprint, footprint[0]])
    fig, (world, image) = plt.subplots(1, 2, figsize=(11, 5))
    world.fill(footprint[:, 0], footprint[:, 1], alpha=0.2)
    world.plot(footprint[:, 0], footprint[:, 1])
    world.scatter(TARGETS[:, 0], TARGETS[:, 1], c=np.where(visible, 'green', 'red'))
    world.scatter(0, 0, marker='^', color='black')
    world.add_patch(plt.Rectangle(BOX[0][:2], 2, 2, color='gray', alpha=0.6))
    for i, point in enumerate(TARGETS):
        world.text(point[0] + 0.3, point[1], str(i))
    world.set(xlabel='World X (m)', ylabel='World Y (m)', title='Ground FOV and targets')
    world.set_aspect('equal')
    image.scatter(measurements[:, 0] * 1000, measurements[:, 1] * 1000)
    for i in np.flatnonzero(visible):
        image.text(measurements[i, 0] * 1000, measurements[i, 1] * 1000, str(i))
    image.set(xlim=(-18, 18), ylim=(-12, 12), xlabel='Image x (mm)', ylabel='Image y (mm)', title='Available image measurements')
    image.grid()
    fig.tight_layout()
    fig.savefig(OUT / '01_scene.png', dpi=160)
    plt.close(fig)
    print('Scene visibility:', visible.tolist())
    print('Image measurements (mm):\n', measurements * 1000)


def pan_experiment():
    rows = []
    for angle in np.linspace(-60, 60, 121):
        camera = Camera(pan=np.deg2rad(angle))
        _, in_fov = camera.project(TARGETS)
        _, visible = camera.measure(TARGETS, boxes=[BOX])
        rows.append([angle, in_fov.sum(), visible.sum()])
    data = np.array(rows)
    np.savetxt(OUT / '02_pan.csv', data, delimiter=',', header='pan_deg,in_fov,visible', comments='')
    fig, ax = plt.subplots()
    ax.step(data[:, 0], data[:, 1], where='mid', label='Inside FOV')
    ax.step(data[:, 0], data[:, 2], where='mid', label='Visible after occlusion')
    ax.set(xlabel='Pan (deg)', ylabel='Number of targets', title='Orientation and visibility')
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / '02_pan.png', dpi=160)
    plt.close(fig)


def noise_experiment():
    rng = np.random.default_rng(4810)
    camera = Camera(tilt=np.pi)
    points = np.zeros((10000, 3))
    truth, _ = camera.project(points)
    rows = []
    for sigma in np.array([0, .02, .05, .1, .2, .5]) * .001:
        measurements, _ = camera.measure(points, sigma=sigma, rng=rng)
        error = measurements - truth
        rmse = np.sqrt(np.mean(np.sum(error**2, axis=1)))
        rows.append([sigma, rmse, np.sqrt(2) * sigma])
    data = np.array(rows)
    np.savetxt(OUT / '03_noise.csv', data, delimiter=',', header='sigma_m,radial_rmse_m,theory_m', comments='')
    fig, ax = plt.subplots()
    ax.plot(data[:, 0] * 1000, data[:, 1] * 1000, 'o', label='Simulation')
    ax.plot(data[:, 0] * 1000, data[:, 2] * 1000, label='Theory: sqrt(2) sigma')
    ax.set(xlabel='Noise sigma (mm)', ylabel='Radial image RMSE (mm)', title='10000 samples per condition')
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / '03_noise.png', dpi=160)
    plt.close(fig)
    print('Noise table: sigma / RMSE / theory (mm)\n', data * 1000)


if __name__ == '__main__':
    scene_experiment()
    pan_experiment()
    noise_experiment()
    print('Results saved to:', OUT)
