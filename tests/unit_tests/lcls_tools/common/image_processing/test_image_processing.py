import unittest
import os
import numpy as np
import lcls_tools.common.image_processing as ip
from lcls_tools.common.matlab2py.mat_image import MatImage

CAMERA = "CAMR:LGUN:210"


class ImageProcessingTest(unittest.TestCase):
    data_location: str = "/tests/datasets/images/matlab/"

    def setUp(self):
        self.file = os.path.join(self.data_location, "test_image.mat")
        try:
            if not os.path.isfile(self.file):
                raise FileNotFoundError(f"Could not find {self.file}, aborting test.")
        except FileNotFoundError:
            self.skipTest("Invalid dataset location")
        """Use test image"""
        self.MI = MatImage()
        self.MI.load_mat_image("test_image.mat")

    def test_fliplr(self):
        """Test that fliplr does the right thing"""
        col_init = self.MI.image[:, 0]
        col_final = ip.fliplr(self.MI.image)[:, -1]
        self.assertEqual(np.array_equal(col_init, col_final), True)

    def test_flipud(self):
        """Test that flipud does the right thing"""
        row_init = self.MI.image[0]
        row_final = ip.flipud(self.MI.image)[-1]
        self.assertEqual(np.array_equal(row_init, row_final), True)

    def test_center_of_mass(self):
        """Test that we get correct x and y centroids"""
        (x1, y1) = ip.center_of_mass(self.MI.image)
        self.assertEqual((int(x1), int(y1)), (522, 669))
        (x2, y2) = ip.center_of_mass(self.MI.image, sigma=2)
        self.assertEqual((int(x2), int(y2)), (540, 660))

    def test_average_image(self):
        """Test that we can average a number of images"""
        images = []
        while len(images) < 10:
            images.append(self.MI.image)

        ave_image = ip.average_image(images)
        self.assertEqual(np.array_equal(ave_image, self.MI.image), True)

    def test_shape_image(self):
        """Test that we can reshape our ndarray"""
        self.assertEqual(self.MI.image.shape, (1024, 1392))
        image = ip.shape_image(self.MI.image, 16, 89088)
        self.assertEqual(image.shape, (89088, 16))

    def test_x_projection(self):
        """Test we get expected value for x projection"""
        x_proj = ip.x_projection(self.MI.image)
        self.assertEqual(x_proj.sum(), 9792279)
        self.assertEqual(int(x_proj.mean()), 7034)
        self.assertEqual(int(x_proj.std()), 10005)

    def test_y_projection(self):
        """Test that we get expected value for y projection"""
        y_proj = ip.y_projection(self.MI.image)
        self.assertEqual(y_proj.sum(), 9623943)
        self.assertEqual(int(y_proj.mean()), 9398)
        self.assertEqual(int(y_proj.std()), 10398)

    def test_gauss_func(self):
        """Test we get correct value for a gaussian evaluation"""
        ans = ip.gauss_func(1.0, 2.0, 3.0, 4.0)
        self.assertEqual(round(ans, 2), 1.76)

    def test_gauss_fit(self):
        """Test that we get the correct gaussian fit parameters"""
        x_proj = ip.x_projection(self.MI.image)
        y_proj = ip.y_projection(self.MI.image)
        _, a_x, x0_x, sigma_x = ip.gauss_fit(x_proj)
        _, a_y, y0_y, sigma_y = ip.gauss_fit(y_proj)
        self.assertEqual(int(a_x), 30373)
        self.assertEqual(int(x0_x), 660)
        self.assertEqual(int(sigma_x), 124)
        self.assertEqual(int(a_y), 29528)
        self.assertEqual(int(y0_y), 541)
        self.assertEqual(int(sigma_y), 127)
