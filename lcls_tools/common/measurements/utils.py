from typing import Annotated
import numpy as np
from pydantic import BeforeValidator
import time


def calculate_statistics(data: np.ndarray, name):
    return {
        f"{name}_mean": np.mean(data),
        f"{name}_std": np.std(data),
        f"{name}_q05": np.quantile(data, 0.05),
        f"{name}_q95": np.quantile(data, 0.95),
    }


def ensure_numpy_array(v):
    return v if isinstance(v, np.ndarray) else np.array(v)


def collect_with_size_check(
    collector_func, expected_points, *collector_args, logger, max_retries=3, delay=0.5
):
    """
    Collects data using the provided function and checks its size.
    Retries collection if the data size does not match the expected points.
    Parameters:
        collector_func (callable): Function to collect data.
        expected_points (int): Expected number of data points.
        max_retries (int): Maximum number of retries on size mismatch.
        delay (float): Delay in seconds between retries.
        *args, **kwargs: Arguments to pass to the collector function.
    Returns:
        Collected data if size matches expected points.
    """
    for attempt in range(max_retries):
        data = collector_func(*collector_args)
        size = len(data) if data is not None else 0

        if size == expected_points:
            return data

        if logger is not None:
            logger.warning(
                "Data size mismatch: expected %d, got %d. Retrying (%d/%d)...",
                expected_points,
                size,
                attempt + 1,
                max_retries,
            )
        if delay > 0:
            time.sleep(delay)

    raise RuntimeError(
        f"Failed to collect data of expected size {expected_points} after {max_retries} attempts."
    )


NDArrayAnnotatedType = Annotated[np.ndarray, BeforeValidator(ensure_numpy_array)]
