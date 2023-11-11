from datetime import datetime, timedelta
import os
import unittest
from unittest.mock import PropertyMock, patch
from lcls_tools.common.devices.screen.reader import create_screen
import h5py
import numpy as np


class TestScreen(unittest.TestCase):
    def setUp(self) -> None:
        self.screen_collection = create_screen("BC1")
        self.screen = self.screen_collection.screens["OTR11"]
        return super().setUp()

    @patch(
        "lcls_tools.common.devices.screen.screen.Screen.image",
        new_callable=PropertyMock,
    )
    @patch(
        "lcls_tools.common.devices.screen.screen.Screen.image_timestamp",
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
        self.screen.save_images(num_to_capture=num_capture)
        self.assertTrue(
            os.path.exists(self.screen.last_save_filepath),
            msg=f"expected file to exist: {self.screen._last_save_filepath}",
        )
        # Open the file we have saved and check the contents
        with h5py.File(self.screen.last_save_filepath, "r") as f:
            # check we have the correct number of datasets
            dataset_keys = list(f.keys())
            self.assertEqual(len(dataset_keys), num_capture)
            # check metadata is stored as attributes in HDF5.
            for dataset in f:
                self.assertSequenceEqual(
                    list(f[dataset].attrs.keys()),
                    list(self.screen.metadata.model_dump().keys()),
                )
