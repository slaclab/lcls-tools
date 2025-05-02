from copy import copy
from typing import Optional

import numpy as np
from scipy.ndimage import gaussian_filter, median_filter
from pydantic import PositiveFloat, ConfigDict, PositiveInt
from lcls_tools.common.image.roi import ROI
import lcls_tools


class ImageProcessor(lcls_tools.common.BaseModel):
    """
    Image Processing class that allows for background subtraction and roi cropping
    ------------------------
    Arguments:
    roi: ROI (roi object either Circular or Rectangular),
    background_image: np.ndarray (optional image that will be used in
        background subtraction if passed),
    threshold: Positive Float (value of pixel intensity to be subtracted
        if background_image is None, default value = 0.0)
    visualize: bool (plots processed image)
    ------------------------
    Methods:
    subtract_background: takes a raw image and does pixel intensity subtraction
    process: takes raw image and calls subtract_background, passes to result
        to the roi object for cropping.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    roi: Optional[ROI] = None
    background_image: Optional[np.ndarray] = None
    threshold: Optional[PositiveFloat] = 0.0
    gaussian_filter_size: Optional[PositiveInt] = None
    median_filter_size: Optional[PositiveInt] = None

    def subtract_background(self, raw_image: np.ndarray) -> np.ndarray:
        """Subtract background pixel intensity from a raw image"""
        if self.background_image is not None:
            image = raw_image - self.background_image
        else:
            image = raw_image - self.threshold

        # clip images to make sure values are positive
        return np.clip(image, 0, None)

    def auto_process(self, raw_image: np.ndarray) -> np.ndarray:
        """Process image by subtracting background pixel intensity
        from a raw image, crop, and filter"""
        raw_image = copy(raw_image)
        image = self.subtract_background(raw_image)
        if self.roi is not None:
            image = self.roi.crop_image(image)

        if self.median_filter_size is not None:
            image = median_filter(image, self.median_filter_size)

        # apply smoothing filter if smoothing_factor is specified
        if self.gaussian_filter_size is not None:
            image = gaussian_filter(image, self.gaussian_filter_size)

        return image
