import numpy as np
from scipy.optimize import curve_fit
import statistics
from sklearn.metrics import mean_squared_error

# from scipy.ndimage import gaussian_filter
# from scipy.special import erf


class FittingTool:
    def __init__(self, data: np.array, **kwargs):
        """tool takes in the data points for some distribution"""

        self.options = {
            "batch_mode": False,
            "best_fit": False,
            "data_dictionary": {},
            "initial_guess_dictionary": {},
            "n_restarts": 10,
        }
        self.options.update(kwargs)

        self.distribution_data = data
        self.x = np.arange(len(data))

        # need like some dictionary looper here.

        # print(self.options)

        self.initial_params = self.guess_params(
            self.distribution_data, self.options["initial_guess_dictionary"]
        )

    def guess_params(self, distribution: np.array, initial_guess: dict = {}) -> dict:
        initial_params = {}

        offset = initial_guess.pop("offset", distribution.min())
        amplitude = initial_guess.pop("amplitude", distribution.max() - offset)
        mu = initial_guess.pop("mu", np.argmax(distribution))
        sigma = initial_guess.pop("sigma", distribution.shape[0] / 5)
        gaussian_params = {
            "params": {"amp": amplitude, "mu": mu, "sig": sigma, "offset": offset}
        }
        initial_params["gaussian"] = gaussian_params
        # super gaussian extension
        power = 2
        super_gaussian_params = {
            "params": {
                "amp": amplitude,
                "mu": mu,
                "sig": sigma,
                "P": power,
                "offset": offset,
            }
        }
        initial_params["super_gaussian"] = super_gaussian_params
        #  for double gaussian
        #  will make new helper functions for peaks and widths
        amplitude2 = amplitude / 3
        nu = mu / 2
        rho = sigma / 2
        double_gaussian_params = {
            "params": {
                "amp": amplitude,
                "mu": mu,
                "sig": sigma,
                "amp2": amplitude2,
                "nu": nu,
                "rho": rho,
                "offset": offset,
            }
        }
        initial_params["double_gaussian"] = double_gaussian_params

        return initial_params

    def unpack_dictionary_to_ordered_list(self, method, param_dict):
        ordered_list_param_vals = []
        param_names = method.__code__.co_varnames
        param_names = list(param_names)
        for i in range(len(param_names)):
            if param_names[i] == "x":
                continue
            else:
                ordered_list_param_vals.append(param_dict[param_names[i]])
        return ordered_list_param_vals

    def pack_list_to_param_dict(self, method, param_list):
        packed_dict = {}
        param_names = method.__code__.co_varnames
        param_names = list(param_names)
        if param_names[0] == "x":
            param_names.pop(0)
        try:
            for i in range(len(param_names)):
                packed_dict[param_names[i]] = param_list[i]

        except TypeError:
            print("Type Error")
            print("param names list ", param_names)
            print("param vals list ", param_list)

        params_dict = {}
        params_dict["params"] = packed_dict
        return params_dict

    def get_fit(self, best_fit: bool = False) -> dict:
        """Return fit parameters to data y such that y = method(x,parameters)"""
        fits = {}

        for key, val in self.initial_params.items():
            method = getattr(self, key)
            ordered_param_vals = self.unpack_dictionary_to_ordered_list(
                method, val["params"]
            )
            fit_params = self.iterative_fit(
                method,
                self.x,
                self.distribution_data,
                ordered_param_vals,
                self.options["n_restarts"],
            )
            packed_dict = self.pack_list_to_param_dict(method, fit_params)
            y_fitted = method(self.x, *fit_params)
            rmse = self.calculate_rms_deviation(self.distribution_data, y_fitted)
            packed_dict["rmse"] = rmse
            fits[key] = packed_dict

        return fits

    def iterative_fit(self, method, x_data, y_data, param_guesses, n_restarts):
        if n_restarts > 0:
            try:
                fit_params = curve_fit(method, x_data, y_data, param_guesses)[0]
                return fit_params
            except RuntimeError:
                self.iterative_fit(
                    method, x_data, y_data, param_guesses, n_restarts - 1
                )
        else:
            print("failed returning param guesses: ", param_guesses)
        return param_guesses

    def check_skewness(self, outcomes, mu, sigma):
        """Checks for skewness in dataset, neg if mean<median<mode, pos if opposite"""
        mode = statistics.mode(outcomes)
        pearsons_coeff = (mu - mode) / sigma
        print(pearsons_coeff)
        return pearsons_coeff

    def check_kurtosis(self):
        """greater kurtosis higher the peak"""
        """how fast tails approaching zero, more outliers with higher kurtosis"""
        """positive excess - tails approach zero slower"""
        """negative excess - tails approach zero faster"""
        print("This function is not implemented")
        # do later
        raise NotImplementedError

    def find_peaks(self):
        print("This function is not implemented")
        raise NotImplementedError

    def find_widths(self):
        print("This function is not implemented")
        raise NotImplementedError

    def find_runs(self):
        print("This function is not implemented")
        raise NotImplementedError

    def find_moments(self):
        """mean, sigma, skewness, kurtosis"""
        print("This function is not implemented")
        raise NotImplementedError

    def truncate_distribution(x, lower_bound: float = None, upper_bound: float = None):
        if lower_bound is None:
            lower_bound = x.min()
        if upper_bound is None:
            upper_bound = x.max()
        truncated_x = np.clip(x, lower_bound, upper_bound)
        return truncated_x

    def calculate_rms_deviation(
        self, predictions: np.array, targets: np.array
    ) -> float:
        rms_deviation = np.sqrt(mean_squared_error(targets, predictions, squared=False))
        return rms_deviation

    # def calculate_unbiased_rms_deviated(x: np.array = None):
    #    mean = np.mean(x)
    #    rms_deviation = np.sqrt(np.power(sum(x - mean), 2) / len(x))
    #    return rms_deviation

    @staticmethod
    def gaussian(x, amp, mu, sig, offset):
        """Gaussian Function"""
        """need a way to guess params if amp =/"""
        return amp * np.exp(-np.power(x - mu, 2.0) / (2 * np.power(sig, 2.0))) + offset

    @staticmethod
    def gaussian_with_linear_background(x, amp, mu, sig, offset, slope):
        return (
            amp * np.exp(-np.power(x - mu, 2.0) / (2 * np.power(sig, 2.0)))
            + offset
            + slope * x
        )

    @staticmethod
    def super_gaussian(x, amp, mu, sig, P, offset):
        """Super Gaussian Function"""
        """Degree of P related to flatness of curve at peak"""
        return amp * np.exp((-abs(x - mu) ** (P)) / (2 * sig ** (P))) + offset

    @staticmethod
    def double_gaussian(x, amp, mu, sig, amp2, nu, rho, offset):
        return (
            amp * np.exp(-np.power(x - mu, 2.0) / (2 * np.power(sig, 2.0)))
            + amp2 * np.exp(-np.power(x - nu, 2.0) / (2 * np.power(rho, 2.0)))
        ) + offset

    @staticmethod
    def two_dim_gaussian(x, y, A, x0, y0, sigma_x, sigma_y):
        """2-D Gaussian Function"""
        """Possible usage fitting an image with the 1-D projections"""
        return A * np.exp(
            -((x - x0) ** 2) / (2 * sigma_x**2) - (y - y0) ** 2 / (2 * sigma_y**2)
        )
