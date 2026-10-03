import unittest
import numpy as np
from lcls_tools.common.image.roi import ROI, CircularROI


class TestROI(unittest.TestCase):
    data_location: str = "tests/datasets/images/numpy/"

    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        self.center = [400, 400]
        self.size = (800, 800)
        self.extent = [300, 300]
        self.radius = 50

        self.image = np.load(self.data_location + "test_roi_image.npy")
        self.filled_value_test_image = np.load(
            self.data_location + "test_roi_fill_value_image.npy"
        )

    def test_circular_roi_crop_image(self):
        """
        Given a circular ROI and image,
        test that image has correct size after cropping
        (size of roi)
        """
        circular = CircularROI(center=self.center, radius=self.radius)
        cropped_image = circular.crop_image(self.image)
        assert cropped_image.shape[0] == 2 * self.radius
        assert cropped_image.shape[1] == 2 * self.radius

    def test_fill_value_outside_circle(self):
        """
        Given a test image change the pixel values
        of all elements of the image outside a radius of 10 to zero
        Test that this image is now exactly equal to the test filled value image
        """
        circular = CircularROI(center=self.center, radius=self.radius)
        image = circular.negative_fill(self.image, fill_value=0)
        assert image.all() == self.filled_value_test_image.all()

    def test_crop_keeps_the_circle_wherever_the_roi_sits(self):
        """
        The crop is the ROI bounding box, so the kept area should be the circle
        itself and must not depend on where the ROI sits in the full image.
        """
        image = np.ones(self.size)
        expected = np.pi * self.radius**2
        for center in ([400, 400], [100, 100], [self.radius, self.radius]):
            circular = CircularROI(center=center, radius=self.radius)
            cropped = circular.crop_image(image.copy())
            kept = np.count_nonzero(cropped)
            assert abs(kept - expected) / expected < 0.01, (
                f"center={center} kept {kept} pixels, expected about {expected:.0f}"
            )

    def test_rectangular_roi_crop_image(self):
        """
        Given a rectangular ROI and image,
        test that image has correct size after cropping
        (size of roi)
        """
        rectangular = ROI(center=self.center, extent=self.extent)
        cropped_image = rectangular.crop_image(self.image)
        assert list(cropped_image.shape) == self.extent
