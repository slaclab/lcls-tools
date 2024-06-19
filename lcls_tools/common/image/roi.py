import numpy as np
from pydantic import (
    BaseModel,
    field_validator,
    model_validator,
    PositiveFloat
)
from typing import List, Optional
from typing_extensions import Self


class ROI(BaseModel):
    center: List[PositiveFloat]
    width: List[PositiveFloat]

    @property
    def box(self):
        return [
            int(self.center[0] - int(self.width[0] / 2)),
            int(self.center[1] - int(self.width[1] / 2)),
            int(self.center[0] + int(self.width[0] / 2)),
            int(self.center[1] + int(self.width[1] / 2))
        ]

    def crop_image(self, img) -> np.ndarray:
        """Crop image using the ROI center and bounding width."""
        x_size, y_size = img.shape
        if self.width[0] > x_size or self.width[1] > y_size:
            raise ValueError(
                f"must pass image that is larger than ROI, "
                f"image size is {img.shape}, "
            )
        img = img[self.box[0]:self.box[2],
                  self.box[1]:self.box[3]]
        return img


class EllipticalROI(ROI):
    """
    Define an elliptical region of interest (ROI) for an image.
    """
    radius: Optional[List[PositiveFloat]] = None
    width: Optional[List[PositiveFloat]] = None

    @model_validator(mode='after')
    def __set_radius_and_width__(self) -> Self:
        radius = self.radius
        width = self.width
        if not (radius is None) ^ (width is None):
            raise ValueError('enter width or radius field but not both')
        if radius is not None:
            self.width = [r * 2 for r in radius]
        if width is not None:
            self.radius = [w / 2 for w in width]
        return self

    def negative_fill(self, img, fill_value):
        """ Fill the region outside the defined ellipse. """
        r = self.radius
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
    radius: Optional[PositiveFloat] = None
    width: Optional[PositiveFloat] = None

    @field_validator('radius', 'width')
    @classmethod
    def double(cls, v: PositiveFloat) -> PositiveFloat:
        if v is not None:
            v = [v, v]
        return v
