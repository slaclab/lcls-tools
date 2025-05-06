import numpy as np
import scipy.optimize

def fit(forward, prior, pos, data, init, bounds=None):
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
