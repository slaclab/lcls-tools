import numpy as np
from scipy.stats import norm
from lcls_tools.common.model as model

def super_gaussian(x, mean, sigma, amp, off, n):
    exp = abs((x - mean) / sigma) ** n / 2
    exp = 2 ** (1 / 2 - n / 4) * exp
    A = np.sqrt(2 * np.pi) * amp
    return A * norm.pdf(exp) + off

def fit(x, y, use_prior = False):
    def forward(x, p):
        return curve(x, p[0], p[1], p[2], p[3], p[4])
    def prior(p):
        return 0
    mean_0 = np.average(x, weights=y)
    sigma_0 = np.sqrt(np.cov(x, aweights=y))
    amp_0 = y.max() - y.min() - 0.01
    off_0 = y.min() + 0.01
    n_0 = 2
    init = [mean_0, sigma_0, amp_0, off_0, n_0]
    bounds = ((None, None),
              (0, None),
              (None, None),
              (None, None),
              (0, None))
    return model.fit(forward, prior,  x, y, init)
