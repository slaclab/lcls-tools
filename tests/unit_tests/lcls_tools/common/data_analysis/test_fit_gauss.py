from lcls_tools.common.data_analysis.fitting_tool import FittingTool
import numpy as np
import unittest


class TestFitTool(unittest.TestCase):
    def gaussian(self, x, amp, mu, sig, offset):
        return amp * np.exp(-np.power(x - mu, 2.0) / (2 * np.power(sig, 2.0))) + offset

    def super_gaussian(self, x, amp, mu, sig, P, offset):
        """Super Gaussian Function"""
        """Degree of P related to flatness of curve at peak"""
        return amp * np.exp((-abs(x - mu) ** (P)) / (2 * sig ** (P))) + offset

    def double_gaussian(self, x, amp, mu, sig, amp2, nu, rho, offset):
        return (
            amp * np.exp(-np.power(x - mu, 2.0) / (2 * np.power(sig, 2.0)))
            + amp2 * np.exp(-np.power(x - nu, 2.0) / (2 * np.power(rho, 2.0)))
        ) + offset

    @unittest.skip("Assertion is not raised when it should be; fixing in issue #130.")
    def test_fit_tool_gaussian(self):
        # Test that the fitting tool can fit each type of gaussian distribution
        x_data = np.arange(500)

        # generated data for pure gaussian
        test_params = [3, 125, 45, 1.5]
        y_data = self.gaussian(x_data, *test_params)
        y_noise = np.random.normal(size=len(x_data), scale=0.04)
        y_test = y_data + y_noise

        fitting_tool = FittingTool(data=y_test)
        fits = fitting_tool.get_fit()
        self.assertIsInstance(fits, dict)
        for key, val in fits.items():
            self.assertIsInstance(val, dict)
            self.assertIn("rmse", val)
            self.assertLessEqual(val["rmse"], 0.4)

    @unittest.skip("Assertion is not raised when it should be; fixing in issue #130.")
    def test_fit_tool_super_gaussian(self):
        x_data = np.arange(500)
        y_noise = np.random.normal(size=len(x_data), scale=0.04)
        test_params_super_gauss = [4, 215, 75, 4, 1]
        y_data_super_gauss = self.super_gaussian(x_data, *test_params_super_gauss)
        y_test_super_gauss = y_data_super_gauss + y_noise
        super_gauss_fitting_tool = FittingTool(data=y_test_super_gauss)
        s_fits = super_gauss_fitting_tool.get_fit()
        self.assertIsInstance(s_fits, dict)
        for key, val in s_fits.items():
            self.assertIsInstance(val, dict)
            self.assertIn("rmse", val)
            if key == "super_gaussian":
                self.assertLessEqual(val["rmse"], 0.4)

    @unittest.skip("Assertion is not raised when it should be; fixing in issue #130.")
    def test_fit_tool_double_gaussian(self):
        # generated data for super gaussian
        x_data = np.arange(500)
        y_noise = np.random.normal(size=len(x_data), scale=0.04)
        test_params_double_gauss = [2, 100, 25, 10, 240, 25, 2]
        y_data_double_gauss = self.double_gaussian(x_data, *test_params_double_gauss)
        y_test_double_gauss = y_data_double_gauss + 3 * y_noise
        double_gauss_fitting_tool = FittingTool(data=y_test_double_gauss)
        d_fits = double_gauss_fitting_tool.get_fit()
        self.assertIsInstance(d_fits, dict)
        for key, val in d_fits.items():
            self.assertIsInstance(val, dict)
            self.assertIn("rmse", val)
            if key == "double_gaussian":
                self.assertLessEqual(val["rmse"], 0.8)
