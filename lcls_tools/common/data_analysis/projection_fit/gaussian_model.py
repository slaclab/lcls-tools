import numpy as np
from scipy.stats import norm, gamma
from scipy.ndimage import gaussian_filter
from lcls_tools.common.data_analysis.projection_fit.method_base import MethodBase


class GaussianModel(MethodBase):
    """
    GaussianModel Class that finds initial param values for gaussian distribution
        and builds probability density functions for the likelyhood a param
        to be that value based on those initial param values

    - passing this class the variable distribution_data automatically updates
        the initial values and and probability density functions to match that data
    """

    param_names: list = ["amplitude", "mean", "sigma", "offset"]
    param_guesses: np.ndarray = np.array(
        [0.75, 0.5, 0.1, 0.2]
    )  # amp, mean, sigma,offset
    param_bounds: np.ndarray = np.array(
        [[0.01, 1.0], [0.01, 1.0], [0.01, 5.0], [0.01, 1.0]]
    )

    def __init__(self, distribution_data: np.ndarray = None):
        if distribution_data is not None:
            self.distribution_data = distribution_data
            self.find_priors(self.distribution_data)

    def find_init_values(self, data: np.array) -> list:
        offset = float(np.min(data))
        amplitude = np.max(gaussian_filter(data, sigma=5)) - offset
        mean = np.argmax(gaussian_filter(data, sigma=5)) / (len(data))
        sigma = 0.1
        self.init_values = [amplitude, mean, sigma, offset]
        return self.init_values

    def find_priors(self, data: np.array) -> None:
        """do initial guesses based on data and make distribution from that guess"""

        init_values = self.find_init_values(data)

        amplitude_mean = init_values[0]
        amplitude_var = 0.05
        amplitude_alpha = (amplitude_mean**2) / amplitude_var
        amplitude_beta = amplitude_mean / amplitude_var
        amplitude_prior = gamma(amplitude_alpha, loc=0, scale=1 / amplitude_beta)

        mean_prior = norm(init_values[1], 0.1)

        sigma_alpha = 2.5
        sigma_beta = 5.0
        sigma_prior = gamma(sigma_alpha, loc=0, scale=1 / sigma_beta)

        offset_prior = norm(init_values[3], 0.5)
        self.priors = {
            self.param_names[0]: amplitude_prior,
            self.param_names[1]: mean_prior,
            self.param_names[2]: sigma_prior,
            self.param_names[3]: offset_prior,
        }
        return self.priors

    @staticmethod
    def forward(x: float, params: list) -> float:
        amplitude = params[0]
        mean = params[1]
        sigma = params[2]
        offset = params[3]
        return amplitude * np.exp(-((x - mean) ** 2) / (2 * sigma**2)) + offset

    def log_prior(self, params: list) -> float:
        return np.sum(
            [
                prior.logpdf[params[i]]
                for i, (key, prior) in enumerate(self.priors.items())
            ]
        )
