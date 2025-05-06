import numpy as np
from scipy.stats import norm, gamma

from lcls_tools.common.model as model


def curve(x, mean=0, sigma=1, amp=1, off=0):
    A = np.sqrt(2 * np.pi) * amp
    return A * norm.pdf((x - mean) / sigma) + off


def fit(x, y, use_prior = False):
    mean, mean_0 = mean_prior(x, y)
    sigma, sigma_0 = sigma_prior(x, y)
    amp, amp_0 = amplitude_prior(x, y)
    off, off_0 = off_prior(x, y)
    def forward(x, p):
        return curve(x, p[0], p[1], p[2], p[3])
    if use_prior:
        def prior(p):
            return mean(p[0]) + sigma(p[1]) + amp(p[2]) + off(p[3])
    else:
        def prior(p):
            return 0
    init = [mean_0, sigma_0, amp_0, off_0]
    return model.fit(forward, prior,  x, y, init)


def mean_prior(x, y):
    mean_0 = np.average(x, weights=y)
    return norm(mean_0, 0.1).logpdf, mean_0


def sigma_prior(x, y):
    sigma_0 = np.sqrt(np.cov(x, aweights=y))
    return gamma(2.5, loc=0, scale=1 / 5.0).logpdf, sigma_0


def amplitude_prior(x, y):
    amp_0 = y.max() - y.min() - 0.01
    var = 0.05
    alpha = (amp_0**2) / var
    beta = amp_0 / var
    return gamma(alpha, loc=0, scale=1 / beta).logpdf, amp_0


def off_prior(x, y):
    off_0 = y.min() + 0.01
    return norm(off_0, 0.5).logpdf, off_0
