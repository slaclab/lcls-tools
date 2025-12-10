import numpy as np
from scipy.stats import norm
import lcls_tools.common.model.optimize as optimize
import lcls_tools.common.model.gaussian as gaussian


def curve(x, mean=0, sigma=1, amp=1, off=0, skew=0):
    asym = 1 + np.sign(x - mean) * skew
    A = np.sqrt(2 * np.pi) * amp
    return A * norm.pdf((x - mean) / (sigma * asym)) + off


class skew(optimize.Parameter):
    name = "skew"
    bounds = (-1, 1)

    @staticmethod
    def init(pos, data):
        return 0

    @staticmethod
    def prior(skew, skew_0):
        # Waiting for hyperparams from ML team to implement.
        return 0

    @staticmethod
    def scale(skew, x, y):
        return skew


params = gaussian.params + [skew]


def fit(pos, data, use_prior=False):
    return optimize.param_fit(curve, params, pos, data, use_prior)


def signal_to_noise(fit_params):
    return gaussian.signal_to_noise(fit_params)


def extent(fit_params, extent_n_stds: float = 4.0):
    return gaussian.extent(fit_params, extent_n_stds)
