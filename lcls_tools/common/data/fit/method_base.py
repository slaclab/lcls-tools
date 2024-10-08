from abc import ABC, abstractmethod
import numpy as np

from pydantic import BaseModel, ConfigDict
from scipy.stats import rv_continuous


class Parameter(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    bounds: list
    initial_value: float = None
    prior: rv_continuous = None


class ModelParameters(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str
    parameters: dict[str, Parameter]

    @property
    def bounds(self):
        return np.vstack(
            [np.array(parameter.bounds) for parameter in self.parameters.values()]
        )

    @property
    def initial_values(self):
        return np.array(
            [parameter.initial_value for parameter in self.parameters.values()]
        )

    @initial_values.setter
    def initial_values(self, initial_values: dict[str, float]):
        for parameter, initial_value in initial_values.items():
            self.parameters[parameter].initial_value = initial_value

    @property
    def priors(self):
        return np.array(
            [self.parameters[parameter].prior for parameter in self.parameters]
        )

    @priors.setter
    def priors(self, priors: dict[str, float]):
        for parameter, prior in priors.items():
            self.parameters[parameter].prior = prior


# TODO: define properties


class MethodBase(ABC):
    """
    Base abstract class for all fit methods, which serves as the bare minimum
    skeleton code needed. Should be used only as a parent class to all method
    models.
    ---------------------------
    Arguments:
    param_names: list (list all of param names that the model will contain)
    param_guesses: np.ndarray (array that contains a guess as to what
        each param value is organized in the same order as param_names)
    param_bounds: np.ndarray (array that contains the lower
        and upper bound on for acceptable values of each parameter)
    """

    parameters: ModelParameters = None

    @abstractmethod
    def find_init_values(self) -> list:
        ...

    @abstractmethod
    def find_priors(self, data: np.ndarray) -> dict:
        ...

    def forward(
        self, x: np.ndarray, method_parameter_dict: dict[str, float]
    ) -> np.ndarray:
        method_parameter_list = np.array(
            [
                method_parameter_dict[parameter_name]
                for parameter_name in self.parameters.parameters
            ]
        )
        return self._forward(x, method_parameter_list)

    @staticmethod
    @abstractmethod
    def _forward(x: np.ndarray, params: np.ndarray) -> np.ndarray:
        ...

    def log_prior(self, method_parameter_dict: dict[str, rv_continuous]):
        method_parameter_list = np.array(
            [
                method_parameter_dict[parameter_name]
                for parameter_name in self.parameters.parameters
            ]
        )
        return self._log_prior(method_parameter_list)

    @abstractmethod
    def _log_prior(self, params: np.ndarray):
        ...

    def log_likelihood(self, x: np.ndarray, y: np.ndarray, method_parameter_dict: dict):
        method_parameter_list = np.array(
            [
                method_parameter_dict[parameter_name]
                for parameter_name in self.parameters.parameters
            ]
        )
        return self._log_likelihood(x, y, method_parameter_list)

    def _log_likelihood(
        self, x: np.ndarray, y: np.ndarray, method_parameter_list: np.ndarray
    ):
        return -np.sum((y - self._forward(x, method_parameter_list)) ** 2)

    def loss(
        self,
        method_parameter_list: np.ndarray,
        x: np.ndarray,
        y: np.ndarray,
        use_priors: bool = False,
    ):
        loss_temp = -self._log_likelihood(x, y, method_parameter_list)
        if use_priors:
            loss_temp = loss_temp - self._log_prior(method_parameter_list)
        return loss_temp

    @property
    def profile_data(self):
        """1D array typically projection data"""
        return self._profile_data

    @profile_data.setter
    def profile_data(self, profile_data):
        if not isinstance(profile_data, np.ndarray):
            raise TypeError("Input must be ndarray")
        self._profile_data = profile_data

        self.find_init_values()
        self.find_priors()
        self.fitted_params_dict = {}
