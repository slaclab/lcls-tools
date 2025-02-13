import unittest
from unittest.mock import MagicMock
from lcls_tools.common.devices.screen import Screen
from lcls_tools.common.measurements.screen_profile import ScreenBeamProfileMeasurement, ScreenBeamProfileMeasurementResult
import numpy as np

class TestScreenBeamProfileMeasurement(unittest.TestCase):
    def setUp(self):
        screen = MagicMock(Screen)
        # create a mock Screen device
        def mock_get_image(*args):
            image = np.zeros((100, 100))
            image[40:60, 40:60] = 255
            return image

        type(screen).image = property(mock_get_image)

        self.measurement = ScreenBeamProfileMeasurement(device=screen)

    def test_measure(self):
        result = self.measurement.measure()
        self.assertIsInstance(result, ScreenBeamProfileMeasurementResult)

        assert result.raw_images.shape == (1, 100, 100)
        assert result.processed_images.shape == (1, 100, 100)
        assert result.rms_sizes.shape == (1, 2)
        assert result.centroids.shape == (1, 2)
        assert result.total_intensities.shape == (1,)
        assert np.allclose(result.rms_sizes, np.array([8.0347, 8.0347]))
        assert np.allclose(result.centroids, np.array([50, 50]))
        assert np.allclose(result.total_intensities, np.array([102000.0]))

        assert result.metadata == self.measurement.model_dump()

    def test_multiple_shot_measure(self):
        result = self.measurement.measure(n_shots=10)
        self.assertIsInstance(result, ScreenBeamProfileMeasurementResult)

        assert result.raw_images.shape == (10, 100, 100)
        assert result.processed_images.shape == (10, 100, 100)
        assert result.rms_sizes.shape == (10, 2)
        assert result.centroids.shape == (10, 2)
        assert result.total_intensities.shape == (10,)


