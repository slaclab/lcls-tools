import unittest
import numpy as np

from lcls_tools.common.image.processing import ImageProcessor
from lcls_tools.common.image.roi import ROI

import matplotlib.pyplot as plt

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
        # test return type
        image_processor = ImageProcessor()
        image = image_processor.process(self.image)
        self.assertIsInstance(
            image, np.ndarray, msg="expected image to be an instance of np.ndarray"
        )
        image_processor = ImageProcessor()
        image = image_processor.process(self.image)
        self.assertIsInstance(
            image, np.ndarray, msg="expected image to be an instance of np.ndarray"
        )

        # test fixed threshold
        image_processor = ImageProcessor(
            threshold=100,
            crop=False,
            center=False
        )
        image = image_processor.process(self.image)
        np.testing.assert_array_equal(
            image,
            np.clip(self.image - 100, 0, None),
            err_msg="expected image to equal thresholded image",
        )

        # test cropping
        image_processor = ImageProcessor(
            crop=True,
            threshold=0,
        )
        processed_image, offsets = image_processor.process(self.image, return_offsets=True)
        np.testing.assert_allclose(
            processed_image,
            self.image[200:599, 200:599],
            err_msg="expected processed image to equal cropped image",
        )
        np.testing.assert_array_equal(
            offsets,
            np.array([[200, 200]]),
            err_msg="expected offsets to equal crop start",
        )

        # test centering
        image_processor = ImageProcessor(
            center=True,
            crop=False,
            threshold=0,
        )
        processed_image, offsets = image_processor.process(self.image[100:, 100:], return_offsets=True)
        np.testing.assert_allclose(
            processed_image,
            self.image[50:-50, 50:-50],
            err_msg="expected processed image to equal cropped image",
        )
        np.testing.assert_array_equal(
            offsets,
            np.array([[50, 50]]),
            err_msg="expected offsets to equal crop start",
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
        background = np.clip(self.image - background_image, 0, None)
        np.testing.assert_array_equal(
            image,
            background,
            err_msg=(
                "expected image to equal background " + "during background subtraction"
            ),
        )

