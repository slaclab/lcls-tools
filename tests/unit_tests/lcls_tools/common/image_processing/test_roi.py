import unittest
import os
import numpy as np
from lcls_tools.common.image_processing.roi import ROI,RectangularROI,CircularROI


class TestROI(unittest.TestCase):
    data_location: str = "tests/datasets/images/numpy/"
    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        self.center = [400,400]
        self.size = (800,800)
        self.widths= (300,300)
        self.radius = 50

        self.image = np.load(self.data_location + 'test_roi_image.npy')
        self.filled_value_test_image = np.load(self.data_location + 'test_roi_fill_value_image.npy')


    def test_roi(self):
        '''
        Test that Rectangular and Circular ROIs 
        still instantiate with these arguments
        '''
        rectangular =  RectangularROI(center =self.center,xwidth=self.widths[0], ywidth=self.widths[1])
        circular = CircularROI(center =self.center,radius =self.radius)

    def test_circular_roi_crop_image(self):
        '''
        Given a circular ROI and image, 
        test that image has correct size after cropping
        (size of roi)
        '''
        circular = CircularROI(center =self.center,radius = self.radius)
        cropped_image = circular.crop_image(self.image)
        assert cropped_image.shape[0] == 2*self.radius
        assert cropped_image.shape[1] == 2*self.radius


    def test_fill_value_outside_circle(self):
        '''
        Given a test image change the pixel values
        of all elements of the image outside a radius of 10 to zero
        Test that this image is now exactly equal to the test filled value image
        '''
        circular = CircularROI(center =self.center,radius = self.radius)
        image = circular.fill_value_outside_circle(img=self.image,center = self.center,radius=10,fill_value=0)
        assert image.all() == self.filled_value_test_image.all()


    def test_rectangular_roi_crop_image(self):
        '''
        Given a rectangular ROI and image, 
        test that image has correct size after cropping
        (size of roi)
        '''
        rectangular =  RectangularROI(center =self.center,xwidth=self.widths[0], ywidth=self.widths[1])
        cropped_image = rectangular.crop_image(self.image)
        assert cropped_image.shape == self.widths
        