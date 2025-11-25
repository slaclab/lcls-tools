import unittest
import numpy as np
from lcls_tools.common.frontend.plotting.image import plot_image_projection_fit
from lcls_tools.common.image.fit import ImageProjectionFit
import pprint


class TestImageProjectionFit(unittest.TestCase):
    def test_fit_and_visualization(self):
        test_image = np.zeros((100, 100))
        test_image[40:60, 30:70] = 255

        result = ImageProjectionFit().fit_image(test_image)
        pprint.pprint(result)
        assert np.allclose(result.centroid, [49.5, 49.5])
        assert np.allclose(result.rms_size, [15.09, 7.69], rtol=1e-2)
        assert np.allclose(result.total_intensity, test_image.sum())
        assert np.allclose(result.image, test_image)
        assert np.allclose(
            result.projection_fit_parameters[0]["error"], 1144.9406852568763, atol=1e-5
        )
        assert np.allclose(
            result.projection_fit_parameters[1]["error"], 1619.0121682734334, atol=1e-5
        )

        # test plotting
        plot_image_projection_fit(result)

    def test_with_validation(self):
        test_image = np.zeros((100, 100))
        test_image[40:60, 30:70] = 255

        projection_fit = ImageProjectionFit(
            signal_to_noise_threshold=5.0,
            validate_fit=True,
        )
        result = projection_fit.fit_image(test_image)
        pprint.pprint(result)
        assert np.allclose(result.centroid, [np.nan, 49.5], equal_nan=True)
        assert np.allclose(
            result.rms_size, [np.nan, 7.692413702989997], rtol=1e-2, equal_nan=True
        )
        assert np.allclose(result.total_intensity, test_image.sum())
        assert np.allclose(result.image, test_image)
