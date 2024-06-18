from abc import ABC, abstractmethod
import numpy as np
from pydantic import BaseModel, PositiveFloat
from typing import List


class ROI(BaseModel, ABC):
    center: List[PositiveFloat]

    @property
    @abstractmethod
    def bounds(self):
        """Abstract proprety for the bounding width."""
        pass

    @property
    def box(self):
        return [
            int(self.center[0] - int(self.bounds[0] / 2)),
            int(self.center[1] - int(self.bounds[1] / 2)),
            int(self.center[0] + int(self.bounds[0] / 2)),
            int(self.center[1] + int(self.bounds[1] / 2))
        ]

    def crop_image(self, img) -> np.ndarray:
        """Crop image using the ROI center and bounding width."""
        x_size, y_size = img.shape
        if self.bounds[0] > x_size or self.bounds[1] > y_size:
            raise ValueError(
                f"must pass image that is larger than ROI, "
                f"image size is {img.shape}, "
            )
        img = img[self.box[0]:self.box[2],
                  self.box[1]:self.box[3]]
        return img


class RectangularROI(ROI):
    """
    Define a rectangular region of interest (ROI) for an image, cropping pixels outside
    the ROI.
    """
    width: List[PositiveFloat]

    @property
    def bounds(self):
        return self.width


class EllipticalROI(ROI):
    """
    Define an elliptical region of interest (ROI) for an image.
    """
    radius: List[PositiveFloat]

    @property
    def bounds(self):
        return [r * 2 for r in self.radius]

    def negative_fill(self, img, fill_value):
        """ Fill the region outside the defined ellipse. """
        r = self.radius
        if type(r) is float:
            r = [r, r]
        c = self.center
        height, width = img.shape
        for y in range(height):
            for x in range(width):
                distance = (((x - c[0]) / r[0]) ** 2
                            + ((y - c[1]) / r[1]) ** 2)
                if distance > 1:
                    img[y, x] = fill_value
        return img

    def crop_image(self, img, **kwargs) -> np.ndarray:
        """
        Crop the pixels outside a bounding box and set the boundary to a fill
        value (usually zero).
        """
        img = super().crop_image(img)
        fill_value = kwargs.get("fill_value", 0.0)
        img = self.negative_fill(img, fill_value)
        return img


class CircularROI(EllipticalROI):
    """
    Define a circular region of interest (ROI) for an image.
    """
    radius: PositiveFloat

    @property
    def bounds(self):
        return [self.radius * 2, self.radius * 2]
