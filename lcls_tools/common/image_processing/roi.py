from abc import ABC, abstractmethod
from typing import (
    List,
)
import numpy as np
from matplotlib import patches
from pydantic import (
    BaseModel,
    PositiveFloat,
)

class ROI(BaseModel, ABC):
    roi_type: str
    center: List[PositiveFloat]
    @abstractmethod
    def crop_image(self, img, **kwargs) -> np.ndarray:
        """ crop image using ROI"""
        pass
    @abstractmethod
    def get_patch(self):
        pass

class CircularROI(ROI):
    """
    Define a circular region of interest (ROI) for an image, cropping pixels outside a
    bounding box around the ROI and setting pixels outside the boundary to a fill
    value (usually zero).
    """
    radius: PositiveFloat
    @property
    def bounding_box(self):
        return [int(self.center[0] - int(self.radius)),
                int(self.center[1] - int(self.radius)),
                int(self.radius * 2), int(self.radius * 2)]

    def crop_image(self, img, **kwargs) -> np.ndarray:
        fill_value = kwargs.get("fill_value", 0.0)
        img = self.fill_value_outside_circle(img,self.center,self.radius,fill_value)
        bbox = self.bounding_box
        img = img[ bbox[1]: bbox[1] + bbox[3], bbox[0]: bbox[0] + bbox[2]]
        return img

    def fill_value_outside_circle(self,img:np.ndarray,center:List[PositiveFloat],radius:PositiveFloat,fill_value:float):
        height,width= img.shape
        for y in range(height):
            for x in range(width):
                distance =  np.sqrt((x - center[0])**2 + (y - center[1])**2)
                if distance > radius:
                    img[y, x] = fill_value
        return img
    

    def get_patch(self):
        return patches.Circle(
            tuple(self.center), self.radius, facecolor="none", edgecolor="r")

class RectangularROI(ROI):
    """
    Define a rectangular region of interest (ROI) for an image, cropping pixels outside
    the ROI.
    """
    xwidth: int
    ywidth: int
    @property
    def bounding_box(self):
        return [int(self.center[0] - int(self.xwidth / 2)),
                int(self.center[1] - int(self.ywidth / 2)),
                int(self.xwidth), int(self.ywidth)]

    def crop_image(self, img, **kwargs) -> np.ndarray:
        x_size, y_size = img.shape
        if self.xwidth > x_size or self.ywidth > y_size:
            raise ValueError(
                f"must specify ROI that is smaller than the image, "
                f"image size is {img.shape}")
        bbox = self.bounding_box
        img = img[ bbox[1]: bbox[1] + bbox[3], bbox[0]: bbox[0] + bbox[2]]
        return img

    def get_patch(self):
        return patches.Rectangle(
        (self.bounding_box[0],self.bounding_box[1]),self.bounding_box[2],self.bounding_box[3], facecolor="none", edgecolor="r")