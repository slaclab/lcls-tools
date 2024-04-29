import unittest
import os
import numpy as np
from lcls_tools.common.image_processing.roi import ROI,RectangularROI,CircularROI

class TestImageCreator():   
    def create_test_image(self, size: tuple, center: list, radius: int):
        ''' 
        make img that is a circle in the center of the image with known
        standard dev and mean. no imports, no calls to external or
        internal files.
         '''
        image = np.zeros(size)
        for y in range(image.shape[0]):
            for x in range(image.shape[1]):
                distance = np.sqrt((x - center[0]) ** 2 + (y - center[1]) ** 2)
                if distance < radius:
                    image[y, x] = 1
        return image

class ROITest(unittest.TestCase):
    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        self.center = [400,400]
        self.size = (800,800)
        self.widths= (300,300)
        self.radius = 50
        self.image_creator = TestImageCreator()
        self.image = self.image_creator.create_test_image(size = self.size, center=self.center,radius = self.radius)
    def test_roi(self):
        rectangular =  RectangularROI(center =self.center,xwidth=self.widths[0], ywidth=self.widths[1])
        circular = CircularROI(center =self.center,radius =self.radius)

    def test_circular_roi_crop_image(self):
        circular = CircularROI(center =self.center,radius = self.radius)
        cropped_image = circular.crop_image(self.image)
        assert cropped_image.shape[0] < self.image.shape[0]
        assert cropped_image.shape[1] < self.image.shape[1]

    def test_fill_value_outside_circle(self):
        # create circular ROI with zero length
        circular = CircularROI(center =self.center,radius = 1)
        # fill values outside the circular radius to zero. if this works the projections will be zero)
        # radius zero wont work set to radius to one,  if distance  > 1 fill_value so only 8 elements in the 2 d array have a value
        image = circular.fill_value_outside_circle(img=self.image,center = self.center,radius=1,fill_value=0)
        assert np.array(np.sum(image,axis=0))[self.center[1]] <5
        assert np.array(np.sum(image,axis=1))[self.center[0]] <5


    def test_rectangular_roi_crop_image(self):
        rectangular =  RectangularROI(center =self.center,xwidth=self.widths[0], ywidth=self.widths[1])
        cropped_image = rectangular.crop_image(self.image)
        assert cropped_image.shape == self.widths