import json

import h5py
import numpy as np


def save_measurement_result(result, filepath: str):
    """
    Save a measurement result (e.g. EmittanceMeasurementResult)
    to a desired filepath (e.g. /path/to/file/my_result.h5)
    """
    with h5py.File(filepath, "w") as h5f:
        for field_name, value in result:
            # Save single arrays
            if isinstance(value, np.ndarray):
                h5f.create_dataset(field_name, data=value)
            # Save lists of arrays
            elif isinstance(value, list) and all(
                isinstance(v, np.ndarray) for v in value
            ):
                group = h5f.create_group(field_name)
                for i, array in enumerate(value):
                    group.create_dataset(str(i), data=array)
            # Skip None values
            elif value is None:
                continue
            # Try to save as JSON string, if not just string as is
            else:
                try:
                    h5f.attrs[field_name] = json.dumps(value)
                except TypeError:
                    h5f.attrs[field_name] = str(value)


def load_measurement_result(filepath: str, result_class: type):
    """
    Load a measurement result of some result class (e.g. EmittanceMeasurementResult)
    from some filepath (e.g. /path/to/file/my_result.h5)
    """
    data = {}

    with h5py.File(filepath, "r") as h5f:
        for key in h5f.keys():
            item = h5f[key]
            # Load single arrays
            if isinstance(item, h5py.Dataset):
                data[key] = item[()]
            # Load lists of arrays
            elif isinstance(item, h5py.Group):
                arrays = []
                for subkey in sorted(item.keys(), key=lambda x: int(x)):
                    arrays.append(item[subkey][()])
                data[key] = arrays

        for attr_key, attr_val in h5f.attrs.items():
            if isinstance(attr_val, bytes):  # h5py sometimes stores strings as bytes
                attr_val = attr_val.decode("utf-8")

            try:
                data[attr_key] = json.loads(attr_val)
            except json.JSONDecodeError:
                data[attr_key] = attr_val

    return result_class(**data)
