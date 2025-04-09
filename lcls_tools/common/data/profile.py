import math
import numpy


def gaussian(x, mu, sigma):
    amp = 1 / (sigma * math.sqrt(2 * math.pi))
    exp = -1 / 2 * (x - mu) ** 2 / sigma**2
    return amp * numpy.exp(exp)


def asymmetrical_gaussian(x, mu, sigma, amp, A):
    skew = 1 + numpy.sign(x - mu) * A
    exp = -1 / 2 * ((x - mu) / skew / sigma) ** 2
    return amp * numpy.exp(exp)


def super_gaussian(x, y, mu, sigma, amp, n):
    exp = abs((x - mu) / math.sqrt(2) / sigma)
    exp = -(exp**n)
    return amp * numpy.exp(exp)


def asymmetrical_super_gaussian(x, y, mu, sigma, amp, A, n):
    skew = 1 + numpy.sign(x - mu) * A
    exp = abs((x - mu) / skew / math.sqrt(2) / sigma)
    exp = -(exp**n)
    return amp * numpy.exp(exp)
