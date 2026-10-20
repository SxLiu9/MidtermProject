"""Independent geometric and statistical checks, including failure boundaries."""

import unittest
import numpy as np
from ptcamera import Camera, segment_box
from ptcamera.model import footprint_area


class GeometryTests(unittest.TestCase):
    def test_known_nadir_projection_and_negative_depth(self):
        c = Camera(tilt=np.pi)
        uv, visible = c.project([[0, 0, 0], [1, 2, 0], [0, 0, 9]])
        np.testing.assert_allclose(uv[:2], [[0, 0], [0.0025, -0.005]], atol=1e-14)
        self.assertEqual(visible.tolist(), [True, True, False])
        self.assertTrue(np.isnan(uv[-1]).all())

    def test_pan_quarter_turn_changes_image_axes(self):
        uv, _ = Camera(tilt=np.pi, pan=np.pi / 2).project([1, 0, 0])
        np.testing.assert_allclose(uv[0], [0, 0.0025], atol=1e-14)

    def test_fov_edge_and_outside(self):
        c = Camera(tilt=np.pi)
        _, visible = c.project(
            [[7.2, 0, 0], [7.2001, 0, 0], [0, 4.8, 0], [0, 4.8001, 0]]
        )
        self.assertEqual(visible.tolist(), [True, False, True, False])

    def test_ground_corners_reproject(self):
        c = Camera(pan=0.4)
        uv, visible = c.project(c.footprint())
        np.testing.assert_allclose(
            uv,
            [[-0.018, -0.012], [0.018, -0.012], [0.018, 0.012], [-0.018, 0.012]],
            atol=1e-14,
        )
        self.assertTrue(visible.all())

    def test_height_area_law_and_pan_invariance(self):
        for h in [4, 8, 12]:
            for pan in [0, 0.4, 1.2]:
                c = Camera(position=(0, 0, h), tilt=np.pi, pan=pan)
                self.assertAlmostEqual(
                    footprint_area(c), 0.036 * 0.024 * h * h / 0.02**2, places=10
                )

    def test_horizon_does_not_fabricate_finite_footprint(self):
        c = Camera(tilt=np.pi / 2)
        self.assertTrue(np.isnan(c.footprint()).any())
        self.assertTrue(np.isnan(footprint_area(c)))

    def test_los_threshold_and_obstacle_behind_target(self):
        c = Camera()
        for height, expected in [(2.7, True), (2.8, False), (2.9, False)]:
            z, v = c.measure([0, -8, 0], boxes=[((-0.8, -5.2, 0), (0.8, -4, height))])
            self.assertEqual(bool(v[0]), expected)
            self.assertEqual(bool(np.isnan(z[0]).all()), not expected)
        self.assertFalse(segment_box([0, 0, 8], [0, 0, 0], [-1, -1, -4], [1, 1, -2]))

    def test_projection_derivative_against_central_difference(self):
        c = Camera(pan=0.37)
        p = np.array([[1.0, -7.0, 0.0], [-2.0, -10.0, 0.0]])
        j = c.projection_jacobian(p)
        for axis in range(3):
            d = np.eye(3)[axis] * 1e-5
            fd = (c.project(p + d)[0] - c.project(p - d)[0]) / (2e-5)
            np.testing.assert_allclose(j[:, :, axis], fd, atol=1e-10, rtol=1e-7)

    def test_noise_statistics_and_missing_values(self):
        c = Camera(tilt=np.pi)
        z, v = c.measure(
            np.zeros((40000, 3)), sigma=0.001, rng=np.random.default_rng(42)
        )
        self.assertTrue(v.all())
        self.assertLess(abs(z.mean()), 0.00002)
        self.assertAlmostEqual(z.std(), 0.001, delta=0.00002)
        z, v = c.measure([[100, 0, 0]], sigma=0.001, rng=np.random.default_rng(42))
        self.assertFalse(v[0])
        self.assertTrue(np.isnan(z).all())

    def test_reject_invalid_parameters(self):
        with self.assertRaises(ValueError):
            Camera(focal=0)
        with self.assertRaises(ValueError):
            Camera().measure([[0, 0, 0]], sigma=-1)
        with self.assertRaises(ValueError):
            Camera().project([[1, 2]])


if __name__ == "__main__":
    unittest.main()
