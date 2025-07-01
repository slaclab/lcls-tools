import h5py
import numpy as np
import pandas as pd
from pathlib import PosixPath


class H5Saver:
    """
    Serialize and deserialize Python data structures to and from HDF5 files.

    Supports:
        - dict, list, tuple, np.ndarray, pandas.DataFrame,
          scalars (int, float, bool, str), None, PosixPath.

    Raises
    ------
    NotImplementedError
        If an unsupported type or structure is encountered.
    """

    def __init__(self):
        """
        Initialize the H5Saver.

        Sets string encoding and supported scalar types.
        """
        self.string_dtype = "utf-8"
        self.supported_scalars = (
            bool,
            int,
            float,
            str,
            np.integer,
            np.floating,
            np.bool_,
        )

    def dump(self, data, filepath):
        """
        Serialize a Python dictionary to an HDF5 file.

        Parameters
        ----------
        data : dict
            The data to serialize. Can contain nested dicts, lists, tuples,
            numpy arrays, pandas DataFrames, scalars, None, and PosixPath.
        filepath : str
            Path to the HDF5 file to write.

        Raises
        ------
        NotImplementedError
            If an unsupported type or structure is encountered.
        """
        h5str = h5py.string_dtype(encoding=self.string_dtype)

        def recursive_save(key, val, f):
            """
            Recursively save a key-value pair to the HDF5 group or file.

            Parameters
            ----------
            key : str
                The key or name for the group/dataset.
            val : Any
                The value to serialize.
            f : h5py.Group or h5py.File
                The HDF5 group or file to write to.

            Raises
            ------
            NotImplementedError
                If an unsupported type or structure is encountered.
            """
            # Handle dictionaries
            if isinstance(val, dict):
                group = f.create_group(key, track_order=True)
                if not val:
                    group.attrs["is_empty_dict"] = True  # Mark empty dicts
                for k, v in val.items():
                    recursive_save(k, v, group)
            # Handle pandas DataFrames
            elif isinstance(val, pd.DataFrame):
                group = f.create_group(key)
                group.attrs["pandas_type"] = "dataframe"
                group.attrs["columns"] = list(val.columns)
                group.attrs["dtypes"] = [str(dt) for dt in val.dtypes]
                for col in val.columns:
                    col_data = val[col].values
                    # Handle string/object columns
                    if val[col].dtype == np.dtype("O") or np.issubdtype(
                        val[col].dtype, np.str_
                    ):
                        try:
                            col_data = col_data.astype("float64")
                            group.create_dataset(col, data=col_data)
                        except ValueError:
                            group.create_dataset(
                                col,
                                data=col_data.astype(
                                    h5py.string_dtype(encoding=self.string_dtype)
                                ),
                                dtype=h5py.string_dtype(encoding=self.string_dtype),
                            )
                    else:
                        group.create_dataset(col, data=col_data)
            # Handle numpy arrays
            elif isinstance(val, np.ndarray):
                if val.dtype == np.dtype("O"):
                    # Disallow np.ndarray of dicts
                    if any(isinstance(x, dict) for x in val):
                        raise NotImplementedError(
                            "np.ndarray of dicts is not supported."
                        )
                    # Save object arrays as group
                    group = f.create_group(key, track_order=True)
                    group.attrs["_ndarray"] = True
                    for i, ele in enumerate(val.tolist()):
                        recursive_save(str(i), ele, group)
                else:
                    # Save homogeneous arrays as dataset
                    f.create_dataset(key, data=val, track_order=True)
                    f[key].attrs["_type"] = "ndarray"
            # Handle lists
            elif isinstance(val, list):
                # Disallow lists of dicts or heterogeneous lists with dicts, but only if not empty
                if len(val) > 0 and all(isinstance(x, dict) for x in val):
                    raise NotImplementedError(
                        "Lists of dictionaries are not supported."
                    )
                if len(val) > 0 and any(isinstance(x, dict) for x in val):
                    raise NotImplementedError(
                        "Heterogeneous lists containing dictionaries are not supported."
                    )
                group = f.create_group(key, track_order=True)
                if not val:
                    group.attrs["_empty_list"] = True  # Mark empty list
                for i, ele in enumerate(val):
                    recursive_save(str(i), ele, group)
            # Handle tuples
            elif isinstance(val, tuple):
                # Disallow tuple of dicts, but only if not empty
                if len(val) > 0 and all(isinstance(x, dict) for x in val):
                    raise NotImplementedError(
                        "Tuples of dictionaries are not supported."
                    )
                group = f.create_group(key, track_order=True)
                group.attrs["_tuple"] = True
                if not val:
                    group.attrs["_empty_tuple"] = True  # Mark empty tuple
                for i, ele in enumerate(val):
                    recursive_save(str(i), ele, group)
            # Handle PosixPath
            elif isinstance(val, PosixPath):
                f.create_dataset(key, data=str(val), dtype=h5str, track_order=True)
                f[key].attrs["_type"] = "posixpath"
            # Handle None
            elif val is None:
                f.create_dataset(key, data="None", dtype=h5str, track_order=True)
                f[key].attrs["_type"] = "none"
            # Handle scalars
            elif isinstance(val, self.supported_scalars):
                f.create_dataset(key, data=val, track_order=True)
                f[key].attrs["_type"] = type(val).__name__
            # Raise for unsupported types
            else:
                raise NotImplementedError(f"Type {type(val)} is not supported.")

        # Open file and start recursive save
        with h5py.File(filepath, "w") as file:
            for k, v in data.items():
                recursive_save(k, v, file)

    def load(self, filepath):
        """
        Deserialize an HDF5 file into a Python dictionary.

        Parameters
        ----------
        filepath : str
            Path to the HDF5 file to read.

        Returns
        -------
        dict
            The reconstructed data structure, with original types restored.

        Raises
        ------
        NotImplementedError
            If an unsupported type or structure is encountered.
        """

        def recursive_load(f):
            """
            Recursively load an HDF5 group or dataset.

            Parameters
            ----------
            f : h5py.Group or h5py.Dataset
                The HDF5 group or dataset to read.

            Returns
            -------
            Any
                The reconstructed Python object.
            """
            # Handle groups (dict, list, tuple, ndarray, DataFrame, etc.)
            if isinstance(f, h5py.Group):
                # Handle DataFrame
                if "pandas_type" in f.attrs and f.attrs["pandas_type"] == "dataframe":
                    columns = f.attrs["columns"]
                    dtypes = f.attrs.get("dtypes", None)
                    data = {col: f[col][:] for col in columns}
                    for col in columns:
                        if data[col].dtype.kind == "S" or data[col].dtype == object:
                            data[col] = [
                                x.decode(self.string_dtype)
                                if isinstance(x, bytes)
                                else x
                                for x in data[col]
                            ]
                    df = pd.DataFrame(data)
                    if dtypes is not None:
                        for col, dtype in zip(columns, dtypes):
                            if len(df[col]) > 0:
                                df[col] = df[col].astype(dtype)
                            else:
                                df[col] = df[col].astype(dtype, copy=False)
                    return df
                # Handle empty dict
                elif "is_empty_dict" in f.attrs and f.attrs["is_empty_dict"]:
                    return {}
                # Handle empty list
                elif "_empty_list" in f.attrs and f.attrs["_empty_list"]:
                    return []
                # Handle empty tuple
                elif (
                    "_tuple" in f.attrs
                    and "_empty_tuple" in f.attrs
                    and f.attrs["_empty_tuple"]
                ):
                    return tuple()
                # Handle tuple
                elif "_tuple" in f.attrs:
                    items = []
                    for k in sorted(f.keys(), key=lambda x: int(x)):
                        items.append(recursive_load(f[k]))
                    return tuple(items)
                # Handle object ndarray
                elif "_ndarray" in f.attrs:
                    items = []
                    for k in sorted(f.keys(), key=lambda x: int(x)):
                        items.append(recursive_load(f[k]))
                    return np.array(items, dtype=object)
                # Handle list (integer keys)
                elif all(k.isdigit() for k in f.keys()):
                    items = []
                    for k in sorted(f.keys(), key=lambda x: int(x)):
                        items.append(recursive_load(f[k]))
                    return items
                # Handle dict
                else:
                    return {k: recursive_load(f[k]) for k in f.keys()}
            # Handle datasets (scalars, arrays, etc.)
            elif isinstance(f, h5py.Dataset):
                dtype = f.attrs.get("_type", None)
                if dtype is not None:
                    dtype = dtype if isinstance(dtype, str) else dtype.decode("utf-8")
                v = f[()]
                # Restore type from _type attribute
                if dtype == "str":
                    return (
                        v.decode(self.string_dtype) if isinstance(v, bytes) else str(v)
                    )
                elif dtype == "int":
                    return int(v)
                elif dtype == "float":
                    return float(v)
                elif dtype == "bool":
                    return bool(v)
                elif dtype == "ndarray":
                    return v
                elif dtype == "posixpath":
                    return PosixPath(
                        v.decode(self.string_dtype) if isinstance(v, bytes) else v
                    )
                elif dtype == "none":
                    return None
                else:
                    return v
            # Fallback: return raw value
            else:
                return f[()]

        # Open file and start recursive load
        with h5py.File(filepath, "r") as file:
            return {k: recursive_load(file[k]) for k in file.keys()}
