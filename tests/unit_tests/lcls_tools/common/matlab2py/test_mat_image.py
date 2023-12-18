import unittest
import numpy as np
import os
from lcls_tools.common.matlab2py.mat_image import MatImage as MI


class MatImageTest(unittest.TestCase):
    dataset_location = "tests/datasets/images/matlab/"

    def setUp(self) -> None:
        try:
            if not os.path.isdir(self.dataset_location):
                raise FileNotFoundError(
                    f"Could not find dataset files in {self.dataset_location}"
                )
        except FileNotFoundError:
            self.skipTest("Invalid dataset location")
        self.mi = MI()
        self.camera = "CAMR:LGUN:210"
        self.test_file_name = "ProfMon-CAMR_LGUN_210-2019-03-15-151532.mat"
        self.file = os.path.join(self.dataset_location, self.test_file_name)
        return super().setUp()

    def test_initial_properties(self):
        self.assertIsNone(self.mi.mat_file)
        self.assertIsNone(self.mi.camera_name)
        self.assertIsNone(self.mi.image)
        self.assertIsInstance(self.mi.image_as_list, list)
        self.assertIsNone(self.mi.roi_x_n)
        self.assertIsNone(self.mi.roi_y_n)
        self.assertIsNone(self.mi.timestamp)
        self.assertIsNone(self.mi.pulse_id)
        self.assertIsNone(self.mi.columns)
        self.assertIsNone(self.mi.rows)
        self.assertIsNone(self.mi.bit_depth, None)
        self.assertIsNone(self.mi.resolution, None)
        self.assertIsNone(self.mi.roi_x, None)
        self.assertIsNone(self.mi.roi_y, None)
        self.assertIsNone(self.mi.orientation_x, None)
        self.assertIsNone(self.mi.orientation_y, None)
        self.assertIsNone(self.mi.center_x, None)
        self.assertIsNone(self.mi.center_y, None)
        self.assertIsNone(self.mi.filt_stat, None)
        self.assertIsNone(self.mi.filt_od, None)
        self.assertIsNone(self.mi.image_attn, None)
        self.assertIsNone(self.mi.is_raw, None)
        self.assertIsNone(self.mi.back, None)

    def test_load_mat_image_exception(self):
        junk_datafile = os.path.join(self.dataset_location, "junk.mat")
        with self.assertRaises(Exception):
            self.mi._unpack_mat_data(junk_datafile)

    def test_load_mat_image(self):
        self.mi.load_mat_image(self.file)
        self.assertEqual(self.mi.mat_file, self.file)
        self.assertEqual(self.mi.camera_name, self.camera)
        self.assertEqual(isinstance(self.mi.image, np.ndarray), True)
        self.assertIsInstance(self.mi.image_as_list, list)
        self.assertEqual(self.mi.roi_x_n, 1392)
        self.assertEqual(self.mi.roi_y_n, 1024)
        self.assertEqual(round(self.mi.timestamp, 1), 737499.6)
        self.assertEqual(self.mi.pulse_id, 66868)
        self.assertEqual(self.mi.columns, 1392)
        self.assertEqual(self.mi.rows, 1040)
        self.assertEqual(self.mi.bit_depth, 12)
        self.assertEqual(round(self.mi.resolution, 2), 4.65)
        self.assertEqual(self.mi.roi_x, 0)
        self.assertEqual(self.mi.roi_y, 0)
        self.assertEqual(self.mi.orientation_x, 0)
        self.assertEqual(self.mi.orientation_y, 0)
        self.assertEqual(self.mi.center_x, 696)
        self.assertEqual(self.mi.center_y, 520)
        np.testing.assert_array_equal(self.mi.filt_stat, [0, 0])
        np.testing.assert_array_equal(self.mi.filt_od, [0, 0])
        self.assertEqual(self.mi.image_attn, 1)
        self.assertEqual(self.mi.is_raw, 0)
        self.assertEqual(self.mi.back, 0)

    def test_show_image(self):
        # not asserting anything here, needs to have test
        self.mi.load_mat_image(self.file)
        self.mi.show_image()

    def test_show_image_no_file(self):
        # not assserting anything here either, needs to have test
        with self.assertRaises(AttributeError):
            self.mi.show_image()
