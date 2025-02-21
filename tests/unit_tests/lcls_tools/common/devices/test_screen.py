from datetime import datetime, timedelta
import os
import time
import unittest
from unittest.mock import PropertyMock, patch
from lcls_tools.common.devices.reader import create_screen
import h5py
import numpy as np


class TestScreen(unittest.TestCase):
    def setUp(self) -> None:
        self.screen_collection = create_screen("BC1")
        self.screen = self.screen_collection.screens["OTR11"]
        return super().setUp()

    @patch(
        "lcls_tools.common.devices.screen.Screen.image",
        new_callable=PropertyMock,
    )
    @patch(
        "lcls_tools.common.devices.screen.Screen.image_timestamp",
        new_callable=PropertyMock,
    )
    def test_hdf5_saving(self, mock_timestamp, mock_image):
        num_capture = 100
        mock_image.return_value = np.zeros(shape=(2000, 2000))
        t0 = datetime.now()
        # return an incrementing timestamp each time .image_timestamp is accessed.
        mock_timestamp.side_effect = [
            t0 + timedelta(seconds=i) for i in range(0, num_capture * 10)
        ]
        for is_threaded in [True, False]:
            self.screen.save_images(num_to_capture=num_capture, threaded=is_threaded)
            while self.screen.is_saving_images:
                time.sleep(1)
            self.assertTrue(
                os.path.exists(self.screen.last_save_filepath),
                msg=f"expected file to exist: {self.screen._last_save_filepath}",
            )
            # Open the file we have saved and check the contents
            with h5py.File(self.screen.last_save_filepath, "r") as f:
                # check we have the correct number of images
                self.assertEqual(len(f), num_capture)
                # check metadata is stored as attributes in HDF5.
                for dataset in f:
                    self.assertSetEqual(
                        set(f[dataset].attrs.keys()),
                        set(self.screen.metadata.model_dump().keys()),
                    )
                    # check dataset content for shape
                    self.assertTrue(
                        np.array_equal(np.zeros(shape=(2000, 2000)), f[dataset])
                    )

    @patch(
        "lcls_tools.common.devices.screen.Screen.image",
        new_callable=PropertyMock,
    )
    @patch(
        "lcls_tools.common.devices.screen.Screen.image_timestamp",
        new_callable=PropertyMock,
    )
    def test_hdf5_with_user_metadata(self, mock_timestamp, mock_image):
        num_capture = 100
        mock_image.return_value = np.zeros(shape=(2000, 2000))
        t0 = datetime.now()
        # return an incrementing timestamp each time .image_timestamp is accessed.
        mock_timestamp.side_effect = [
            t0 + timedelta(seconds=i) for i in range(0, num_capture * 10)
        ]
        user_metadata_for_scan = {
            "Comments": "Emittance Scan for HTR.",
            "QUAD1_BACT": 0.23,
            "QUAD_1_UNITS": "kG",
            "timestamp": str(datetime.now()),
        }
        for is_threaded in [True, False]:
            self.screen.save_images(
                num_to_capture=num_capture,
                threaded=is_threaded,
                extra_metadata=user_metadata_for_scan,
            )
            while self.screen.is_saving_images:
                time.sleep(1)
            self.assertTrue(
                os.path.exists(self.screen.last_save_filepath),
                msg=f"expected file to exist: {self.screen._last_save_filepath}",
            )
            # Open the file we have saved and check the contents
            with h5py.File(self.screen.last_save_filepath, "r") as f:
                # check we have the correct number of images
                self.assertEqual(len(f), num_capture)
                user_metadata_for_scan.update(**self.screen.metadata.model_dump())
                # check metadata is stored as attributes in HDF5.
                for dataset in f:
                    self.assertSequenceEqual(
                        sorted(list(f[dataset].attrs.keys())),
                        sorted(list(user_metadata_for_scan.keys())),
                    )
                    # check dataset content for shape
                    self.assertTrue(
                        np.array_equal(np.zeros(shape=(2000, 2000)), f[dataset])
                    )
