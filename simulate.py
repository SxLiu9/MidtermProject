"""Reproducible experiments. Run from repository root: python simulate.py."""
import os
os.environ.setdefault('XDG_CACHE_HOME','/tmp/midterm-cache')
os.environ.setdefault('MPLCONFIGDIR','/tmp/midterm-mpl')
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter
from camera import Camera

def main(output_dir=None):
    if output_dir is None:
        output_dir = Path(__file__).resolve().parent / "outputs"
    out=Path(output_dir).resolve(); out.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(4810)
    targets=np.array([[-2,-5,0],[0,-8,0],[3,-10,0],[1,-4,0]])
    box=((-1,-5,0),(1,-3,4))
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    
    def draw(angle):
        c=Camera(pan=np.deg2rad(angle))
        z,v=c.measure(targets,boxes=[box])
        for a in axes: a.clear()
        a,b=axes
        fp=c.footprint()[:,:2]; fp=np.vstack([fp,fp[0]])
        a.fill(fp[:,0],fp[:,1],alpha=.15); a.plot(fp[:,0],fp[:,1])
        a.scatter(targets[:,0],targets[:,1],c=np.where(v,'green','red'))
        for i,p in enumerate(targets): a.text(p[0]+.2,p[1],str(i))
        a.add_patch(plt.Rectangle(box[0][:2],2,2,color='gray',alpha=.7))
        a.plot(0,0,'k^'); a.set(xlim=(-38,38),ylim=(-40,8),xlabel='World X (m)',ylabel='World Y (m)',title=f'Pan {angle:.0f} deg; tilt 140 deg'); a.set_aspect('equal')
        b.scatter(z[:,0]*1000,z[:,1]*1000)
        for i in np.flatnonzero(v): b.text(z[i,0]*1000,z[i,1]*1000,str(i))
        b.set(xlim=(-18,18),ylim=(-12,12),xlabel='Image x (mm)',ylabel='Image y (mm)',title='Available measurements (occlusion enabled)'); b.grid()
        fig.tight_layout()
    
    draw(0); fig.savefig(out/'scene.png',dpi=160)
    animation=FuncAnimation(fig,draw,frames=np.linspace(-40,40,41),interval=100)
    animation.save(out/'pan_scan.gif',writer=PillowWriter(fps=10)); plt.close(fig)
    
    angles=np.linspace(-60,60,121); rows=[]
    for angle in angles:
        c=Camera(pan=np.deg2rad(angle))
        _,fov=c.project(targets); _,visible=c.measure(targets,boxes=[box])
        rows.append([angle,fov.sum(),visible.sum()])
    rows=np.array(rows); np.savetxt(out/'visibility.csv',rows,delimiter=',',header='pan_deg,in_fov,visible_after_occlusion',comments='')
    fig,ax=plt.subplots(); ax.plot(rows[:,0],rows[:,1],label='Inside FOV'); ax.plot(rows[:,0],rows[:,2],label='Visible after occlusion'); ax.set(xlabel='Pan (deg)',ylabel='Number of targets'); ax.legend(); fig.tight_layout(); fig.savefig(out/'visibility.png',dpi=160); plt.close(fig)
    
    c=Camera(tilt=np.pi); sigmas=np.array([0,.02,.05,.1,.2,.5])*1e-3
    results=[]
    for sigma in sigmas:
        z,_=c.measure(np.zeros((10000,3)),sigma=sigma,rng=rng)
        results.append([sigma,float(np.sqrt(np.mean(np.sum(z*z,axis=1)))),np.sqrt(2)*sigma])
    results=np.array(results); np.savetxt(out/'noise.csv',results,delimiter=',',header='sigma_m,radial_rmse_m,theoretical_radial_rmse_m',comments='')
    fig,ax=plt.subplots(); ax.plot(results[:,0]*1000,results[:,1]*1000,'o',label='Simulation: 10000 samples/condition'); ax.plot(results[:,0]*1000,results[:,2]*1000,label='Theory: sqrt(2) sigma'); ax.set(xlabel='Per-axis noise sigma (mm)',ylabel='Radial image RMSE (mm)'); ax.legend(); fig.tight_layout(); fig.savefig(out/'noise.png',dpi=160); plt.close(fig)
    summary={'seed':4810,'noise_samples_per_condition':10000,'max_noise_rmse_difference_m':float(np.max(abs(results[:,1]-results[:,2]))),'limitations':['Synthetic validation only; no real camera calibration','Point targets, ideal pinhole, static box occluder','No illumination or lens distortion model','No controller or motor dynamics implemented']}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))

    # Standalone overview and browser gallery, no local server required.
    from PIL import Image
    fig, axs = plt.subplots(3, 1, figsize=(12, 15))
    for ax, name in zip(axs, ['scene.png', 'visibility.png', 'noise.png']):
        ax.imshow(Image.open(out/name)); ax.axis('off')
    fig.tight_layout(); fig.savefig(out/'overview.png',dpi=120); plt.close(fig)
    html = '<!doctype html><meta charset="utf-8"><title>PT Camera Experiments</title><style>body{font:18px sans-serif;max-width:1100px;margin:30px auto}img{max-width:100%}section{margin:40px 0}</style><h1>PT Camera Simulation Results</h1><p>Ideal pinhole model with geometric visibility and image-plane Gaussian noise. Synthetic validation, not real-camera calibration.</p>'
    for title, name in [('1. Scene and image measurements','scene.png'),('2. Pan scan animation','pan_scan.gif'),('3. FOV versus occlusion','visibility.png'),('4. Noise versus theory','noise.png')]:
        html += f'<section><h2>{title}</h2><img src="{name}" alt="{title}"></section>'
    (out/'index.html').write_text(html)
    print(f"Results saved to: {out}")
    for path in sorted(out.iterdir()):
        if path.is_file(): print(f"  {path.name}: {path.stat().st_size:,} bytes")
    return out

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', default=None)
    main(parser.parse_args().output_dir)
