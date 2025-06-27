import os
import unittest

import numpy as np

from lcls_tools.common.measurements.screen_profile import (
    ScreenBeamProfileMeasurementResult,
)
from lcls_tools.common.image.processing import ImageProcessor
from lcls_tools.common.image.fit import ImageProjectionFit
from lcls_tools.common.data.saver import H5Saver


class TestSaver(unittest.TestCase):
    def test_nans(self):
        saver = H5Saver()
        data = {
            "a": np.nan,
            "b": np.inf,
            "c": -np.inf,
            "d": [np.nan, np.inf, -np.inf],
            "e": [np.nan, np.inf, -np.inf, 1.0],
            "f": [np.nan, np.inf, -np.inf, "a"],
            "g": {"a": np.nan, "b": np.inf, "c": -np.inf},
            "h": "np.Nan",
            "i": np.array((1.0, 2.0), dtype="O"),
        }
        saver.dump(data, "test.h5")
        os.remove("test.h5")

    def test_screen_measurement_results(self):
        # Load test data
        images = np.load("tests/datasets/images/numpy/test_images.npy")

        # Process data
        image_processor = ImageProcessor()

        processed_images = [image_processor.auto_process(image) for image in images]

        rms_sizes = []
        centroids = []
        total_intensities = []
        for image in processed_images:
            fit_result = ImageProjectionFit().fit_image(image)
            rms_sizes.append(fit_result.rms_size)
            centroids.append(fit_result.centroid)
            total_intensities.append(fit_result.total_intensity)

        # Store results in ScreenBeamProfileMeasurementResult
        result = ScreenBeamProfileMeasurementResult(
            raw_images=images,
            processed_images=processed_images,
            rms_sizes=rms_sizes or None,
            centroids=centroids or None,
            total_intensities=total_intensities or None,
            metadata={"info": "test"},
        )

        # Dump to H5
        result_dict = result.model_dump()
        saver = H5Saver()
        saver.dump(
            result_dict,
            os.path.join("screen_test.h5"),
        )

        # Load H5
        loaded_dict = saver.load("screen_test.h5")

        # Check if the loaded dictionary is the same as the original
        assert result_dict.keys() == loaded_dict.keys()
        assert result_dict["metadata"] == loaded_dict["metadata"]
        assert isinstance(loaded_dict["raw_images"], np.ndarray)
        assert np.allclose(images, loaded_dict["raw_images"], rtol=1e-5)

        mask = ~np.isnan(rms_sizes)
        assert np.allclose(
            np.asarray(rms_sizes)[mask], loaded_dict["rms_sizes"][mask], rtol=1e-5
        )
        mask = ~np.isnan(centroids)
        assert np.allclose(
            np.asarray(centroids)[mask], loaded_dict["centroids"][mask], rtol=1e-5
        )
        assert np.allclose(
            total_intensities, loaded_dict["total_intensities"], rtol=1e-5
        )

        os.remove("screen_test.h5")

    def test_basic_data_types(self):
        saver = H5Saver()
        data = {
            "int": 42,
            "float": 3.14,
            "bool": True,
            "string": "test",
            "list": [1, 2, 3],
            "tuple": (4, 5, 6),
            "dict": {"a": 1, "b": 2},
            "ndarray": np.array([7, 8, 9]),
        }
        saver.dump(data, "test_basic.h5")
        loaded_data = saver.load("test_basic.h5")
        os.remove("test_basic.h5")

        assert data["int"] == loaded_data["int"]
        assert data["float"] == loaded_data["float"]
        assert data["bool"] == loaded_data["bool"]
        assert data["string"] == loaded_data["string"]
        assert data["list"] == loaded_data["list"]
        assert (
            list(data["tuple"]) == loaded_data["tuple"].tolist()
        )  # tuple are saved as arrays
        assert data["dict"] == loaded_data["dict"]
        assert np.array_equal(data["ndarray"], loaded_data["ndarray"])

    def test_special_values(self):
        saver = H5Saver()
        data = {
            "nan": np.nan,
            "inf": np.inf,
            "ninf": -np.inf,
            "nan_list": [np.nan, np.inf, -np.inf],
        }
        saver.dump(data, "test_special.h5")
        loaded_data = saver.load("test_special.h5")
        os.remove("test_special.h5")

        assert np.isnan(loaded_data["nan"])
        assert np.isinf(loaded_data["inf"])
        assert np.isneginf(loaded_data["ninf"])
        assert np.isnan(loaded_data["nan_list"][0])
        assert np.isinf(loaded_data["nan_list"][1])
        assert np.isneginf(loaded_data["nan_list"][2])

    def test_nested_structures(self):
        saver = H5Saver()
        data = {
            "nested_dict": {"level1": {"level2": {"level3": "value"}}},
            "nested_list": [[1, 2, 3], [4, 5, 6]],
        }
        saver.dump(data, "test_nested.h5")
        loaded_data = saver.load("test_nested.h5")
        os.remove("test_nested.h5")

        assert data["nested_dict"] == loaded_data["nested_dict"]
        for i in range(len(data["nested_list"])):
            # lists of lists are saved as dicts
            # here the lists are saved as nd.arrays
            assert np.array_equal(
                data["nested_list"][i], loaded_data["nested_list"][i]
            )

    def test_object_arrays(self):
        saver = H5Saver()
        data = {"object_array": np.array([1, "a", 3.14], dtype=object)}
        saver.dump(data, "test_object_array.h5")
        loaded_data = saver.load("test_object_array.h5")
        os.remove("test_object_array.h5")

        assert all(isinstance(item, str) for item in loaded_data["object_array"])

    def test_list_of_ndarrays(self):
        saver = H5Saver()
        data = {"list_of_ndarrays": [np.array([1, 2, 3]), np.array([4, 5, 6])]}
        saver.dump(data, "test_list_of_ndarrays.h5")
        loaded_data = saver.load("test_list_of_ndarrays.h5")
        os.remove("test_list_of_ndarrays.h5")

        assert len(data["list_of_ndarrays"]) == len(loaded_data["list_of_ndarrays"])
        for original, loaded in zip(
            data["list_of_ndarrays"], loaded_data["list_of_ndarrays"]
        ):
            # lists of ndarrays are saved as dicts
            assert np.array_equal(original, loaded)
