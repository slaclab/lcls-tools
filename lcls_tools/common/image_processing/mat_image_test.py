import sys
import unittest
import numpy as np
from mat_image import MatImage as MI

FILE = 'test_image.mat'
CAMERA = 'CAMR:LGUN:210'

class MatImageTest(unittest.TestCase):
    
    def test_initial_properties(self):
        mi = MI()
        self.assertEqual(mi.mat_file, None)
        self.assertEqual(mi.camera_name, None)
        self.assertEqual(mi.image, None)
        self.assertEqual(mi.image_as_list, [])
        self.assertEqual(mi.roi_x_n, None)
        self.assertEqual(mi.roi_y_n, None)
        self.assertEqual(mi.timestamp, None)
        self.assertEqual(mi.pulse_id, None)
        self.assertEqual(mi.columns, None)
        self.assertEqual(mi.rows, None)
        self.assertEqual(mi.bit_depth, None)
        self.assertEqual(mi.resolution, None)
        self.assertEqual(mi.roi_x, None)
        self.assertEqual(mi.roi_y, None)
        self.assertEqual(mi.orientation_x, None)
        self.assertEqual(mi.orientation_y, None)
        self.assertEqual(mi.center_x, None)
        self.assertEqual(mi.center_y, None)
        self.assertEqual(mi.filt_stat, None)
        self.assertEqual(mi.filt_od, None)
        self.assertEqual(mi.image_attn, None)
        self.assertEqual(mi.is_raw, None)
        self.assertEqual(mi.back, None)
        
    def test_load_mat_image_exception(self):
        mi = MI()
        self.assertRaises(Exception, mi.load_mat_image('junk'))

    def test_load_mat_image(self):
        mi = MI()
        mi.load_mat_image(FILE)
        self.assertEqual(mi.mat_file, FILE)
        self.assertEqual(mi.camera_name, CAMERA)
        self.assertEqual(isinstance(mi.image, np.ndarray), True)
        self.assertEqual(isinstance(mi.image_as_list, list), True)
        self.assertEqual(mi.roi_x_n, 1392)
        self.assertEqual(mi.roi_y_n, 1024)
        self.assertEqual(round(mi.timestamp, 1), 737450.7)
        self.assertEqual(mi.pulse_id, 33164)
        self.assertEqual(mi.columns, 1392)
        self.assertEqual(mi.rows, 1040)
        self.assertEqual(mi.bit_depth, 12)
        self.assertEqual(round(mi.resolution, 2), 4.65)
        self.assertEqual(mi.roi_x, 0)
        self.assertEqual(mi.roi_y, 0)
        self.assertEqual(mi.orientation_x, 0)
        self.assertEqual(mi.orientation_y, 0)
        self.assertEqual(mi.center_x, 696)
        self.assertEqual(mi.center_y, 520)
        np.testing.assert_array_equal(mi.filt_stat, [0, 0])
        np.testing.assert_array_equal(mi.filt_od, [0, 0])
        self.assertEqual(mi.image_attn, 1)
        self.assertEqual(mi.is_raw, 0)
        self.assertEqual(mi.back, 0)

    def test_show_image(self):
        mi = MI()
        mi.load_mat_image(FILE)
        mi.show_image()

    def test_show_image_no_file(self):
        mi = MI()
        mi.show_image()

if __name__ == '__main__':
    unittest.main()
