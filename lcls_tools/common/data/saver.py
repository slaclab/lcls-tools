from typing import Dict, Any
import h5py
import numpy as np
from pydantic import validate_call
import pandas as pd


class H5Saver:
    """
    Class to dump and load dictionaries to and from HDF5 files.

    Methods
    -------
    dump(data, filepath)
        Dumps a dictionary to an HDF5 file.
    load(filepath)
        Loads a dictionary from an HDF5 file.
    """

    def __init__(self):
        """
        Initialize the H5Saver class.

        Parameters
        ----------
        string_dtype : str, optional
            The encoding to use when saving string data. Default is 'utf-8'.
        """
        self.string_dtype = "utf-8"
        self.supported_types = (bool, int, float, np.integer, np.floating)

    @validate_call
    def dump(self, data: Dict[str, Any], filepath: str):
        """
        Save a dictionary to an HDF5 file. 5s

        Parameters
        ----------
        data : Dict[str, Any]
            The dictionary to save.
        filepath : str
            The path to save the HDF5 file.

        Returns
        -------
        None
        """
        dt = h5py.string_dtype(encoding=self.string_dtype)

        def recursive_save(d, f):
            for key, val in d.items():
                if key == "attrs":
                    f.attrs.update(val or h5py.Empty("f4"))
                elif isinstance(val, dict):
                    group = f.create_group(key, track_order=True)
                    recursive_save(val, group)
                elif isinstance(val, list):
                    if all(isinstance(ele, self.supported_types) for ele in val):
                        f.create_dataset(key, data=val, track_order=True)
                    elif all(isinstance(ele, np.ndarray) for ele in val):
                        # save np.arrays as datasets
                        for i, ele in enumerate(val):
                            f.create_dataset(f"{key}/{i}", data=ele, track_order=True)
                            if ele.dtype == np.dtype("O"):
                                f.create_dataset(
                                    f"{key}/{i}",
                                    data=str(ele),
                                    dtype=dt,
                                    track_order=True,
                                )
                    elif all(isinstance(ele, dict) for ele in val):
                        # save dictionaries as groups recursively
                        for i, ele in enumerate(val):
                            group = f.create_group(f"{key}/{i}", track_order=True)
                            recursive_save(ele, group)
                    elif all(isinstance(ele, tuple) for ele in val):
                        # save tuples as np.array
                        for i, ele in enumerate(val):
                            val_array = np.array(ele)
                            f.create_dataset(
                                f"{key}/{i}", data=val_array, track_order=True
                            )
                    elif all(isinstance(ele, list) for ele in val):
                        # if it's  a list of lists, save as np.array if homogeneous and type allows
                        # else save as strings
                        for i, ele in enumerate(val):
                            if all(isinstance(j, self.supported_types) for j in ele):
                                f.create_dataset(
                                    f"{key}/{i}", data=np.array(ele), track_order=True
                                )
                            else:
                                f.create_dataset(
                                    f"{key}/{i}",
                                    data=str(ele),
                                    dtype=dt,
                                    track_order=True,
                                )
                    else:
                        for i, ele in enumerate(val):
                            # if it's a list of mixed types, save as strings
                            if isinstance(ele, str):
                                f.create_dataset(
                                    f"{key}/{i}", data=ele, dtype=dt, track_order=True
                                )
                            else:
                                f.create_dataset(
                                    f"{key}/{i}",
                                    data=str(ele),
                                    dtype=dt,
                                    track_order=True,
                                )
                elif isinstance(val, self.supported_types):
                    f.create_dataset(key, data=val, track_order=True)
                elif isinstance(val, np.ndarray):
                    if val.dtype != np.dtype("O"):
                        f.create_dataset(key, data=val, track_order=True)
                    else:
                        f.create_dataset(key, data=str(val), dtype=dt, track_order=True)
                elif isinstance(val, tuple):
                    val_array = np.array(val)
                    f.create_dataset(key, data=val_array, track_order=True)
                elif isinstance(val, str):
                    # specify string dtype to avoid issues with encodings
                    f.create_dataset(key, data=val, dtype=dt, track_order=True)
                elif isinstance(val, pd.DataFrame):
                    # save DataFrame as a group with datasets for columns
                    group = f.create_group(key)
                    group.attrs["pandas_type"] = "dataframe"
                    group.attrs["columns"] = list(val.columns)
                    for col in val.columns:
                        if val[col].dtype == np.dtype("O"):
                            try:
                                val[col] = val[col].astype("float64")
                            except ValueError:
                                val[col] = val[col].astype("string")
                        group.create_dataset(col, data=val[col].values)
                else:
                    f.create_dataset(key, data=str(val), dtype=dt, track_order=True)

        with h5py.File(filepath, "w") as file:
            recursive_save(data, file)

    def load(self, filepath):
        """
        Load a dictionary from an HDF5 file.

        Parameters
        ----------
        filepath : str
            The path to the file to load.

        Returns
        -------
        dict
            The dictionary loaded from the file.
        """

        def recursive_load(f):
            d = {"attrs": dict(f.attrs)} if f.attrs else {}
            for key, val in f.items():
                if isinstance(val, h5py.Group):
                    if (
                        "pandas_type" in val.attrs
                        and val.attrs["pandas_type"] == "dataframe"
                    ):
                        # Load DataFrame from group
                        columns = val.attrs["columns"]
                        data = {}
                        for col in columns:
                            data[col] = val[col][:]
                        d[key] = pd.DataFrame(data)
                    else:
                        d[key] = recursive_load(val)
                elif isinstance(val, h5py.Dataset):
                    if isinstance(val[()], bytes):
                        d[key] = val[()].decode(self.string_dtype)
                    else:
                        d[key] = val[()]
            return d

        with h5py.File(filepath, "r") as file:
            return recursive_load(file)
