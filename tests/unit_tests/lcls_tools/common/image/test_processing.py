import unittest
import numpy as np

from lcls_tools.common.image.processing import ImageProcessor
from lcls_tools.common.image.roi import ROI


class TestImageProcessing(unittest.TestCase):
    data_location: str = "tests/datasets/images/numpy/"

    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        self.center = [400, 400]
        self.size = (800, 800)
        self.extent = [350, 300]
        self.radius = 50
        self.image = np.load(self.data_location + "test_roi_image.npy")

    def test_process(self):
        """
        Given an np.ndarray and roi process
        and assert the return in an np.ndarray
        """
        image_processor = ImageProcessor()
        image = image_processor.auto_process(self.image)
        self.assertIsInstance(
            image, np.ndarray,
            msg="expected image to be an instance of np.ndarray"
        )
        roi = ROI(center=self.center, extent=self.extent)
        image_processor = ImageProcessor(roi=roi)
        image = image_processor.auto_process(self.image)
        self.assertIsInstance(
            image, np.ndarray,
            msg="expected image to be an instance of np.ndarray"
        )
        imageShape = image.shape
        roiShape = tuple(roi.extent)
        self.assertEqual(
            imageShape, roiShape,
            msg=(f"expected image shape {imageShape} "
                 + f"to equal roi {roiShape}")
        )

    def test_subtract_background(self):
        """
        Given an np.ndarray, check that when the image_processor
        is passed a background_image. the subtract_background function
        call subtracts the returns an np.ndarray
        that is the difference between the two np.ndarrays
        """
        background_image = np.ones(self.size)
        image_processor = ImageProcessor(background_image=background_image)
        image = image_processor.subtract_background(self.image)
        image = image
        background = np.clip(self.image - 1, 0, None)
        np.testing.assert_array_equal(
            image, background,
            err_msg=("expected image to equal background "
                     + "during background subtraction")
        )

        """
        Given an np.ndarray check that when the image_processor
        is passed a threshold check that subtraction occurs correctly
        """
        image_processor = ImageProcessor(threshold=1)
        image = image_processor.subtract_background(self.image)
        image = image
        background = np.clip(self.image - 1, 0, None)
        np.testing.assert_array_equal(
            image, background,
            err_msg=("expected image to equal background "
                     + "when applying threshold")
        )
