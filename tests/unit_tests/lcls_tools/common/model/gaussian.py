import numpy as np
import unittest
from lcls_tools.common.model import gaussian


class TestGaussianFits(unittest.TestCase):
    def test_gaussian_fit(self):
        # TODO: An empirical measure of fit quality.
        n = 100
        params_0 = {"mean": 50, "sigma": 10, "amp": 10, "off": 10}
        x = np.array(range(n))
        y = gaussian.curve(x, **params_0)

        params = gaussian.fit(x, y)

        self.assertAlmostEqual(params["mean"], params_0["mean"], places=1)
        self.assertAlmostEqual(params["sigma"], params_0["sigma"], places=1)
        self.assertAlmostEqual(params["amp"], params_0["amp"], places=1)
        self.assertAlmostEqual(params["off"], params_0["off"], places=1)
