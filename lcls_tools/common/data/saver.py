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
        Save a dictionary to an HDF5 file.

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
        h5str = h5py.string_dtype(encoding=self.string_dtype)

        def recursive_save(d, f):
            for key, val in d.items():
                if key == "attrs":
                    f.attrs.update(val or h5py.Empty("f4"))
                elif isinstance(val, dict):
                    group = f.create_group(key, track_order=True)
                    recursive_save(val, group)
                elif isinstance(val, list):
                    types = [type(ele).__name__ for ele in val]
                    if all(isinstance(ele, list) for ele in val):
                        group = f.create_group(key, track_order=True)
                        for i, sublist in enumerate(val):
                            # Save each sublist as a dataset (handle homogeneous/heterogeneous as before)
                            sub_types = [type(x).__name__ for x in sublist]
                            if len(set(sub_types)) == 1 and all(
                                    isinstance(x, (str, int, float, bool)) for x in sublist):
                                dset = group.create_dataset(str(i), data=sublist,
                                                            dtype=h5py.string_dtype(encoding=self.string_dtype) if
                                                            sub_types[0] == "str" else None, track_order=True)
                                dset.attrs["_type"] = sub_types[0]
                            else:
                                dset = group.create_dataset(str(i), data=[str(x) for x in sublist],
                                                            dtype=h5py.string_dtype(encoding=self.string_dtype),
                                                            track_order=True)
                                dset.attrs["_types"] = np.array(sub_types,
                                                                dtype=h5py.string_dtype(encoding=self.string_dtype))
                    elif len(set(types)) == 1 and all(isinstance(ele, (str, int, float, bool)) for ele in val):
                        dset = f.create_dataset(key, data=val,
                                                dtype=h5py.string_dtype(encoding=self.string_dtype) if types[
                                                                                                           0] == "str" else None,
                                                track_order=True)
                        dset.attrs["_type"] = types[0]
                    elif all(isinstance(ele, np.ndarray) for ele in val):
                        # save np.arrays as datasets
                        for i, ele in enumerate(val):
                            f.create_dataset(f"{key}/{i}", data=ele, track_order=True)
                            if ele.dtype == np.dtype("O"):
                                f.create_dataset(
                                    f"{key}/{i}",
                                    data=str(ele),
                                    dtype=h5str,
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
                                    dtype=h5str,
                                    track_order=True,
                                )
                    else:
                        # Mixed types: save as strings and store types
                        dset = f.create_dataset(key, data=[str(ele) for ele in val], dtype=h5str, track_order=True)
                        dset.attrs["_types"] = np.array(types, dtype=h5str)
                elif isinstance(val, self.supported_types):
                    f.create_dataset(key, data=val, track_order=True)
                elif isinstance(val, np.ndarray):
                    if val.dtype != np.dtype("O"):
                        f.create_dataset(key, data=val, track_order=True)
                    else:
                        f.create_dataset(key, data=str(val), dtype=h5str, track_order=True)
                elif isinstance(val, tuple):
                    val_array = np.array(val)
                    f.create_dataset(key, data=val_array, track_order=True)
                elif isinstance(val, str):
                    # specify string dtype to avoid issues with encodings
                    f.create_dataset(key, data=val, dtype=h5str, track_order=True)
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
                    f.create_dataset(key, data=str(val), dtype=h5str, track_order=True)

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
            keys = list(f.keys())
            if keys and all(k.isdigit() for k in keys):
                items = []
                for k in sorted(keys, key=int):
                    val = f[k]
                    if isinstance(val, h5py.Group):
                        items.append(recursive_load(val))
                    elif isinstance(val, h5py.Dataset):
                        if "_type" in val.attrs:
                            dtype = val.attrs["_type"]
                            arr = val[()]
                            if dtype == "str":
                                items.append(
                                    [x.decode(self.string_dtype) if isinstance(x, bytes) else str(x) for x in arr])
                            elif dtype == "int":
                                items.append([int(x) for x in arr])
                            elif dtype == "float":
                                items.append([float(x) for x in arr])
                            elif dtype == "bool":
                                items.append([bool(x) for x in arr])
                            else:
                                items.append(arr.tolist())
                        elif "_types" in val.attrs:
                            arr = val[()]
                            types = val.attrs["_types"]
                            if isinstance(types, bytes):
                                types = [types.decode(self.string_dtype)]
                            else:
                                types = [t.decode(self.string_dtype) if isinstance(t, bytes) else t for t in types]
                            result = []
                            for x, t in zip(arr, types):
                                if t == "int":
                                    result.append(int(x))
                                elif t == "float":
                                    result.append(float(x))
                                elif t == "bool":
                                    result.append(x == b"True" if isinstance(x, bytes) else x == "True")
                                elif t == "list":
                                    # Try to parse stringified list
                                    s = x.decode(self.string_dtype) if isinstance(x, bytes) else str(x)
                                    try:
                                        result.append(ast.literal_eval(s))
                                    except Exception:
                                        result.append(s)
                                else:
                                    result.append(x.decode(self.string_dtype) if isinstance(x, bytes) else str(x))
                            d[key] = result
                        else:
                            v = val[()]
                            if isinstance(v, bytes):
                                v = v.decode(self.string_dtype)
                            # Try to parse stringified list
                            try:
                                parsed = ast.literal_eval(v)
                                if isinstance(parsed, list):
                                    items.append(parsed)
                                else:
                                    items.append(v)
                            except Exception:
                                items.append(v)
                return items
            for key, val in f.items():
                if isinstance(val, h5py.Group):
                    if "pandas_type" in val.attrs and val.attrs["pandas_type"] == "dataframe":
                        columns = val.attrs["columns"]
                        data = {}
                        for col in columns:
                            data[col] = val[col][:]
                        d[key] = pd.DataFrame(data)
                    else:
                        d[key] = recursive_load(val)
                elif isinstance(val, h5py.Dataset):
                    if "_type" in val.attrs:
                        dtype = val.attrs["_type"]
                        arr = val[()]
                        if dtype == "str":
                            d[key] = [x.decode(self.string_dtype) if isinstance(x, bytes) else str(x) for x in arr]
                        elif dtype == "int":
                            d[key] = [int(x) for x in arr]
                        elif dtype == "float":
                            d[key] = [float(x) for x in arr]
                        elif dtype == "bool":
                            d[key] = [bool(x) for x in arr]
                        else:
                            d[key] = arr.tolist()
                    elif "_types" in val.attrs:
                        arr = val[()]
                        types = val.attrs["_types"]
                        if isinstance(types, bytes):
                            types = [types.decode(self.string_dtype)]
                        else:
                            types = [t.decode(self.string_dtype) if isinstance(t, bytes) else t for t in types]
                        result = []
                        for x, t in zip(arr, types):
                            if t == "int":
                                result.append(int(x))
                            elif t == "float":
                                result.append(float(x))
                            elif t == "bool":
                                result.append(x == b"True" if isinstance(x, bytes) else x == "True")
                            else:
                                result.append(x.decode(self.string_dtype) if isinstance(x, bytes) else str(x))
                        d[key] = result
                    else:
                        d[key] = val[()].decode(self.string_dtype) if isinstance(val[()], bytes) else val[()]
            return d

        with h5py.File(filepath, "r") as file:
            return recursive_load(file)
