import numpy as np
from scipy.optimize import curve_fit
import statistics


# from scipy.ndimage import gaussian_filter
# from scipy.special import erf
# from lmfit import Model
# want functions for gaussian
# truncated gaussian
# super gaussian
# rms
# truncated rms


class FittingTool:
    def __init__(self, data: np.array, **kwargs) -> dict:
        """tool takes in the data points for some distribution, for now just one distrbution at a time"""
        self.y = data
        self.x = np.arange(len(data))
        # self.initial_guess = kwargs['initial_guess']

        self.initial_params = self.guess_params(self.y)

    def guess_params(self, y: np.array, initial_guess: dict = {}) -> dict:
        initial_params = {}

        offset = initial_guess.pop("offset", np.mean(y[-10:]))
        amplitude = initial_guess.pop("amplitude", y.max() - offset)
        mu = initial_guess.pop("mu", np.argmax(y))
        sigma = initial_guess.pop("sigma", y.shape[0] / 5)
        initial_params["gaussian"] = [amplitude, mu, sigma, offset]

        # super gaussian extension
        power = 2
        initial_params["super_gaussian"] = [amplitude, mu, sigma, power, offset]

        #  for double gaussian
        #  will make new helper functions for peaks and widths
        amplitude2 = amplitude / 3
        nu = mu / 2
        rho = sigma / 2
        initial_params["double_gaussian"] = [
            amplitude,
            mu,
            sigma,
            amplitude2,
            nu,
            rho,
            offset,
        ]

        return initial_params

    def get_fit(self, best_fit: bool = False) -> dict:
        """Return fit parameters to data y such that y = method(x,parameters)"""
        fits = {}

        for key, val in self.initial_params.items():
            method = getattr(self, key)
            fit_params = curve_fit(method, self.x, self.y, val)[0]

            y_fitted = method(self.x, *fit_params)
            rmse = self.calculate_rms_deviation(self.y, y_fitted)
            print(method)
            print(rmse)
            fits[key] = fit_params
        print("returning only best fit: ", best_fit)
        return fits

    def check_skewness(self, outcomes, mu, sigma):
        """Checks for skewness in dataset, neg if mean<median<mode, pos if opposite"""
        mode = statistics.mode(outcomes)
        pearsons_coeff = (mu - mode) / sigma
        print(pearsons_coeff)
        return pearsons_coeff

    def check_kurtosis(self):
        """greater kurtosis higher the peak"""
        """how fast tails approaching zero, more outliers with higher kurtosis"""
        """positive excess - tails approach zero slower"""
        """negative excess - tails approach zero faster"""
        # do later
        return 0

    def find_peaks(self):
        pass

    def find_widths(self):
        pass

    def find_runs(self):
        pass

    def find_moments(self):
        """mean, sigma, skewness, kurtosis"""
        pass

    def truncate_distribution(x, lower_bound: float = None, upper_bound: float = None):
        if lower_bound is None:
            lower_bound = x.min()
        if upper_bound is None:
            upper_bound = x.max()
        truncated_x = np.clip(x, lower_bound, upper_bound)
        return truncated_x

    def calculate_rms_deviation(self, x: np.array, fit_x: np.array):
        rms_deviation = np.sqrt(np.power(sum(x - fit_x), 2) / len(x))
        return rms_deviation

    def calculate_unbiased_rms_deviated(x: np.array = None):
        mean = np.mean(x)
        rms_deviation = np.sqrt(np.power(sum(x - mean), 2) / len(x))
        return rms_deviation

    @staticmethod
    def gaussian(x, amp, mu, sig, offset):
        """Gaussian Function"""
        """need a way to guess params if amp =/"""
        return amp * np.exp(-np.power(x - mu, 2.0) / (2 * np.power(sig, 2.0))) + offset

    @staticmethod
    def gaussian_with_linear_background(x, amp, mu, sig, offset, slope):
        return (
            amp * np.exp(-np.power(x - mu, 2.0) / (2 * np.power(sig, 2.0)))
            + offset
            + slope * x
        )

    @staticmethod
    def super_gaussian(x, amp, mu, sig, P, offset):
        """Super Gaussian Function"""
        """Degree of P related to flatness of curve at peak"""
        return amp * np.exp((-abs(x - mu) ** P) / (2 * sig**P)) + offset

    @staticmethod
    def double_gaussian(x, amp, mu, sig, amp2, nu, rho, offset):
        return (
            amp * np.exp(-np.power(x - mu, 2.0) / (2 * np.power(sig, 2.0)))
            + amp2 * np.exp(-np.power(x - nu, 2.0) / (2 * np.power(rho, 2.0)))
        ) + offset

    @staticmethod
    def two_dim_gaussian(x, y, A, x0, y0, sigma_x, sigma_y):
        """2-D Gaussian Function"""
        return A * np.exp(
            -((x - x0) ** 2) / (2 * sigma_x**2) - (y - y0) ** 2 / (2 * sigma_y**2)
        )

    # fit batch images
