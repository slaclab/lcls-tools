import unittest
import numpy as np

from lcls_tools.common.image.processing import ImageProcessor
from lcls_tools.common.image.roi import RectangularROI


class TestImageProcessing(unittest.TestCase):
    data_location: str = "tests/datasets/images/numpy/"

    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        self.center = [400, 400]
        self.size = (800, 800)
        self.width = [350, 300]
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
        roi = RectangularROI(center=self.center, width=self.width)
        image_processor = ImageProcessor(roi=roi)
        image = image_processor.auto_process(self.image)
        self.assertIsInstance(
            image, np.ndarray,
            msg="expected image to be an instance of np.ndarray"
        )
        imageShape = image.shape
        roiShape = tuple(roi.width)
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
        background = (self.image - 1)
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
        background = (self.image - 1)
        np.testing.assert_array_equal(
            image, background,
            err_msg=("expected image to equal background "
                     + "when applying threshold")
        )

    def test_clip(self):
        """
        Given an np.ndarray check that when the image_processor
        is passed a threshold check that the np.ndarray elements
        are clipped at to not drop below zero
        """
        image_processor = ImageProcessor(threshold=100)
        image = image_processor.subtract_background(self.image)
        clipped_image = image_processor.clip_image(image)
        np.testing.assert_array_equal(
            clipped_image, np.zeros(self.size),
            err_msg=("expected clipped image to equal zero "
                     + "when subtracting background with threshold")
        )
