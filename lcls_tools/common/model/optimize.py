import numpy as np
import scipy.optimize
from pydantic import BaseModel
from typing import Callable


def fit(curve, params, pos, data, use_prior=False):
    x = (pos - np.min(pos)) / (np.max(pos) - np.min(pos))
    y = (data - np.min(data)) / (np.max(data) - np.min(data))
    init = [p.init(pos, data) for p in params]
    def forward(x, vec):
        return curve(x, *vec)
    def prior(vec):
        return np.sum([p.prior(v, i) for p, v, i in zip(params, vec, init)])
    bounds = tuple(p.bounds for p in params)
    res = max_likelihood(forward, prior,  x, y, init, bounds, use_prior)
    return {p.name: p.denormalize(val, pos, data) for p, val, in zip(params, res.x)}


def max_likelihood(forward, prior, pos, data, init, bounds=None, use_prior = False):
    if ~use_prior:
        def prior(p):
            return 0
    def loss(params, x, y):
        v = np.sum((y - forward(x, params)) ** 2)
        v -= prior(params)
        return v
    res = scipy.optimize.minimize(
        loss,
        init,
        args=(pos, data),
        bounds=bounds,
        method="Powell",
    )
    return res
