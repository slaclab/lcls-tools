from lcls_tools.common.measurements.screen_beam_profile_measurement import (
    ScreenBeamProfileMeasurement,
)
from lcls_tools.common.data.fit.projection import ProjectionFit
from lcls_tools.common.data.fit.methods import GaussianModel
from lcls_tools.common.image.processing import ImageProcessor
from lcls_tools.common.image.roi import ROI
from lcls_tools.common.devices.device import Metadata
from lcls_tools.common.devices.screen import (
    ScreenControlInformation,
    ScreenPVSet,
    Screen,
)
import numpy as np
import unittest


class ScreenTest(Screen):
    @property
    def image(self) -> np.ndarray:
        return self._image

    @image.setter
    def image(self, image):
        self._image = image


class TestScreenBeamProfileMeasurement(unittest.TestCase):
    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        self.test_instantiate_pydantic_objects()

    def create_test_image(self, size: tuple, center: list, radius: int):
        # make img that is a circle in the center of the image with known
        # standard dev and mean. no imports, no calls to external or
        # internal files.
        image = np.zeros(size)
        for y in range(image.shape[0]):
            for x in range(image.shape[1]):
                distance = np.sqrt((x - center[0]) ** 2 + (y - center[1]) ** 2)
                if distance < radius:
                    image[y, x] = 1
        return image

    def test_instantiate_pydantic_objects(self):
        # creating image processing class
        self.radius = 50
        self.size = (800, 800)
        self.center = [400, 400]
        self.extent = [300, 300]
        self.means = [150, 150]
        self.sigmas = [30, 30]
        self.amplitude = [99, 99]
        self.offsets = [1, 1]
        self.roi = ROI(center=[400, 400], extent=[300, 300])
        self.image_processor = ImageProcessor(roi=self.roi)

        self.pvs = {
            "image": "ArrayData",
            "n_bits": "N_OF_BITS",
            "n_col": "Image:ArraySize1_RBV",
            "n_row": "Image:ArraySize0_RBV",
            "resolution": ":RESOLUTION",
        }
        self.metadata = {
            "area": "TEST",
            "beam_path": ["SC_TEST"],
            "sum_l_meters": 99.99,
        }
        self.control_name = "OTRS:TEST:650:"

        self.screen_pvs = ScreenPVSet(**self.pvs)
        self.meta_data = Metadata(**self.metadata)
        self.controls_information = ScreenControlInformation(
            control_name=self.control_name, PVs=self.screen_pvs
        )
        self.screen_test = ScreenTest(
            controls_information=self.controls_information, metadata=self.metadata
        )
        self.screen_test.image = self.create_test_image(
            size=self.size, center=self.center, radius=self.radius
        )
        self.gauss_model = GaussianModel()
        self.projection = ProjectionFit(model=self.gauss_model)

        self.screen_beam_profile_measurement = ScreenBeamProfileMeasurement(
            name=self.control_name,
            device=self.screen_test,
            image_processor=self.image_processor,
            fitting_tool=self.projection,
        )

    def test_single_measure(self):
        perform_single_measure = self.screen_beam_profile_measurement.single_measure()
        self.assertIsInstance(perform_single_measure, dict)
        assert len(perform_single_measure) == 2

    def test_measure(self):
        perform_measure = self.screen_beam_profile_measurement.measure()
        self.assertIsInstance(perform_measure, list)
        self.assertIsInstance(perform_measure[0], dict)
        if isinstance(self.gauss_model, GaussianModel):
            for key, val in perform_measure[0].items():
                if key == "amplitude_x":
                    self.assertTrue(90 <= val <= 100)
                elif key == "amplitude_y":
                    self.assertTrue(90 <= val <= 100)
                elif key == "mean_x":
                    self.assertTrue(140 <= val <= 160)
                elif key == "mean_y":
                    self.assertTrue(140 <= val <= 160)
                elif key == "sigma_x":
                    self.assertTrue(20 <= val <= 40)
                elif key == "sigma_y":
                    self.assertTrue(20 <= val <= 40)
                elif key == "offset_x":
                    self.assertTrue(0 <= val <= 1)
                elif key == "offset_y":
                    self.assertTrue(0 <= val <= 1)
