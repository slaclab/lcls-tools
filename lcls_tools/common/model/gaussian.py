import numpy as np
from scipy.stats import norm
import lcls_tools.common.model.optimize as optimize
from pydantic import PositiveFloat


def curve(x, mean=0, sigma=1, amp=1, off=0):
    A = np.sqrt(2 * np.pi) * amp
    return A * norm.pdf((x - mean) / sigma) + off


class mean(optimize.Parameter):
    name = "mean"
    bounds = (0, 1)

    @staticmethod
    def init(pos, data):
        return np.average(pos, weights=data)

    @staticmethod
    def prior(mean, mean_0):
        # Waiting for hyperparams from ML team to implement.
        return 0

    @staticmethod
    def scale(mean, x, y):
        x_scale = np.max(x) - np.min(x)
        return mean * x_scale + min(x)


class sigma(optimize.Parameter):
    name = "sigma"
    bounds = (1e-10, None)

    @staticmethod
    def init(pos, data):
        return np.sqrt(np.cov(pos, aweights=data))

    @staticmethod
    def prior(sigma, sigma_0):
        # Waiting for hyperparams from ML team to implement.
        return 0

    @staticmethod
    def scale(sigma, x, y):
        x_scale = np.max(x) - np.min(x)
        return sigma * x_scale


class amplitude(optimize.Parameter):
    name = "amp"
    bounds = (0, 1)

    @staticmethod
    def init(pos, data):
        return data.max() - data.min()

    @staticmethod
    def prior(amp, amp_0):
        # Waiting for hyperparams from ML team to implement.
        return 0

    @staticmethod
    def scale(amp, x, y):
        y_scale = np.max(y) - np.min(y)
        return amp * y_scale


class offset(optimize.Parameter):
    name = "off"
    bounds = (-1, 1)

    @staticmethod
    def init(pos, data):
        return data.min()

    @staticmethod
    def prior(off, off_0):
        # Waiting for hyperparams from ML team to implement.
        return 0

    @staticmethod
    def scale(off, x, y):
        y_scale = np.max(y) - np.min(y)
        return off * y_scale + min(y)


params = [mean, sigma, amplitude, offset]


def fit(pos, data, use_prior=False):
    return optimize.param_fit(curve, params, pos, data, use_prior)


def signal_to_noise(fit_params):
    return fit_params["amp"] / fit_params["error"]


def extent(fit_params, extent_n_stds: PositiveFloat = 4.0):
    return [
        fit_params["mean"] - extent_n_stds * fit_params["sigma"],
        fit_params["mean"] + extent_n_stds * fit_params["sigma"],
    ]
