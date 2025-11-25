import numpy as np
import unittest
from lcls_tools.common.model import asymmetric_gaussian


class TestAssymetricGaussianFits(unittest.TestCase):
    def test_asymmetric_gaussian_fit(self):
        # TODO: An empirical measure of fit quality.
        n = 100
        params_0 = {"mean": 50, "sigma": 10, "amp": 10, "off": 10, "skew": -1}
        x = np.array(range(n))
        y = asymmetric_gaussian.curve(x, **params_0)

        params = asymmetric_gaussian.fit(x, y)
        assert np.allclose(params["mean"], params_0["mean"], rtol=1e-1)
        assert np.allclose(params["sigma"], params_0["sigma"], rtol=1e-1)
        assert np.allclose(params["amp"], params_0["amp"], rtol=1e-1)
        assert np.allclose(params["off"], params_0["off"], rtol=1e-1)
        assert np.allclose(params["skew"], params_0["skew"], rtol=1e-1)
