from lcls_tools.common.data_analysis.fitting.fitting_tool import FittingTool
import numpy as np
import matplotlib.pyplot as plt


def gaussian(x, amp, mu, sig, offset):
    return amp * np.exp(-np.power(x - mu, 2.0) / (2 * np.power(sig, 2.0))) + offset


def super_gaussian(x, amp, mu, sig, P, offset):
    """Super Gaussian Function"""
    """Degree of P related to flatness of curve at peak"""
    return amp * np.exp((-abs(x - mu) ** P) / (2 * sig**P)) + offset


def double_gaussian(x, amp, mu, sig, amp2, nu, rho, offset):
    return (
        amp * np.exp(-np.power(x - mu, 2.0) / (2 * np.power(sig, 2.0)))
        + amp2 * np.exp(-np.power(x - nu, 2.0) / (2 * np.power(rho, 2.0)))
    ) + offset


x_data = np.arange(500)

# generated data for pure gaussian
test_params = [3, 125, 45, 1.5]
y_data = gaussian(x_data, *test_params)
y_noise = np.random.normal(size=len(x_data), scale=0.04)
y_test = y_data + y_noise
fitting_tool = FittingTool(y_test)
fits = fitting_tool.get_fit()
# print(test_params)
# print(fits)
y_gaussian_fit = gaussian(x_data, *fits["gaussian"])
y_super_gaussian_fit = super_gaussian(x_data, *fits["super_gaussian"])
y_double_gaussian_fit = double_gaussian(x_data, *fits["double_gaussian"])


# generated data for super gaussian
test_params_super_gauss = [4, 215, 75, 4, 1]
y_data_super_gauss = super_gaussian(x_data, *test_params_super_gauss)
y_test_super_gauss = y_data_super_gauss + y_noise
super_gauss_fitting_tool = FittingTool(y_test_super_gauss)

s_fits = super_gauss_fitting_tool.get_fit()
s_gaussian_fit = gaussian(x_data, *s_fits["gaussian"])
s_super_gaussian_fit = super_gaussian(x_data, *s_fits["super_gaussian"])
s_double_gaussian_fit = double_gaussian(x_data, *s_fits["double_gaussian"])

# generated data for double gaussian
test_params_double_gauss = [2, 100, 25, 10, 240, 25, 2]
y_data_double_gauss = double_gaussian(x_data, *test_params_double_gauss)
y_test_double_gauss = y_data_double_gauss + 3 * y_noise
double_gauss_fitting_tool = FittingTool(y_test_double_gauss)
d_fits = double_gauss_fitting_tool.get_fit()
d_gaussian_fit = gaussian(x_data, *d_fits["gaussian"])
d_super_gaussian_fit = super_gaussian(x_data, *d_fits["super_gaussian"])
d_double_gaussian_fit = double_gaussian(x_data, *d_fits["double_gaussian"])


fig, (ax1, ax2, ax3) = plt.subplots(3, 1)

# plots need legends
ax1.plot(x_data, y_test)
ax1.plot(x_data, y_gaussian_fit, "-.")
ax1.plot(x_data, y_super_gaussian_fit, "-.")
ax1.plot(x_data, y_double_gaussian_fit, "-.")


ax2.plot(x_data, y_test_super_gauss)
ax2.plot(x_data, s_gaussian_fit, "-.")
ax2.plot(x_data, s_super_gaussian_fit, "-.")
ax2.plot(x_data, s_double_gaussian_fit, "-.")

ax3.plot(x_data, y_test_double_gauss)
ax3.plot(x_data, d_gaussian_fit, "-.")
ax3.plot(x_data, d_super_gaussian_fit, "-.")
ax3.plot(x_data, d_double_gaussian_fit, "-.")

plt.show()


# right now performs all fits,
# needs option perform single fit only if passed get_fit(best_fit = True)
# needs nested dictionary structure
# {'gaussian':
#          'params':{
#                 'amp' :  3.00969146,
#                 'mu'  : 125.03092854,
#                 'sig' : 44.9545378,
#                 'offset' : 1.49578195
#                 }
#           ?'fitted_data': [...] yes/no?
#           'rmse': 7.970151073658837e-11
# }
# needs batch fitting option kwarg
# needs initial guess option kwarg
