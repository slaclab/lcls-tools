import unittest
import os
import numpy as np
from lcls_tools.common.image_processing.image_processing import ImageProcessor
from lcls_tools.common.image_processing.roi import RectangularROI


class TestImageProcessing(unittest.TestCase):
    data_location: str = "tests/datasets/images/numpy/"
    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        self.center = [400,400]
        self.size = (800,800)
        self.widths= (300,300)
        self.radius = 50
        self.image = np.load(self.data_location + 'test_roi_image.npy')


    def test_process(self):
        '''
        Given an np.ndarray and roi process 
        and assert the return in an np.ndarray
        '''
        image_processor = ImageProcessor()
        image = image_processor.process(self.image)
        assert isinstance(image,np.ndarray)
        roi = RectangularROI(center =self.center,xwidth=self.widths[0], ywidth=self.widths[1])
        image_processor = ImageProcessor(roi=roi)
        image = image_processor.process(self.image)
        assert isinstance(image,np.ndarray)
        #TODO:run coverage

    def test_subtract_background(self):
        '''
        Given an np.ndarray, check that when the image_processor 
        is passed a background_image. the subtract_background function 
        call subtracts the returns an np.ndarray
        that is the difference between the two np.ndarrays
        '''
        background_image = np.ones(self.size)
        image_processor = ImageProcessor(background_image=background_image)
        image = image_processor.subtract_background(self.image)
        assert image.all() == (self.image-1).all()

        '''
        Given an np.ndarray check that when the image_processor 
        is passed a threshold check that the np.ndarray elements
        are clipped at to not drop below zero
        '''
        image_processor = ImageProcessor(threshold = 1)
        image = image_processor.subtract_background(self.image)
        assert image.all() >= np.zeros(self.size).all()

