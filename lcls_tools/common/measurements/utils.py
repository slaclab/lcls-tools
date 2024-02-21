import numpy as np
from numpy import ndarray


def calculate_statistics(data: ndarray, name):
    return {
        f"{name}_mean": np.mean(data),
        f"{name}_std": np.std(data),
        f"{name}_q05": np.quantile(data, 0.05),
        f"{name}_q95": np.quantile(data, 0.95),
    }
