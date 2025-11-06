import unittest
from unittest.mock import MagicMock
from lcls_tools.common.devices.screen import Screen
from lcls_tools.common.measurements.screen_profile import (
    ScreenBeamProfileMeasurement,
    ScreenBeamProfileMeasurementResult,
)
import numpy as np


class TestScreenBeamProfileMeasurement(unittest.TestCase):
    def setUp(self):
        self.screen = MagicMock(Screen)
        self.screen.resolution = 1.0

        # create a mock Screen device
        def mock_get_image(*args):
            image = np.zeros((100, 100))
            image[40:60, 40:60] = 255
            return image

        type(self.screen).image = property(mock_get_image)

    def test_measure(self):
        measurement = ScreenBeamProfileMeasurement(beam_profile_device=self.screen)
        result = measurement.measure()
        self.assertIsInstance(result, ScreenBeamProfileMeasurementResult)

        assert result.processed_images.shape == (1, 100, 100)
        assert result.rms_sizes.shape == (2,)
        assert result.total_intensities.shape == ()
        assert np.allclose(result.rms_sizes, np.array([7.6924137, 7.6924137]))
        assert np.allclose(result.centroids.flatten(), np.array([49.5, 49.5]))
        assert np.allclose(result.total_intensities, np.array([102000.0]))

        assert result.metadata == measurement.model_dump()

    def test_multiple_shot_measure(self):
        measurement = ScreenBeamProfileMeasurement(
            beam_profile_device=self.screen, n_shots=10
        )
        result = measurement.measure()
        self.assertIsInstance(result, ScreenBeamProfileMeasurementResult)

        assert result.processed_images.shape == (10, 100, 100)
        assert result.rms_sizes.shape == (2,)
        assert result.total_intensities.shape == ()
