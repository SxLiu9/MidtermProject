"""Ideal pinhole position sensor. Lengths: metres; angles: radians.

R maps camera vectors into the world. Points are stored as row vectors.
Visibility is selected before Gaussian image-plane noise is applied.
"""

from dataclasses import dataclass
import numpy as np

EPS = 1e-12


def _points(value):
    points = np.atleast_2d(np.asarray(value, dtype=float))
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
        raise ValueError("points must be a finite (N, 3) array")
    return points


@dataclass(frozen=True)
class Camera:
    position: tuple = (0.0, 0.0, 8.0)
    pan: float = 0.0
    tilt: float = np.deg2rad(140.0)
    focal: float = 0.02
    width: float = 0.036
    height: float = 0.024  # image-plane height, not camera elevation

    def __post_init__(self):
        if np.asarray(self.position).shape != (3,):
            raise ValueError("camera position must have three components")
        if not np.isfinite(
            [*self.position, self.pan, self.tilt, self.focal, self.width, self.height]
        ).all():
            raise ValueError("camera parameters must be finite")
        if min(self.focal, self.width, self.height) <= 0:
            raise ValueError("focal length and image dimensions must be positive")

    def rotation(self):
        """Camera-to-world Rz(pan) Rx(tilt); tilt=pi looks downward."""
        c, s = np.cos(self.pan), np.sin(self.pan)
        a, b = np.cos(self.tilt), np.sin(self.tilt)
        return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]]) @ np.array(
            [[1, 0, 0], [0, a, -b], [0, b, a]]
        )

    def project(self, points):
        """Return ideal image coordinates and FOV mask; LOS is not applied."""
        q = (_points(points) - self.position) @ self.rotation()
        uv = np.full((len(q), 2), np.nan)
        front = q[:, 2] > 1e-10
        uv[front] = self.focal * q[front, :2] / q[front, 2, None]
        in_fov = (
            front
            & (np.abs(uv[:, 0]) <= self.width / 2 + EPS)
            & (np.abs(uv[:, 1]) <= self.height / 2 + EPS)
        )
        return uv, in_fov

    def footprint(self):
        """Four forward Z=0 intersections; missing intersections are NaN.

        A finite quadrilateral is valid only when all four rays meet ground.
        This method does not clip a horizon-crossing FOV to a finite workspace.
        """
        rays = (
            np.array(
                [
                    [-self.width / 2, -self.height / 2, self.focal],
                    [self.width / 2, -self.height / 2, self.focal],
                    [self.width / 2, self.height / 2, self.focal],
                    [-self.width / 2, self.height / 2, self.focal],
                ]
            )
            @ self.rotation().T
        )
        t = np.full(4, np.nan)
        if self.position[2] > 0:
            down = rays[:, 2] < -1e-10
            t[down] = -self.position[2] / rays[down, 2]
        return np.array(self.position) + t[:, None] * rays

    def projection_jacobian(self, points):
        """d(image position)/d(world position), (N, 2, 3), at fixed pose.

        Defined for positive depth, including points outside the image rectangle.
        This is a local derivative of projection, not of the discontinuous gate.
        """
        q = (_points(points) - self.position) @ self.rotation()
        j = np.full((len(q), 2, 3), np.nan)
        valid = q[:, 2] > 1e-10
        x, y, z = q[valid].T
        j[valid] = 0.0
        j[valid, 0, 0] = self.focal / z
        j[valid, 1, 1] = self.focal / z
        j[valid, 0, 2] = -self.focal * x / z**2
        j[valid, 1, 2] = -self.focal * y / z**2
        return j @ self.rotation().T

    def measure(self, points, boxes=(), sigma=0.0, rng=None):
        """Position measurement and availability mask; missing values are NaN."""
        if not np.isfinite(sigma) or sigma < 0:
            raise ValueError("sigma must be finite and nonnegative")
        points = _points(points)
        uv, visible = self.project(points)
        for i, point in enumerate(points):
            if visible[i] and any(
                segment_box(self.position, point, *box) for box in boxes
            ):
                visible[i] = False
        z = uv.copy()
        if sigma:
            if rng is None:
                raise ValueError("provide a seeded random generator")
            z[visible] += rng.normal(0, sigma, (visible.sum(), 2))
        z[~visible] = np.nan
        return z, visible


def segment_box(origin, target, lower, upper):
    """Open sight-segment / closed solid-box intersection (grazing blocks)."""
    origin, target, lower, upper = _points([origin, target, lower, upper])
    if np.any(upper < lower):
        raise ValueError("box upper corner must not be below lower corner")
    lo, hi = 0.0, 1.0
    for j, direction in enumerate(target - origin):
        if abs(direction) < EPS:
            if origin[j] < lower[j] - EPS or origin[j] > upper[j] + EPS:
                return False
        else:
            a, b = sorted(
                ((lower[j] - origin[j]) / direction, (upper[j] - origin[j]) / direction)
            )
            lo, hi = max(lo, a), min(hi, b)
            if lo > hi + EPS:
                return False
    return hi > EPS and lo < 1 - EPS


def footprint_area(camera):
    """Shoelace area (m²); NaN if footprint is not a finite quadrilateral."""
    xy = camera.footprint()[:, :2]
    if not np.isfinite(xy).all():
        return np.nan
    x, y = xy.T
    return 0.5 * abs(x @ np.roll(y, -1) - y @ np.roll(x, -1))
