import inspect
import math
import numpy
import scipy.optimize


def __fit__(curve, x, y, **kwargs):
    popt, pcov = scipy.optimize.curve_fit(curve, x, y, **kwargs)
    sig = inspect.signature(curve)
    # Grab params excluding x.
    par = list(sig.parameters)[1:]
    params = {}
    for k, v in zip(par, popt):
        params[k] = v
    return params, pcov


def gaussian(x, y):
    def gauss(x, mu, sigma):
        amp = 1 / (sigma * math.sqrt(2 * math.pi))
        exp = -1 / 2 * (x - mu) ** 2 / sigma**2
        return amp * numpy.exp(exp)

    return __fit__(gauss, x, y)


def asymmetrical_gaussian(x, y):
    def gauss(x, mu, sigma, amp, A):
        skew = 1 + numpy.sign(x - mu) * A
        exp = -1 / 2 * ((x - mu) / skew / sigma) ** 2
        return amp * numpy.exp(exp)

    inf = numpy.inf
    bounds = ([-inf, -inf, -inf, -1], [inf, inf, inf, 1])

    return __fit__(gauss, x, y, bounds=bounds)


def super_gaussian(x, y):
    def gauss(x, mu, sigma, amp, n):
        exp = abs((x - mu) / math.sqrt(2) / sigma)
        exp = -(exp**n)
        return amp * numpy.exp(exp)

    return __fit__(gauss, x, y)


def asymmetrical_super_gaussian(x, y):
    def gauss(x, mu, sigma, amp, A, n):
        skew = 1 + numpy.sign(x - mu) * A
        exp = abs((x - mu) / skew / math.sqrt(2) / sigma)
        exp = -(exp**n)
        return amp * numpy.exp(exp)

    inf = numpy.inf
    bounds = ([-inf, -inf, -inf, -1, 0], [inf, inf, inf, 1, inf])

    return __fit__(gauss, x, y, bounds=bounds)
