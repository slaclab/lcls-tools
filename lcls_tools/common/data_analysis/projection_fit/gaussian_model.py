import numpy as np
from scipy.stats import norm, gamma
from scipy.ndimage import gaussian_filter
from lcls_tools.common.data_analysis.projection_fit.method_base import MethodBase


class GaussianModel(MethodBase):
    """
    GaussianModel Class that finds initial param values for gaussian distribution
        and builds probability density functions for the likelyhood a param
        to be that value based on those initial param values

    - passing this class the variable profile_data automatically updates
        the initial values and and probability density functions to match that data
    """

    param_names: list = ["amplitude", "mean", "sigma", "offset"]
    param_bounds: np.ndarray = np.array(
        [[0.01, 1.0], [0.01, 1.0], [0.01, 5.0], [0.01, 1.0]]
    )

    def __init__(self, profile_data: np.ndarray = None):
        if profile_data is not None:
            self.profile_data = profile_data
            self.find_init_values(self.profile_data)
            self.find_priors(self.profile_data)

    def find_init_values(self, data: np.array) -> np.array:
        offset = float(np.min(data))
        amplitude = np.max(gaussian_filter(data, sigma=5)) - offset
        mean = np.argmax(gaussian_filter(data, sigma=5)) / (len(data))
        sigma = 0.1
        self.init_values_list = np.array([amplitude, mean, sigma, offset])
        self.init_values = {"amplitude":amplitude,"mean":mean,"sigma":sigma,"offset":offset}
        # if use_priors = True in projection_fit then find priors? use case where projection fit is instantiated with use_priors = False then flag is changed but you have no priors
        self.find_priors()
        #TODO:change to dictionary
        return self.init_values

    def find_priors(self) ->dict:
        """do initial guesses based on data and make distribution from that guess"""

        #amplitude_mean = init_values[0] #insert for zero<-index(param_name,'amp')
        amplitude_mean = self.init_values["amplitude"]
        amplitude_var = 0.05
        amplitude_alpha = (amplitude_mean**2) / amplitude_var
        amplitude_beta = amplitude_mean / amplitude_var
        amplitude_prior = gamma(amplitude_alpha, loc=0, scale=1 / amplitude_beta)
        #TODO:change to be compatible with init_values dictionary
        mean_prior = norm(self.init_values["mean"], 0.1)

        sigma_alpha = 2.5
        sigma_beta = 5.0
        sigma_prior = gamma(sigma_alpha, loc=0, scale=1 / sigma_beta)

        offset_prior = norm(self.init_values["offset"], 0.5)
        self.priors = {
            self.param_names[0]: amplitude_prior,
            self.param_names[1]: mean_prior,
            self.param_names[2]: sigma_prior,
            self.param_names[3]: offset_prior,
        }

        return self.priors

    @staticmethod
    def forward(x: float, params: dict) -> float:
        #TODO:implement calling _foward
        amplitude = params[0]
        mean = params[1]
        sigma = params[2]
        offset = params[3]
        #TODO: init scipy.norm has private attribute then reference it return 
        return amplitude * np.exp(-((x - mean) ** 2) / (2 * sigma**2)) + offset

        pass
    @staticmethod
    def _forward(x:float,params:np.ndarray) :
        amplitude = params[0]
        mean = params[1]
        sigma = params[2]
        offset = params[3]
        #TODO: init scipy.norm has private attribute then reference it return 
        return amplitude * np.exp(-((x - mean) ** 2) / (2 * sigma**2)) + offset

    def log_prior(self, params: list) -> float:
        #TODO:change to dictionary
        return np.sum([prior.logpdf(params[i]) for i, (key, prior) in enumerate(self.priors.items())])

