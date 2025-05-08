import numpy as np
from scipy.stats import norm
import lcls_tools.common.model.optimize as optimize
import lcls_tools.common.model.gaussian as gaussian


def curve(x, mean, sigma, amp, off, n):
    exp = abs((x - mean) / sigma) ** (n / 2)
    exp = 2 ** (1 / 2 - n / 4) * exp
    A = np.sqrt(2 * np.pi) * amp
    return A * norm.pdf(exp) + off

class order(optimize.Parameter):
    name = "n"
    bounds = (0, None)
    @staticmethod
    def init(x, y):
        return 2
    
    @staticmethod
    def prior(n, n_0):
        return 0

    @staticmethod
    def denormalize(n, x, y):
        return n

params = gaussian.params + [order]

def fit(pos, data):
    return optimize.fit(curve, params, pos, data, use_prior=False)
