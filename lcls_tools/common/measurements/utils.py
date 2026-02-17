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
    device, collector_func, buffer, logger, max_retries=3, delay=3
):
    """
    Collects data using the provided function and checks its size.
    Retries collection if the data size does not match the expected points.
    Parameters:
        device (Device): A slac-tools Device object
        collector_func (string): Function name (as a string) to collect data.
        buffer (edef.BSABuffer): Buffer object containing measurement data.
        logger (logging.Logger): Logger for logging warnings.
        max_retries (int): Maximum number of retries on size mismatch.
        delay (float): Delay in seconds between retries.
        *args, **kwargs: Arguments to pass to the collector function.
    Returns:
        Collected data if size matches expected points.
    """
    method = getattr(device, collector_func)
    for attempt in range(max_retries):
        data = method(buffer)
        size = len(data) if data is not None else 0
        expected_points = buffer.n_measurements

        if size == expected_points:
            return data

        if logger is not None:
            logger.warning(
                "Data size mismatch for %s %s: expected %d, got %d. Retrying (%d/%d)...",
                device.name,
                collector_func,
                expected_points,
                size,
                attempt + 1,
                max_retries,
            )
        else:
            print(
                f"Warning: Data size mismatch for {device.name} {collector_func}: "
                f"expected {expected_points}, got {size}. Retrying ({attempt + 1}/{max_retries})..."
            )
        if delay > 0:
            time.sleep(delay)

    raise RuntimeError(
        f"Unable to collect complete {collector_func} data for {device.name}. "
        f"Expected {expected_points} points but retrieved {size} after {max_retries} attempts."
    )


NDArrayAnnotatedType = Annotated[np.ndarray, BeforeValidator(ensure_numpy_array)]
