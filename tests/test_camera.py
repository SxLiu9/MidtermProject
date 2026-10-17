import unittest
import numpy as np
from camera import Camera, segment_box

class GeometryTests(unittest.TestCase):
    def test_nadir_known_projection_and_front(self):
        c=Camera(tilt=np.pi)
        uv,v=c.project([[0,0,0],[1,2,0],[0,0,9]])
        np.testing.assert_allclose(uv[:2],[[0,0],[.0025,-.005]],atol=1e-14)
        self.assertEqual(v.tolist(),[True,True,False])
    def test_ground_corners_reproject(self):
        c=Camera(pan=.4)
        uv,_=c.project(c.footprint())
        np.testing.assert_allclose(uv,[[-.018,-.012],[.018,-.012],[.018,.012],[-.018,.012]],atol=1e-14)
    def test_occlusion(self):
        c=Camera(tilt=np.pi)
        _,v=c.measure([[0,0,0],[3,0,0]],boxes=[((-.5,-.5,2),(.5,.5,4))])
        self.assertEqual(v.tolist(),[False,True])
        self.assertFalse(segment_box([0,0,8],[0,0,0],[-1,-1,-4],[1,1,-2]))
    def test_noise_statistics(self):
        c=Camera(tilt=np.pi)
        z,v=c.measure(np.zeros((40000,3)),sigma=.001,rng=np.random.default_rng(42))
        self.assertTrue(v.all())
        self.assertLess(abs(z.mean()),.00002)
        self.assertAlmostEqual(z.std(),.001,delta=.00002)

if __name__=='__main__': unittest.main()
