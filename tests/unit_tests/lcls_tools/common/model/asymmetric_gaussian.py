import numpy as np
import unittest
from lcls_tools.common.model import asymmetric_gaussian


class TestGaussianFits(unittest.TestCase):
    def test_asymmetric_gaussian_fit(self):
        # TODO: An empirical measure of fit quality.
        n = 100
        params_0 = {"mean": 50, "sigma": 10, "amp": 10, "off": 10, "skew": 2.5}
        x = np.array(range(n))
        y = asymmetric_gaussian.curve(x, **params_0)

        params = asymmetric_gaussian.fit(x, y)

        self.assertAlmostEqual(params["mean"], params_0["mean"], places=1)
        self.assertAlmostEqual(params["sigma"], params_0["sigma"], places=1)
        self.assertAlmostEqual(params["amp"], params_0["amp"], places=1)
        self.assertAlmostEqual(params["off"], params_0["off"], places=1)
        self.assertAlmostEqual(params["skew"], params_0["skew"], places=1)
