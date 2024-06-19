import numpy as np
from pydantic import (
    BaseModel,
    field_validator,
    model_validator,
    PositiveFloat
)
from typing import Any, Dict, List, Optional
from typing_extensions import Self


class ROI(BaseModel):
    center: List[PositiveFloat]
    extent: List[PositiveFloat]

    @property
    def box(self):
        return [
            int(self.center[0] - int(self.extent[0] / 2)),
            int(self.center[1] - int(self.extent[1] / 2)),
            int(self.center[0] + int(self.extent[0] / 2)),
            int(self.center[1] + int(self.extent[1] / 2))
        ]

    def crop_image(self, img) -> np.ndarray:
        """Crop image using the ROI center and bounding extent."""
        x_size, y_size = img.shape
        if self.extent[0] > x_size or self.extent[1] > y_size:
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
    radius: List[PositiveFloat]

    @model_validator(mode='before')
    def __set_radius_and_extent__(cls, data: Any) -> Any:
        # The caret key '^' is logical xor in this case. 
        if not ('radius' in data) ^ ('extent' in data):
            raise ValueError('enter extent or radius field but not both')
        if 'radius' in data:
            data['extent'] = [r * 2 for r in data['radius']]
        if 'extent' in data:
            data['radius'] = [w / 2 for w in data['extent']]
        return data

    def negative_fill(self, img, fill_value):
        """ Fill the region outside the defined ellipse. """
        r = self.radius
        c = self.center
        height, extent = img.shape
        for y in range(height):
            for x in range(extent):
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
    @model_validator(mode='before')
    def __set_radius_and_extent__(cls, data: Dict[str, Any]) -> Any:
        if 'radius' in data:
            data['radius'] = [data['radius'], data['radius']]
        if 'extent' in data:
            data['extent'] = [data['extent'], data['extent']]
        return super().__set_radius_and_extent__(data)
