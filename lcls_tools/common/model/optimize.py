from abc import ABC, abstractmethod
import numpy as np
import scipy.optimize


class Parameter(ABC):
    """
    A static class that supports parameter fitting.

    Attributes:
        name: The name of this parameter.
        bounds: The bounds of this parameter assuming normalized data.

    methods:
        init(x, y): Function that computes the initial value of this
              parameter.
            x: The data positions.
            y: The data weights.
        prior(par, par_0): The prior penalty function for this parameter.
            par: The current value of the parameter.
            par_0: The initial value of the parameter.
        denormalize(par, x, y): Denormalize the parameter where x and y
              have been scaled to fit between 0 and 1.
    """

    name = ""
    bounds = (None, None)

    @staticmethod
    @abstractmethod
    def init(x, y): ...

    @staticmethod
    @abstractmethod
    def prior(par, par_0): ...

    @staticmethod
    @abstractmethod
    def denormalize(par, x, y): ...


def param_fit(curve, params, pos, data, use_prior=False):
    """
    Given a curve function and parameter objects, computes a 2D MLE fit on
    normalized data.

    Arguments:
        curve (Callable[x, params]): The curve to be fit.
            x: The data positions.
            params: A list of parameters scipy.optimipze.minimize will fit.
        params (list[Parameter]): A list of Parameter objects. Indicies
              correspond to the params arguments in curve and prior.
        pos (np.array[float]): The data positions.
        data (np.array[float]): The data weights.
        use_prior (bool): Flag to apply the prior penalty in MLE fit.
    """
    x = (pos - np.min(pos)) / (np.max(pos) - np.min(pos))
    y = (data - np.min(data)) / (np.max(data) - np.min(data))
    init = [p.init(x, y) for p in params]

    def forward(x, vec):
        return curve(x, *vec)

    def prior(vec):
        return np.sum([p.prior(v, i) for p, v, i in zip(params, vec, init)])

    bounds = tuple(p.bounds for p in params)
    res = max_likelihood(forward, prior, x, y, init, bounds, use_prior)
    return {p.name: p.denormalize(val, pos, data) for p, val in zip(params, res.x)}


def max_likelihood(curve, prior, x, y, init, bounds=None, use_prior=False):
    """
    Computes a 2D curve fit using Maximum Likelihood Estimation (MLE).

    Arguments:
        curve (Callable[x, params]): The curve to be fit.
            x: The data positions.
            params: A list of parameters scipy.optimize.minimize will fit.
        prior (Callable[params]): The penalty function that encourages
              the fit to closely match the initial parameter estimation.
            x: The data positions.
            params: A list of parameters scipy.optimize.minimize will fit.
        x (np.array[float]): The data positions.
        y (np.array[float]): The data weights.
        init (list[float]): The initial parameter estimation. Indicies
              correspond to the params arguments in curve and prior.
        bounds (tuple(tuple[float, float])): Boundaries for the fitted params.
        use_prior (bool): Flag to apply the prior penalty.

    Out:
        res: scipy OptimizeResult object.
    """
    if not use_prior:

        def prior(p):
            return 0

    def loss(params, x, y):
        v = np.sum((y - curve(x, params)) ** 2)
        v -= prior(params)
        return v

    res = scipy.optimize.minimize(
        loss,
        init,
        args=(x, y),
        bounds=bounds,
        method="Powell",
    )
    return res
