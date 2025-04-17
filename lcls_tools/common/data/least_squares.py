import lcls_tools.common.data.profile
import numpy
import scipy.optimize


def _fit(curve, params, x, y, **kwargs):
    popt, cov = scipy.optimize.curve_fit(curve, x, y, **kwargs)
    if len(popt) != len(params):
        raise ValueError(
            "Length of arg params should be equal to 1 minus number of args in curve."
        )
    param_fit = {}
    for k, v in zip(params, popt):
        param_fit[k] = v
    return param_fit, cov


def gaussian(x, y):
    curve = lcls_tools.common.data.profile.gaussian
    params = ["mu", "sigma"]
    return _fit(curve, params, x, y)


def asymmetrical_gaussian(x, y):
    curve = lcls_tools.common.data.profile.asymmetrical_gaussian
    params = ["mu", "sigma", "amp", "A"]
    inf = numpy.inf
    bounds = ([-inf, -inf, -inf, -1], [inf, inf, inf, 1])
    return _fit(curve, params, x, y, bounds=bounds)


def super_gaussian(x, y):
    curve = lcls_tools.common.data.profile.super_gaussian
    params = ["mu", "sigma", "amp", "n"]
    return _fit(curve, params, x, y)


def asymmetrical_super_gaussian(x, y):
    curve = lcls_tools.common.data.profile.asymmetrical_super_gaussian
    params = ["mu", "sigma", "amp", "A", "n"]
    inf = numpy.inf
    bounds = ([-inf, -inf, -inf, -1, 0], [inf, inf, inf, 1, inf])
    return _fit(curve, params, x, y, bounds=bounds)
