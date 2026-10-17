"""Ground-target PT camera; lengths in metres, angles in radians."""
from dataclasses import dataclass
import numpy as np

@dataclass
class Camera:
    position: tuple = (0., 0., 8.)
    pan: float = 0.
    tilt: float = np.deg2rad(140.)
    focal: float = .02
    width: float = .036
    height: float = .024

    def rotation(self):
        """Camera-to-world rotation: Rz(pan) Rx(tilt), supplement convention."""
        c, s = np.cos(self.pan), np.sin(self.pan)
        a, b = np.cos(self.tilt), np.sin(self.tilt)
        return np.array([[c,-s,0],[s,c,0],[0,0,1]]) @ np.array([[1,0,0],[0,a,-b],[0,b,a]])

    def project(self, points):
        points = np.atleast_2d(points)
        q = (points - self.position) @ self.rotation()
        uv = np.full((len(q),2), np.nan)
        front = q[:,2] > 1e-10
        uv[front] = self.focal*q[front,:2]/q[front,2,None]
        visible = front & (np.abs(uv[:,0]) <= self.width/2) & (np.abs(uv[:,1]) <= self.height/2)
        return uv, visible

    def footprint(self):
        """Ground intersection of image corners; NaN if a ray misses ground."""
        rays = np.array([[-self.width/2,-self.height/2,self.focal],[self.width/2,-self.height/2,self.focal],[self.width/2,self.height/2,self.focal],[-self.width/2,self.height/2,self.focal]]) @ self.rotation().T
        t = np.full(4,np.nan)
        down = rays[:,2] < -1e-10
        t[down] = -self.position[2]/rays[down,2]
        return np.array(self.position) + t[:,None]*rays

    def measure(self, points, boxes=(), sigma=0., rng=None):
        """Return image-plane measurements (metres), NaN for unavailable targets."""
        if sigma < 0: raise ValueError('sigma must be nonnegative')
        points = np.atleast_2d(points)
        uv, visible = self.project(points)
        for i, point in enumerate(points):
            if visible[i] and any(segment_box(self.position,point,*box) for box in boxes):
                visible[i] = False
        z = uv.copy()
        if sigma:
            if rng is None: raise ValueError('provide a seeded random generator')
            z[visible] += rng.normal(0,sigma,(visible.sum(),2))
        z[~visible] = np.nan
        return z, visible

def segment_box(origin, target, lower, upper):
    """Slab intersection of open sight segment with an axis-aligned solid box."""
    origin, target, lower, upper = map(lambda x: np.asarray(x,dtype=float),(origin,target,lower,upper))
    lo, hi = 0., 1.
    for j,d in enumerate(target-origin):
        if abs(d) < 1e-12:
            if origin[j] < lower[j] or origin[j] > upper[j]: return False
        else:
            a,b = sorted(((lower[j]-origin[j])/d,(upper[j]-origin[j])/d))
            lo,hi = max(lo,a),min(hi,b)
            if lo > hi: return False
    return hi > 1e-9 and lo < 1-1e-9
