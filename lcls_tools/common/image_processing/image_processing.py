import numpy as np
from matplotlib import pyplot as plt
from pydantic import BaseModel, PositiveFloat, ConfigDict
from lcls_tools.common.image_processing.roi import ROI


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
    roi: ROI
    background_image: np.ndarray = None
    threshold: PositiveFloat = 0.0
    visualize: bool = False

    def subtract_background(self, raw_image: np.ndarray) -> np.ndarray:
        """Subtract background pixel intensity from a raw image"""
        if self.background_image is not None:
            # needs test?
            image = raw_image - self.background_image
        else:
            image = np.clip(raw_image - self.threshold, 0, 1e7)
        return image

    def process(self, raw_image: np.ndarray) -> np.ndarray:
        """Process image by subtracting background pixel intensity from a raw image then cropping it"""
        processed_image = self.subtract_background(raw_image)
        if self.roi is not None:
            processed_image = self.roi.crop_image(processed_image)
        if self.visualize:
            # here needs some work
            fig, ax = plt.subplots(2, 1)
            c = ax[0].imshow(raw_image > 0, origin="lower")
            # g = ax[1].imshow(processed_image > 0, origin="lower")
            rect = self.roi.get_patch()
            ax[0].add_patch(rect)
            fig.colorbar(c)

        return processed_image

    # needs read h5 file or update property to not load from file
