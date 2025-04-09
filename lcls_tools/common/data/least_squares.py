import inspect
import lcls_tools.common.data.profile
import numpy
import scipy.optimize


def __fit__(curve, x, y, **kwargs):
    popt, cov = scipy.optimize.curve_fit(curve, x, y, **kwargs)
    sig = inspect.signature(curve)
    # Grab params excluding x.
    par = list(sig.parameters)[1:]
    params = {}
    for k, v in zip(par, popt):
        params[k] = v
    return params, cov


def gaussian(x, y):
    gauss = lcls_tools.common.data.profile.gaussian
    return __fit__(gauss, x, y)


def asymmetrical_gaussian(x, y):
    gauss = lcls_tools.common.data.profile.asymmetrical_gaussian
    inf = numpy.inf
    bounds = ([-inf, -inf, -inf, -1], [inf, inf, inf, 1])

    return __fit__(gauss, x, y, bounds=bounds)


def super_gaussian(x, y):
    gauss = lcls_tools.common.data.profile.super_gaussian

    return __fit__(gauss, x, y)


def asymmetrical_super_gaussian(x, y):
    gauss = lcls_tools.common.data.profile.asymmetrical_super_gaussian
    inf = numpy.inf
    bounds = ([-inf, -inf, -inf, -1, 0], [inf, inf, inf, 1, inf])

    return __fit__(gauss, x, y, bounds=bounds)
