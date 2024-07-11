import numpy as np
from scipy.stats import norm, gamma
from lcls_tools.common.data_analysis.fit.method_base import MethodBase, ModelParameters, Parameter


gaussian_parameters = ModelParameters( name = 'Gaussian Parameters' ,
                                       parameters = 
                                         { 'mean': Parameter(bounds=[0.01, 1.0]),
                                          'sigma': Parameter(bounds=[0.01, 5.0]),
                                          'amplitude': Parameter(bounds=[0.01, 1.0]), 
                                          'offset': Parameter(bounds=[0.01, 1.0])
                                        }
                                     )



class GaussianModel(MethodBase):
    """
    GaussianModel Class that finds initial parameter values for gaussian distribution
    and builds probability density functions for the likelyhood a parameter
    to be that value based on those initial parameter values.
    Passing this class the variable profile_data automatically updates
    the initial values and and probability density functions to match that data.
    """
    model_parameters = gaussian_parameters
    
    def find_init_values(self) -> dict:
        """Fit data without optimization, return values."""

        data = self._profile_data
        x = np.linspace(0, 1, len(data))
        # init_fit = norm.pdf(data)
        offset = data.min() + .01
        amplitude = data.max() - offset

        weighted_mean = np.average(x, weights=data)
        weighted_sigma = np.sqrt(np.cov(x, aweights=data))

        
        init_values = {
            'mean': weighted_mean,
            'sigma': weighted_sigma,
            'amplitude': amplitude,
            'offset': offset
        }
        self.model_parameters.initial_values = init_values
        return init_values

    def find_priors(self) -> dict:
        """Do initial guesses based on data and make distribution from that guess."""
        #TODO: profile data setter method cals this and find values. should remove call to find values in that method.
        # but since priors aren't supposed to be included (i think?) in this PR I will not update this.
        init_values = self.find_init_values()
        amplitude_mean =init_values["amplitude"]
        amplitude_var = 0.05
        amplitude_alpha = (amplitude_mean**2) / amplitude_var
        amplitude_beta = amplitude_mean / amplitude_var
        amplitude_prior = gamma(amplitude_alpha, loc=0, scale=1 / amplitude_beta)

        # Creating a normal distribution of points around the inital mean.
        mean_prior = norm(init_values["mean"], 0.1)
        sigma_alpha = 2.5
        sigma_beta = 5.0
        sigma_prior = gamma(sigma_alpha, loc=0, scale=1 / sigma_beta)

        # Creating a normal distribution of points around initial offset.
        offset_prior = norm(init_values["offset"], 0.5)
        parameters = [parameter for parameter in init_values]
        priors = dict(zip(parameters,[mean_prior,sigma_prior,amplitude_prior,offset_prior])) 
        print(priors)   
        self.model_parameters.priors = priors
        return priors

    def _forward(self, x: np.array, method_parameter_list: np.array):
        # Load distribution parameters
        # needs to be array for scipy.minimize
        mean = method_parameter_list[0]
        sigma = method_parameter_list[1]
        amplitude = method_parameter_list[2]
        offset = method_parameter_list[3]
        return (
            np.sqrt(2 * np.pi) * amplitude * norm.pdf((x - mean) / sigma) + offset
        )



    #TODO: this is going to need some work
    def _log_prior(self, method_parameter_list: np.ndarray) -> float:
        return np.sum(
            [
                prior.logpdf(method_parameter_list[i])
                for i, prior in enumerate(self.model_parameters.priors)
            ]
        )
