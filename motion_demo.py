"""Time-driven 3D PT visualization; open-loop kinematics, not motor dynamics."""
import os
os.environ.setdefault('MPLCONFIGDIR', '/tmp/pt-motion-mpl')
os.environ.setdefault('XDG_CACHE_HOME', '/tmp/pt-motion-cache')
from pathlib import Path
import csv
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter, FFMpegWriter
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from camera import Camera

BOX = ((-.8, -5.2, 0.), (.8, -4., 4.))
PERIOD = 12.
FPS = 10


def state(t):
    """Prescribed smooth camera angles and independent moving ground targets."""
    phase = 2 * np.pi * t / PERIOD
    camera = Camera(pan=np.deg2rad(35 * np.sin(phase)),
                    tilt=np.deg2rad(147 + 8 * np.sin(phase + .7)))
    targets = np.array([
        [-1 + 5 * np.cos(phase), -8 + 1.5 * np.sin(phase), 0.],
        [3 * np.sin(phase + 1.3), -11 + 2 * np.cos(phase + 1.3), 0.]
    ])
    return camera, targets


def box_faces(lower, upper, rotation=None, offset=None):
    lo, hi = np.asarray(lower), np.asarray(upper)
    pts = np.array([[x, y, z] for x in (lo[0], hi[0])
                    for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    if rotation is not None:
        pts = pts @ rotation.T + offset
    return [pts[idx] for idx in ([0, 1, 3, 2], [4, 5, 7, 6],
                                [0, 1, 5, 4], [2, 3, 7, 6],
                                [0, 2, 6, 4], [1, 3, 7, 5])]


def main():
    out = Path(__file__).resolve().parent / 'outputs' / 'motion'
    out.mkdir(parents=True, exist_ok=True)
    times = np.arange(int(PERIOD * FPS)) / FPS
    states = [state(t) for t in times]
    tracks = np.array([targets for _, targets in states])
    angles = np.rad2deg([[c.pan, c.tilt] for c, _ in states])
    measured = [c.measure(p, boxes=[BOX]) for c, p in states]
    statuses = []
    rows = []
    for k, (c, targets) in enumerate(states):
        _, in_fov = c.project(targets)
        z, visible = measured[k]
        statuses.append(['VISIBLE' if visible[i] else ('OCCLUDED' if in_fov[i] else 'OUTSIDE FOV') for i in range(2)])
        for i in range(2):
            rows.append([times[k], *angles[k], i, *targets[i],
                         *z[i], int(in_fov[i]), int(visible[i]), statuses[-1][i]])
    with (out/'measurements.csv').open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['time_s','pan_deg','tilt_deg','target_id','world_x_m','world_y_m','world_z_m','image_x_m','image_y_m','in_fov','visible','status'])
        w.writerows(rows)

    fig = plt.figure(figsize=(12, 7), facecolor='#f7f9fc')
    gs = fig.add_gridspec(2, 2, width_ratios=[1.35, 1], height_ratios=[1.5, 1])
    world = fig.add_subplot(gs[:, 0], projection='3d')
    sensor = fig.add_subplot(gs[0, 1])
    control = fig.add_subplot(gs[1, 1])
    title = fig.suptitle('', fontsize=15)
    fig.subplots_adjust(left=.03, right=.96, top=.88, bottom=.13, wspace=.24, hspace=.46)
    fig.text(.04, .025, 'Prescribed motion | Ideal pinhole + geometric LOS | Noise off | No motor controller or real-image validation', fontsize=10)
    colors = ['#15803d', '#7c3aed']

    def draw(k):
        camera, targets = states[k]
        z, visible = measured[k]
        for ax in (world, sensor, control):
            ax.clear()
        title.set_text(f'PT camera: moving body, viewing frustum and targets   |   t = {times[k]:.1f} s')
        C = np.asarray(camera.position)
        fp = camera.footprint()
        assert np.isfinite(fp).all(), 'Demo requires finite ground footprint'
        world.add_collection3d(Poly3DCollection([fp], facecolor='#38bdf8', alpha=.13))
        for p in fp:
            world.plot(*np.stack([C, p]).T, color='#0284c7', alpha=.5, linewidth=.8)
        closed = np.vstack([fp, fp[0]])
        world.plot(*closed.T, color='#0284c7', linewidth=1.5)
        world.add_collection3d(Poly3DCollection(box_faces(*BOX), facecolor='#64748b', edgecolor='#334155', alpha=.65))
        world.add_collection3d(Poly3DCollection(
            box_faces((-.8,-.6,-1.5),(.8,.6,-.2), camera.rotation(), C),
            facecolor='#f59e0b', edgecolor='#92400e', alpha=.95))
        # Camera body is schematic. Optical center C and optical axis are exact.
        world.scatter(*C, color='black', s=22)
        axis_end = C + 3*camera.rotation()[:, 2]
        world.plot(*np.stack([C, axis_end]).T, color='#ea580c', linewidth=3)
        world.plot([C[0],C[0]],[C[1],C[1]],[0,C[2]], color='black', linestyle=':', alpha=.4)
        world.text(C[0], C[1], C[2]+1, 'PT camera', fontsize=9)
        for i, p in enumerate(targets):
            world.plot(*tracks[:k+1, i].T, color=colors[i], alpha=.4)
            world.scatter(*p, color=colors[i], s=65, edgecolor='black')
            world.text(p[0]+.3,p[1],.5, f'T{i}', fontsize=10)
            world.plot(*np.stack([C,p]).T, color=colors[i] if visible[i] else '#dc2626', linestyle='-' if visible[i] else '--', linewidth=1.2)
        world.set(xlim=(-32,24), ylim=(-34,7), zlim=(0,11), xlabel='World X (m)', ylabel='World Y (m)', zlabel='Z (m)', title='3D world: blue FOV, gray occluder, orange camera')
        world.set_box_aspect((1.3,1,.65))
        world.view_init(elev=27, azim=-60)
        for i in range(2):
            if visible[i]:
                sensor.scatter(*z[i]*1000, color=colors[i], s=90)
                sensor.annotate(f'T{i}',z[i]*1000,xytext=(5,5),textcoords='offset points')
            sensor.text(.02,.96-.08*i,f'T{i}: {statuses[k][i]}',transform=sensor.transAxes,va='top',fontsize=9,color=colors[i] if visible[i] else '#dc2626')
        sensor.set(xlim=(-18,18),ylim=(-12,12),xlabel='Image x (mm)',ylabel='Image y (mm)',title='Sensor output: valid image points only')
        sensor.grid(alpha=.25)
        control.plot(times,angles[:,0],label='Pan (deg)',color='#2563eb')
        control.plot(times,angles[:,1]-147,label='Tilt - 147 deg',color='#ea580c')
        control.axvline(times[k],color='black',linestyle='--')
        control.set(xlim=(0,PERIOD),ylim=(-40,40),xlabel='Time (s)',ylabel='Angle / offset (deg)',title=f'Pan {angles[k,0]:.1f} deg | Tilt {angles[k,1]:.1f} deg')
        control.legend(fontsize=8,loc='upper right')
        control.grid(alpha=.25)

    draw(0)
    fig.savefig(out/'preview.png',dpi=120)
    for k in (30,60,90):
        draw(k); fig.savefig(out/f'frame_{k:03d}.png',dpi=100)
    print('Static previews and CSV written.',flush=True)
    anim = FuncAnimation(fig,draw,frames=len(times),interval=1000/FPS)
    anim.save(out/'pt_motion.mp4',writer=FFMpegWriter(fps=FPS,codec='libx264',extra_args=['-pix_fmt','yuv420p']),dpi=100)
    print('MP4 written.',flush=True)
    anim.save(out/'pt_motion.gif',writer=PillowWriter(fps=FPS),dpi=75)
    plt.close(fig)
    summary = {'frames':len(times),'fps':FPS,'duration_s':PERIOD,
               'pan_range_deg':angles[:,0].min().item(),
               'pan_max_deg':angles[:,0].max().item(),
               'tilt_min_deg':angles[:,1].min().item(),
               'tilt_max_deg':angles[:,1].max().item(),
               'status_counts':{s:sum(row.count(s) for row in statuses) for s in ('VISIBLE','OCCLUDED','OUTSIDE FOV')},
               'motion':'Prescribed smooth kinematic trajectories, no motor dynamics or feedback',
               'noise_sigma_m':0}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    (out/'index.html').write_text('''<!doctype html><meta charset="utf-8"><title>PT camera 动态模型</title><style>body{max-width:1100px;margin:30px auto;font:18px sans-serif}video,img{width:100%}</style><h1>PT camera 三维运动仿真</h1><p>相机位置固定，pan/tilt随时间变化，两个地面目标独立运动。左：三维几何；右上：有效图像测量；右下：角度时间曲线。红色虚线表示目标当前不可观测。</p><video controls loop playsinline preload="metadata" poster="preview.png"><source src="pt_motion.mp4" type="video/mp4"></video><p>本演示采用预设运动学轨迹，不包含马达动力学、反馈控制或实拍验证。轨迹和模型每一帧计算图像坐标；遮挡/出界时无测量。噪声关闭。</p><p><a href="pt_motion.gif">GIF动画</a> | <a href="measurements.csv">逐帧数据</a></p>''')
    print(json.dumps(summary,indent=2),flush=True)


if __name__ == '__main__':
    main()
