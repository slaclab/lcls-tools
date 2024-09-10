import numpy as np
import scipy.optimize
import scipy.signal
from pydantic import BaseModel, ConfigDict
from lcls_tools.common.data.fit.method_base import MethodBase
from lcls_tools.common.data.fit.methods import GaussianModel


class ProjectionFit(BaseModel):
    """
    1d fitting class that allows users to choose the model with which the fit
    is performed, and if prior assumptions (bayesian regression) about
    the data should be used when performing the fit.
    Additionally there is an option to visualize the fitted data and priors.
    -To perform a 1d fit, call fit_projection(projection_data={*data_to_fit*})
    ------------------------
    Arguments:
    model: MethodBase (this argument is a child class object of method base
        e.g GaussianModel & DoubleGaussianModel)
    visualize_priors: bool (shows plots of the priors and init guess
                      distribution before fit)
    use_priors: bool (incorporates prior distribution information into fit)
    visualize_fit: bool (visualize the parameters as a function of the
                   forward function
        from our model compared to distribution data)
    """

    # TODO: come up with better name
    model_config = ConfigDict(arbitrary_types_allowed=True)
    model: MethodBase = GaussianModel()
    use_priors: bool = False

    def normalize(self, data: np.ndarray) -> np.ndarray:
        """
        Normalize a 1d array by scaling and shifting data
        s.t. data is between 0 and 1
        """
        data_copy = data.copy()
        normalized_data = (data_copy - np.min(data)) / (np.max(data) - np.min(data))
        return normalized_data

    def unnormalize_model_params(
        self, method_params_dict: dict, projection_data: np.ndarray
    ) -> np.ndarray:
        """
        Takes fitted and normalized params and returns them
        to unnormalized values i.e the true fitted values of the distribution
        """

        projection_data_range = np.max(projection_data) - np.min(projection_data)
        length = len(projection_data)
        for key, val in method_params_dict.items():
            if "sigma" in key or "mean" in key:
                true_fitted_val = val * length
            elif "offset" in key:
                true_fitted_val = val * projection_data_range + np.min(projection_data)
            else:
                true_fitted_val = val * projection_data_range
            temp = {key: true_fitted_val}
            method_params_dict.update(temp)
        return method_params_dict

    def model_setup(self, projection_data=np.ndarray) -> None:
        """sets up the model and init_values/priors"""
        self.model.profile_data = projection_data

    def fit_model(self) -> scipy.optimize._optimize.OptimizeResult:
        """
        Fits model params to distribution data and plots the fitted params
        as a function of the model.
        Returns optimizeResult object
        """
        x = np.linspace(0, 1, len(self.model.profile_data))
        y = self.model.profile_data

        init_values = self.model.parameters.initial_values
        bounds = self.model.parameters.bounds
        res = scipy.optimize.minimize(
            self.model.loss,
            init_values,
            args=(x, y, self.use_priors),
            bounds=bounds,
            method="Powell",
        )
        return res

    def fit_projection(self, projection_data: np.ndarray) -> dict:
        """
        type is dict[str, float]
        Wrapper function that does all necessary steps to fit 1d array.
        Returns a dictionary where the keys are the model params and their
        values are the params fitted to the data
        """
        assert len(projection_data.shape) == 1
        fitted_params_dict = {}
        normalized_data = self.normalize(projection_data)
        self.model_setup(projection_data=normalized_data)
        res = self.fit_model()

        for i, param in enumerate(self.model.parameters.parameters):
            fitted_params_dict[param] = (res.x)[i]
        self.model.fitted_params_dict = fitted_params_dict.copy()
        params_dict = self.unnormalize_model_params(fitted_params_dict, projection_data)
        return params_dict
