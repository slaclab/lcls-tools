from abc import ABC, abstractmethod
import numpy as np
from matplotlib import pyplot as plt


class MethodBase(ABC):
    """
    Base abstract class for all methods, which serves as the bare minimum skeleton code needed.
    Should be used only as a parent class to all method models.
    ---------------------------
    Arguments:
    param_names: list (list all of param names that the model will contain)
    param_guesses: np.ndarray (array that contains a guess as to what
        each param value is organized in the same order as param_names)
    param_bounds: np.ndarray (array that contains the lower
        and upper bound on for acceptable values of each parameter)
    """

    def __init__(self):
        self.param_names: list = None     
        self.param_bounds: np.ndarray = None
        self.init_values: dict = None
        self.fitted_params_dict: dict = None

    @abstractmethod
    def find_init_values(self, data: np.ndarray) -> list:
        ...
    

    @abstractmethod
    def find_priors(self, data: np.ndarray) -> dict:
        ...

    def plot_init_values(self):
        init_values = np.array(list(self.init_values.values()))
        """Plots init values as a function of forward and visually compares it to the initial distribution"""
        fig, axs = plt.subplots(1, 1)
        x = np.linspace(0, 1, len(self.profile_data))
        y_fit = self._forward(x, init_values)
        axs.plot(x, self.profile_data, label="Projection Data")
        axs.plot(x, y_fit, label="Initial Guess Fit Data")
        axs.set_xlabel("x")
        axs.set_ylabel("Forward(x)")
        axs.set_title("Initial Fit Guess")
        return fig, axs

    def plot_priors(self):
        """Plots prior distributions for each param in param_names"""
        num_plots = len(self.priors)
        fig, axs = plt.subplots(num_plots, 1)
        for i, (param, prior) in enumerate(self.priors.items()):
            x = np.linspace(0, self.param_bounds[i][-1], len(self.profile_data))
            axs[i].plot(x, prior.pdf(x))
            axs[i].axvline(
                self.param_bounds[i, 0],
                ls="--",
                c="k",
            )
            axs[i].axvline(self.param_bounds[i, 1], ls="--", c="k", label="bounds")
            axs[i].set_title(param + " prior")
            axs[i].set_ylabel("Density")
            axs[i].set_xlabel(param)
        fig.tight_layout()
        return fig, axs

    def forward(self, x: np.ndarray, params: dict) -> np.ndarray:
        #TODO:test new usage
        print('calling forward')
        params_list = np.array([params[name] for name in self.param_names])
        print(params_list)
        return self._forward(x,params_list)
    
    @staticmethod
    @abstractmethod
    def _forward(x: np.ndarray, params: np.ndarray) -> np.ndarray:
        ...

    def log_prior(self, params:dict):
        #TODO:test new usage
        params_list = np.array([params[name] for name in self.param_names])
        return self._log_prior(params_list)

    @abstractmethod
    def _log_prior(self, params:np.ndarray):
        ...

    def log_likelihood(self, x:np.ndarray, y:np.ndarray, params:dict):
        #TODO:test new usage
        params_list = np.array([params[name] for name in self.param_names])
        return self._log_likelihood(x,y,params_list)
    
    def _log_likelihood(self, x:np.ndarray, y:np.ndarray, params:np.ndarray):
        return -np.sum((y - self._forward(x, params)) ** 2)

    def loss(self, params, x, y, use_priors=False):
        #TODO:implement using private functions _log_likelihood and _log_prior
        loss_temp = -self._log_likelihood(x, y, params)
        if use_priors:
            loss_temp = loss_temp - self._log_prior(params)
        return loss_temp

    @property
    def priors(self):
        """Initial Priors store in a dictionary where the keys are the complete set of parameters of the Model"""
        return self._priors

    @priors.setter
    def priors(self, priors):
        if not isinstance(priors, dict):
            raise TypeError("Input must be a dictionary")
        self._priors = priors

    @property
    def profile_data(self):
        """1d array typically projection data"""
        return self._profile_data

    @profile_data.setter
    def profile_data(self, profile_data):
        if not isinstance(profile_data, np.ndarray):
            raise TypeError("Input must be ndarray")
        self._profile_data = profile_data
        self.find_init_values(self._profile_data)
        self.find_priors()