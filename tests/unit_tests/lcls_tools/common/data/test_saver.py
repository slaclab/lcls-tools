import os
import tempfile
import unittest
import numpy as np
import pandas as pd

from lcls_tools.common.data.saver import H5Saver
from lcls_tools.common.measurements.screen_profile import (
    ScreenBeamProfileMeasurementResult,
)
from lcls_tools.common.image.processing import ImageProcessor
from lcls_tools.common.image.fit import ImageProjectionFit


class TestH5Saver(unittest.TestCase):
    def setUp(self):
        self.saver = H5Saver()
        self.tempfile = tempfile.NamedTemporaryFile(suffix=".h5", delete=False)
        self.fname = self.tempfile.name
        self.tempfile.close()

    def tearDown(self):
        if os.path.exists(self.fname):
            os.remove(self.fname)

    def roundtrip(self, data):
        self.saver.dump(data, self.fname)
        return self.saver.load(self.fname)

    def test_dict(self):
        data = {"a": 1, "b": 2.5, "c": "test"}
        loaded = self.roundtrip(data)
        self.assertEqual(loaded, data)

    def test_empty_dict(self):
        data = {}
        loaded = self.roundtrip(data)
        self.assertEqual(loaded, data)

    def test_list(self):
        data = {"lst": [1, 2, 3, 4]}
        loaded = self.roundtrip(data)
        self.assertEqual(loaded["lst"], data["lst"])

    def test_empty_list(self):
        data = {"lst": []}
        loaded = self.roundtrip(data)
        self.assertEqual(loaded["lst"], [])

    def test_list_of_ndarrays(self):
        data = {"list_of_ndarrays": [np.array([1, 2, 3]), np.array([4, 5, 6])]}
        loaded = self.roundtrip(data)
        assert len(data["list_of_ndarrays"]) == len(loaded["list_of_ndarrays"])

    def test_typed_dataframe(self):
        df = pd.DataFrame(
            {
                "int": pd.Series([1, 2, 3], dtype="int32"),
                "float": pd.Series([1.1, 2.2, 3.3], dtype="float32"),
                "float_w_nan": pd.Series([1.1, 2.2, np.nan], dtype="float32"),
                "double": pd.Series([1.1, 2.2, 3.3], dtype="float64"),
                "double_w_nan": pd.Series([1.1, 2.2, np.nan], dtype="float64"),
                "object_array": np.array([1, np.nan, 3.5], dtype=object),
                "str": pd.Series(["a", "b", "c"], dtype="str"),
                "bool": pd.Series([True, False, True], dtype="boolean"),
            }
        )

        loaded = self.roundtrip({"df": df})["df"]
        pd.testing.assert_frame_equal(loaded, df)

        # this should cast everything to a string
        df_mixed = pd.DataFrame(
            {
                "mixed": pd.Series([1.0, "two", np.nan], dtype=object),
            }
        )
        loaded_mixed = self.roundtrip({"df": df_mixed})["df"]
        pd.testing.assert_frame_equal(loaded_mixed, df_mixed.astype(str))

    def test_tuple(self):
        data = {"tup": (1, "2", (None, 3.5))}
        loaded = self.roundtrip(data)
        self.assertEqual(loaded["tup"], data["tup"])

    def test_empty_tuple(self):
        data = {"tup": ()}
        loaded = self.roundtrip(data)
        self.assertEqual(tuple(loaded["tup"]), ())

    def test_int(self):
        data = {"i": 42}
        loaded = self.roundtrip(data)
        self.assertEqual(loaded["i"], 42)

    def test_float(self):
        data = {"f": 3.14159}
        loaded = self.roundtrip(data)
        self.assertAlmostEqual(loaded["f"], 3.14159)

    def test_special_values(self):
        data = {
            "nan": np.nan,
            "inf": np.inf,
            "ninf": -np.inf,
            "nan_list": [np.nan, np.inf, -np.inf],
        }
        loaded = self.roundtrip(data)

        assert np.isnan(loaded["nan"])
        assert np.isinf(loaded["inf"])
        assert np.isneginf(loaded["ninf"])
        assert np.isnan(loaded["nan_list"][0])
        assert np.isinf(loaded["nan_list"][1])
        assert np.isneginf(loaded["nan_list"][2])

    def test_bool(self):
        data = {"b": True}
        loaded = self.roundtrip(data)
        self.assertIs(loaded["b"], True)

    def test_str(self):
        data = {"s": "hello world"}
        loaded = self.roundtrip(data)
        self.assertEqual(loaded["s"], "hello world")

    def test_none(self):
        data = {"n": None}
        loaded = self.roundtrip(data)
        self.assertIsNone(loaded["n"])

    def test_numpy_array(self):
        arr = np.arange(5)
        data = {"arr": arr}
        loaded = self.roundtrip(data)
        np.testing.assert_array_equal(loaded["arr"], arr)

    def test_empty_numpy_array(self):
        arr = np.array([])
        data = {"arr": arr}
        loaded = self.roundtrip(data)
        np.testing.assert_array_equal(loaded["arr"], arr)

    def test_large_numpy_array(self):
        arr = np.arange(10000)
        data = {"arr": arr}
        loaded = self.roundtrip(data)
        np.testing.assert_array_equal(loaded["arr"], arr)

    def test_numpy_object_array(self):
        arr = np.array([1, "a", 3.5], dtype=object)
        data = {"objarr": arr}
        self.assertRaises(RuntimeError, self.roundtrip, data)

    def test_nested_structures(self):
        data = {
            "nested_dict": {"level1": {"level2": {"level3": "value"}}},
            "nested_list": [[1, 2, 3], [4, 5, 6]],
        }
        loaded = self.roundtrip(data)
        assert data["nested_dict"] == loaded["nested_dict"]

    def test_nested_structures_not_implemented(self):
        data = {"d": {"l": [1, 2, {"x": 5}], "t": (3, 4, [5, 6])}}
        self.assertRaises(RuntimeError, self.roundtrip, data)

    def test_nested_empty_structures(self):
        data = {"d": {"l": [], "t": (), "d2": {}}}
        loaded = self.roundtrip(data)
        self.assertEqual(loaded["d"]["l"], [])
        self.assertEqual(tuple(loaded["d"]["t"]), ())
        self.assertEqual(loaded["d"]["d2"], {})

    def test_mixed_types(self):
        data = {
            "a": 1,
            "b": [1, "two", 3.0, None],
            "c": {"x": True, "y": [1.1, 2.2]},
            "d": (None, "str", 5),
        }
        loaded = self.roundtrip(data)
        self.assertEqual(loaded["a"], 1)
        self.assertEqual(loaded["b"][0], 1)
        self.assertEqual(loaded["b"][1], "two")
        self.assertEqual(loaded["b"][2], 3.0)
        self.assertIsNone(loaded["b"][3])
        self.assertEqual(loaded["c"]["x"], True)
        self.assertEqual(loaded["c"]["y"], [1.1, 2.2])
        self.assertEqual(tuple(loaded["d"]), (None, "str", 5))

    def test_dataframe(self):
        df = pd.DataFrame(
            {
                "int": [1, 2],
                "float": [1.1, 2.2],
                "str": ["a", "b"],
                "bool": [True, False],
                "array": [np.array([1, 2]), np.array([3, 4])],
            }
        )
        data = {"df": df}
        loaded = self.roundtrip(data)
        pd.testing.assert_frame_equal(loaded["df"], df)

    def test_empty_dataframe(self):
        df = pd.DataFrame(columns=["a", "b"])
        data = {"df": df}
        loaded = self.roundtrip(data)
        pd.testing.assert_frame_equal(loaded["df"], df)

    def test_tuple_of_dicts(self):
        data = {"tuple_dicts": ({"a": 1}, {"b": 2.2}, {"c": "three"})}
        self.assertRaises(RuntimeError, self.roundtrip, data)

    def test_numpy_array_of_dicts(self):
        arr = np.array([{"x": 1}, {"y": 2}], dtype=object)
        data = {"arr_dicts": arr}
        self.assertRaises(RuntimeError, self.roundtrip, data)

    def test_posix_path(self):
        from pathlib import PosixPath

        data = {"path": PosixPath("/tmp/testfile.txt")}
        loaded = self.roundtrip(data)
        self.assertIsInstance(loaded["path"], PosixPath)
        self.assertEqual(loaded["path"], PosixPath("/tmp/testfile.txt"))

    def test_screen_measurement_results(self):
        # Load test data
        images = np.load("tests/datasets/images/numpy/test_images.npy")

        # Process data
        image_processor = ImageProcessor()

        processed_images = [image_processor.auto_process(image) for image in images]

        rms_sizes_all = []
        centroids_all = []
        total_intensities_all = []
        for image in processed_images:
            fit_result = ImageProjectionFit().fit_image(image)
            rms_sizes_all.append(
                np.array(fit_result.rms_size) * 1.0  # fake resolution of 1.0
            )
            centroids_all.append(np.array(fit_result.centroid) * 1.0)
            total_intensities_all.append(fit_result.total_intensity)
        rms_sizes = np.mean(rms_sizes_all, axis=0)
        centroids = np.mean(centroids_all, axis=0)
        total_intensities = np.mean(total_intensities_all, axis=0)

        # Store results in ScreenBeamProfileMeasurementResult
        result = ScreenBeamProfileMeasurementResult(
            raw_images=images,
            processed_images=processed_images,
            rms_sizes_all=rms_sizes_all,
            rms_sizes=rms_sizes if rms_sizes.size > 0 else None,
            centroids=centroids if centroids.size > 0 else None,
            total_intensities=total_intensities if total_intensities.size > 0 else None,
            metadata={"info": "test"},
        )

        # Dump to H5
        result_dict = result.model_dump()
        loaded_dict = self.roundtrip(result_dict)

        # Check if the loaded dictionary is the same as the original
        assert result_dict.keys() == loaded_dict.keys()
        assert result_dict["metadata"] == loaded_dict["metadata"]
        assert isinstance(loaded_dict["raw_images"], np.ndarray)
        assert np.allclose(images, loaded_dict["raw_images"], rtol=1e-5)

        mask = ~np.isnan(rms_sizes_all)
        assert np.allclose(
            np.asarray(rms_sizes_all)[mask],
            loaded_dict["rms_sizes_all"][mask],
            rtol=1e-5,
        )
        mask = ~np.isnan(centroids)
        assert np.allclose(
            np.asarray(centroids)[mask], loaded_dict["centroids"][mask], rtol=1e-5
        )
        assert np.allclose(
            total_intensities, loaded_dict["total_intensities"], rtol=1e-5
        )


if __name__ == "__main__":
    unittest.main()
