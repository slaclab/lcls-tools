import numpy as np
from scipy.stats import norm, gamma
import lcls_tools.common.model.optimize as optimize


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
        return norm(mean_0, 0.1).logpdf(mean)

    @staticmethod
    def denormalize(mean, x, y):
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
        return gamma(2.5, loc=0, scale=1 / 5.0).logpdf(sigma)

    @staticmethod
    def denormalize(sigma, x, y):
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
        var = 0.05
        alpha = (amp_0**2) / var
        beta = amp_0 / var
        return gamma(alpha, loc=0, scale=1 / beta).logpdf(amp)

    @staticmethod
    def denormalize(amp, x, y):
        y_scale = np.max(y) - np.min(y)
        return amp * y_scale


class offset(optimize.Parameter):
    name = "off"
    bounds = (0, 1)

    @staticmethod
    def init(pos, data):
        return data.min()

    @staticmethod
    def prior(off, off_0):
        return norm(off_0, 0.5).logpdf(off)

    @staticmethod
    def denormalize(off, x, y):
        y_scale = np.max(y) - np.min(y)
        return off * y_scale + min(y)


params = [mean, sigma, amplitude, offset]


def fit(pos, data, use_prior=False):
    return optimize.param_fit(curve, params, pos, data, use_prior)
