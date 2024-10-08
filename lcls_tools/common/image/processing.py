import numpy as np
from scipy.ndimage import gaussian_filter
from pydantic import BaseModel, PositiveFloat, ConfigDict
from lcls_tools.common.image.roi import ROI


class ImageProcessor(BaseModel):
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
    roi: ROI = None
    background_image: np.ndarray = None
    threshold: PositiveFloat = 0.0

    def subtract_background(self, raw_image: np.ndarray) -> np.ndarray:
        """Subtract background pixel intensity from a raw image"""
        if self.background_image is not None:
            image = raw_image - self.background_image
        else:
            image = raw_image - self.threshold
        return image

    def clip_image(self, image):
        return np.clip(image, 0, None)

    def auto_process(self, raw_image: np.ndarray) -> np.ndarray:
        """Process image by subtracting background pixel intensity
        from a raw image, crop, and filter"""
        image = self.subtract_background(raw_image)
        clipped_image = self.clip_image(image)
        if self.roi is not None:
            cropped_image = self.roi.crop_image(clipped_image)
        else:
            cropped_image = clipped_image
        processed_image = self.filter(cropped_image)
        return processed_image

    def filter(self, unfiltered_image: np.ndarray, sigma=5) -> np.ndarray:
        # TODO: extend to other types of filters? Change the way we pass sigma?
        filtered_data = gaussian_filter(unfiltered_image, sigma)
        return filtered_data
