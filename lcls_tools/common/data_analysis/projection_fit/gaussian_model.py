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
        self.fitted_params_dict = {}    

    def find_init_values(self, data: np.ndarray) -> dict:
        offset = float(np.min(data))
        amplitude = np.max(gaussian_filter(data, sigma=5)) - offset
        mean = np.argmax(gaussian_filter(data, sigma=5)) / (len(data))
        sigma = 0.1
        self.init_values = {self.param_names[0]:amplitude,self.param_names[1]:mean,self.param_names[2]:sigma,self.param_names[3]:offset}
        
        return self.init_values

    def find_priors(self) ->dict:
        """do initial guesses based on data and make distribution from that guess"""

        amplitude_mean = self.init_values["amplitude"]
        amplitude_var = 0.05
        amplitude_alpha = (amplitude_mean**2) / amplitude_var
        amplitude_beta = amplitude_mean / amplitude_var
        amplitude_prior = gamma(amplitude_alpha, loc=0, scale=1 / amplitude_beta)

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

    #TODO:be more consistent with np.array,np.ndarray, lists

    @staticmethod
    def _forward(x:np.ndarray,params_list:np.ndarray):
        amplitude = params_list[0]
        mean = params_list[1]
        sigma = params_list[2]
        offset = params_list[3]
        #TODO: init scipy.norm has private attribute then reference it return 
        return amplitude * np.exp(-((x - mean) ** 2) / (2 * sigma**2)) + offset
        #normal = norm()
        #return amplitude* normal.pdf((x - mean) / sigma)  + offset

    def _log_prior(self, params: np.ndarray) -> float:
        return np.sum([prior.logpdf(params[i]) for i, (key, prior) in enumerate(self.priors.items())])

