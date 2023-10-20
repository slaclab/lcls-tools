import numpy as np
import scipy.ndimage as snd
from scipy import asarray
import matplotlib.pyplot as plt
import lcls_tools.common.data_analysis.fitting.fit_gaussian as fg


def fliplr(image):
    """Flip over vertical axis"""
    return np.fliplr(image)


def flipud(image):
    """Flip over horizontal axis"""
    return np.flipud(image)


def center_of_mass(image, sigma=5):
    """Find center of mass, sigma sets threshold"""
    return snd.center_of_mass(image > image.mean() + sigma * image.std())


def average_image(images):
    """If we can do things with an average image, do it!"""
    return sum(images) / len(images)


def shape_image(image, x_size, y_size):
    """Shape typical returned array, rows x columns so y x x"""
    return image.reshape(y_size, x_size)


def x_projection(image, axis=0, subtract_baseline=True):
    """Expects ndarray, return x projection"""
    proj = np.sum(image, axis=0)
    if subtract_baseline:
        return proj - min(proj)

    return proj


def y_projection(image, subtract_baseline=True):
    """Expects ndarray, return y projection"""
    proj = np.sum(image, axis=1)
    if subtract_baseline:
        return proj - min(proj)

    return proj


def gauss_func(x, a, x0, sigma):
    return a * np.exp(-((x - x0) ** 2) / (2 * sigma**2))


def gauss_fit(projection, plot=False):
    x = asarray(range(len(projection)))
    data, _, step = fg.process_data(projection)
    guess = fg.get_guess(x, data, step, False, num_peaks=1)[0]
    x0_x, a_x, sigma_x = fg.get_fit(data, x, guess)[2:]

    if plot:
        plt.plot(x, projection, label="data")
        plt.plot(x, gauss_func(x, a_x, x0_x, sigma_x), label="fit")
        plt.legend()
        plt.show()

    return x, a_x, x0_x, sigma_x
