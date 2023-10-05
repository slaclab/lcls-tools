import os
import unittest
import numpy as np
from lcls_tools.common.image_processing.image import Image

FILE = "test_image.npy"


class ImageTest(unittest.TestCase):
    data_location : str = "/tests/datasets/images/numpy/"
    def setUp(self):
        self.file = os.path.join(self.data_location, 'test_image.npy')
        try:
            if not os.path.isfile(self.file):
                raise FileNotFoundError(f"Could not find {self.file}, aborting test.")
        except FileNotFoundError:
            self.skipTest("Invalid dataset location")
        self.image_obj = Image(np.load(FILE))

    def test_image(self):
        """Make sure image array not altered after initialization"""
        test_img = np.load("test_image.npy")
        obj_img = self.image_obj.image
        self.assertEqual(np.array_equal(test_img, obj_img), True)

    def test_std(self):
        """Test std"""
        self.assertEqual(round(self.image_obj.std, 1), 16.9)

    def test_mean(self):
        """Test mean"""
        self.assertEqual(round(self.image_obj.mean, 1), 38.9)

    def test_n_col(self):
        """Test n_col"""
        self.assertEqual(self.image_obj.n_col, 1024)

    def test_n_row(self):
        """Test n_row"""
        self.assertEqual(self.image_obj.n_row, 1392)

    def test_shape(self):
        """Test shape"""
        self.assertEqual(self.image_obj.shape, (1024, 1392))

    def test_min(self):
        """Test min"""
        self.assertEqual(self.image_obj.min, 23)

    def test_max(self):
        """Test max"""
        self.assertEqual(self.image_obj.max, 200)

