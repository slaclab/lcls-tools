from typing import Annotated
import numpy as np
from pydantic import BeforeValidator


def calculate_statistics(data: np.ndarray, name):
    return {
        f"{name}_mean": np.mean(data),
        f"{name}_std": np.std(data),
        f"{name}_q05": np.quantile(data, 0.05),
        f"{name}_q95": np.quantile(data, 0.95),
    }


def ensure_numpy_array(v):
    return v if isinstance(v, np.ndarray) else np.array(v)


NDArrayAnnotatedType = Annotated[np.ndarray, BeforeValidator(ensure_numpy_array)]
