from lcls_tools.common.measurements.screen_beam_profile_measurement import ScreenBeamProfileMeasurement
from lcls_tools.common.data_analysis.projection_fit.projection_fit import ProjectionFit
from lcls_tools.common.data_analysis.projection_fit.gaussian_model import GaussianModel
from lcls_tools.common.image_processing.image_processing import ImageProcessor
from lcls_tools.common.image_processing.roi import ROI, RectangularROI, CircularROI
from lcls_tools.common.devices.device import Device, PVSet, ControlInformation, Metadata
from lcls_tools.common.devices.screen import ScreenControlInformation, ScreenPVSet, Screen
from matplotlib import pyplot as plt
from epics import PV, caget
import numpy as np
import h5py
import random
import unittest

class ScreenTest(Screen):
    @property
    def image(self) -> np.ndarray:
        return self._image
    
    @image.setter
    def image(self,image):
        self._image = image

class TestScreenBeamProfileMeasurement(unittest.TestCase):
    def create_test_image(self,size:tuple,center:list,radius:int):
        # make img that is a circle in the center of the image with known standard dev and mean. no imports, no calls to external or
        # internal files. 
        image = np.zeros(size)
        for y in range(image.shape[0]):
            for x in range(image.shape[1]):
                distance =  np.sqrt((x - center[0])**2 + (y - center[1])**2)
                if distance < radius:
                    image[y,x]= 1
        return image
    def instantiate_pydantic_objects(self):
        self.gauss_model = GaussianModel()
        self.projection_fit = ProjectionFit(model = self.gauss_model,visualize_fit = True)

        # creating image processing class
        self.radius = 50
        self.size = (800,800)
        self.center = [400,400]
        self.xwidth = 300
        self.ywidth = 300
        self.roi = RectangularROI(center =[400,400],xwidth=300,ywidth=300)
        self.image_processor = ImageProcessor(roi = self.roi)

        self.pvs = {
                    'image': 'OTRS:TEST:650:Image:ArrayData',
                    'n_bits': 'OTRS:TEST:650:N_OF_BITS',
                    'n_col': 'OTRS:TEST:650:Image:ArraySize1_RBV',
                    'n_row': 'OTRS:TEST:650:Image:ArraySize0_RBV',
                    'resolution': 'OTRS:TEST:650:RESOLUTION'
                    }
        self.metadata = {
                'area': 'TEST',
                'beam_path': ['SC_TEST'],
                'sum_l_meters': 99.99
                }
        self.control_name =  "OTRS:TEST:650:"

        self.screen_pvs = ScreenPVSet(**self.pvs)
        self.meta_data = Metadata(**self.metadata)
        self.controls_information = ScreenControlInformation(control_name = self.control_name, PVs = self.screen_pvs )
        self.screen_test = ScreenTest(controls_information = self.controls_information, metadata = self.metadata)

        self.screen_beam_profile_measurement = ScreenBeamProfileMeasurement
        
    def test_single_measure(self):
        pass
    def test_measure(self):
        pass