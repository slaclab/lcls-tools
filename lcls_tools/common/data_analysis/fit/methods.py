import numpy as np
from scipy.stats import norm, gamma
from lcls_tools.common.data_analysis.fit.method_base import MethodBase


class GaussianModel(MethodBase):
    """
    GaussianModel Class that finds initial parameter values for gaussian distribution
    and builds probability density functions for the likelyhood a parameter
    to be that value based on those initial parameter values.
    Passing this class the variable profile_data automatically updates
    the initial values and and probability density functions to match that data.
    """

    param_names: list = ["mean", "sigma", "amplitude", "offset"]
    # TODO: remove if not needed
    # param_bounds: np.ndarray = np.array(
    #    [[0.01, 1.0], [0.01, 1.0], [0.01, 5.0], [0.01, 1.0]]
    # )

    def __init__(self, profile_data: np.ndarray):
        self.profile_data = profile_data
        self.find_init_values()
        self.find_priors()
        self.fitted_params_dict = {}

    def find_init_values(self) -> dict:
        """Fit data without optimization, return values."""
        data = self.profile_data
        init_fit = norm.pdf(data)
        amplitude = init_fit.max() - init_fit.min()

        self.init_values = {
            self.param_names[0]: data.mean(),
            self.param_names[1]: data.std(),
            self.param_names[2]: amplitude,
            self.param_names[3]: init_fit.min(),
        }
        return self.init_values

    def find_priors(self) -> dict:
        """Do initial guesses based on data and make distribution from that guess."""
        # Creating a gamma distribution around the inital amplitude.
        # TODO: add to comments on why gamma vs. normal dist used for priors.
        amplitude_mean = self.init_values["amplitude"]
        amplitude_var = 0.05
        amplitude_alpha = (amplitude_mean**2) / amplitude_var
        amplitude_beta = amplitude_mean / amplitude_var
        amplitude_prior = gamma(amplitude_alpha, loc=0, scale=1 / amplitude_beta)

        # Creating a normal distribution of points around the inital mean.
        mean_prior = norm(self.init_values["mean"], 0.1)
        # TODO: remove hard coded numbers?
        sigma_alpha = 2.5
        sigma_beta = 5.0
        sigma_prior = gamma(sigma_alpha, loc=0, scale=1 / sigma_beta)

        # Creating a normal distribution of points around initial offset.
        offset_prior = norm(self.init_values["offset"], 0.5)
        self.priors = {
            self.param_names[0]: mean_prior,
            self.param_names[1]: sigma_prior,
            self.param_names[2]: amplitude_prior,
            self.param_names[3]: offset_prior,
        }
        return self.priors

    # TODO:be more consistent with np.array,np.ndarray, lists
    # TODO: does this need to be a static method?
    def _forward(self, x: np.array, params: dict):
        # Load distribution parameters
        mean = params["mean"]
        sigma = params["sigma"]
        return norm.pdf(x, loc=mean, scale=sigma)

    # TODO: remove when above is confirmed the same/below not needed.
    # @staticmethod
    # def _forward(x: np.ndarray, params_list: np.ndarray):
    #    amplitude = params_list[0]
    #    mean = params_list[1]
    #    sigma = params_list[2]
    #    offset = params_list[3]
    #    normal = norm()
    #    return ((np.sqrt(2 * np.pi)) * amplitude) * normal.pdf(
    #        (x - mean) / sigma
    #    ) + offset

    def _log_prior(self, params: np.ndarray) -> float:
        return np.sum(
            [
                prior.logpdf(params[i])
                for i, (key, prior) in enumerate(self.priors.items())
            ]
        )
