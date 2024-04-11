from abc import ABC, abstractmethod
import numpy as np
from matplotlib import pyplot as plt


class MethodBase(ABC):
    """
    Base abstract class for all methods, which serves as the bare minimum skeleton code needed. Should be used only as a parent class
    to all method models.
    ---------------------------
    Arguments:
    param_names: list (list all of param names that the model will contain)
    param_guesses: np.ndarray (array that contains a guess as to what each param value is organized in the same order as param_names)
    param_bounds: np.ndarray (array that contains the lower and upper bound on for acceptable values of each parameter)
    """

    def __init__(self):
        self.param_names: list = None
        self.param_guesses: np.ndarray = None
        self.param_bounds: np.ndarray = None
        self.init_values: list = None

    @abstractmethod
    def find_init_values(self, data: np.ndarray) -> list:
        pass

    @abstractmethod
    def find_priors(self, data: np.ndarray) -> dict:
        pass

    def plot_init_values(self):
        """Plots init values as a function of forward and visually compares it to the initial distribution"""
        fig, axs = plt.subplots(1, 1, figsize=(10, 5))
        x = np.linspace(0, 1, len(self.distribution_data))
        y_fit = self.forward(x, self.init_values)
        axs.plot(x, self.distribution_data, label="Projection Data")
        axs.plot(x, y_fit, label="Initial Guess Fit Data")
        axs.set_xlabel("x")
        axs.set_ylabel("Forward(x)")
        axs.set_title("Initial Fit Guess")
        return fig, axs

    def plot_priors(self):
        """Plots prior distributions for each param in param_names"""
        num_plots = len(self.priors)
        fig, axs = plt.subplots(num_plots, 1, figsize=(10, 10))
        for i, (param, prior) in enumerate(self.priors.items()):
            x = np.linspace(0, self.param_bounds[i][-1], len(self.distribution_data))
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

    @staticmethod
    @abstractmethod
    def forward(x: np.array, params: np.array) -> np.array:
        pass

    def log_likelihood(self, x, y, params):
        return -np.sum((y - self.forward(x, params)) ** 2)

    @abstractmethod
    def log_prior(self, params):
        pass

    def loss(self, params, x, y, use_priors=False):
        loss_temp = -self.log_likelihood(x, y, params)
        if use_priors:
            loss_temp = loss_temp - self.log_prior(params)
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
    def distribution_data(self):
        """1d array typically projection data"""
        return self._distribution_data

    @distribution_data.setter
    def distribution_data(self, distribution_data):
        if not isinstance(distribution_data, np.ndarray):
            raise TypeError("Input must be ndarray")
        self._distribution_data = distribution_data
        self.find_priors(self._distribution_data)
