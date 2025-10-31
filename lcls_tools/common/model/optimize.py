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
    def scale(par, x, y): ...


def param_fit(curve, params, pos, data, use_prior=False):
    """
    Given a curve function and parameter objects, computes a 1D curve fit
    using Maximum A Postiori (MAP) fitting.

    If `use_prior` is True, prior distributions defined by each parameter will be
    used to penalize parameter values that have a low prior likelihood.
    If `use_prior` is False, optimization is not weighted by
    prior parameter distributions, reducing fitting to Maximum Likelihood
    Estimation (MLE), commonly referred to as least-squares fitting.

    Arguments:
        curve (Callable[x, params]): The curve to be fit.
            x: The data positions.
            params: A list of parameters scipy.optimipze.minimize will fit.
        params (list[Parameter]): A list of Parameter objects. Indicies
              correspond to the params arguments in curve and prior.
        pos (np.array[float]): The data positions.
        data (np.array[float]): The data weights.
        use_prior (bool): Flag to apply the prior penalty in MAP fit.
    """
    x = (pos - np.min(pos)) / (np.max(pos) - np.min(pos))
    y = (data - np.min(data)) / (np.max(data) - np.min(data))
    init = [p.init(x, y) for p in params]

    def forward(x, vec):
        return curve(x, *vec)

    if use_prior:

        def prior(vec):
            return np.sum([p.prior(v) for v, p in zip(vec, params)])
    else:
        prior = None

    bounds = tuple(p.bounds for p in params)
    res = map_fit(forward, x, y, init, bounds, prior)

    fitp = {p.name: p.scale(val, pos, data) for p, val in zip(params, res.x)}
    error = np.std(data - curve(x, **fitp))
    fitp["error"] = error

    return fitp


def map_fit(curve, x, y, init, bounds=None, prior=None):
    """
    Computes a 1D curve fit using Maximum A Postiori (MAP) fitting. If `prior`
    is None this function assumes a uniform prior distribution for all
    parameters, equivelent to Maximum Likelihood Estimation (least-squares).
    If given, the `prior` callable adds a penalty term to optimization that
    encourages the fit to match the maximum prior likelihood of each parameter.

    Arguments:
        curve (Callable[x, params]): The curve to be fit.
            x: The data positions.
            params: A list of parameters scipy.optimize.minimize will fit.
        x (np.array[float]): The data positions.
        y (np.array[float]): The data weights.
        init (list[float]): The initial parameter estimation. Indicies
              correspond to the params arguments in curve and prior.
        bounds (tuple(tuple[float, float])): Boundaries for the fitted params.
        prior (Callable[params]): The penalty function that biases fitting towards
              parameter values with high prior likelihood. If not provided,
              optimization is reduced to Maximum Likelihood Estimation (MLE).
            params: A list of parameter values scipy.optimize.minimize will fit.

    Out:
        res: scipy OptimizeResult object.
    """
    if prior is None:

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
    )
    return res
