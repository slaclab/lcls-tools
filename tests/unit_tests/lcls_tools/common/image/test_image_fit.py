import unittest
import numpy as np
from lcls_tools.common.frontend.plotting.image import plot_image_projection_fit
from lcls_tools.common.image.fit import ImageProjectionFit


class TestImageProjectionFit(unittest.TestCase):
    def test_fit_and_visualization(self):
        test_image = np.zeros((100, 100))
        test_image[40:60, 30:70] = 255

        result = ImageProjectionFit().fit_image(test_image)

        assert np.allclose(result.centroid, [49.5, 49.5])
        assert np.allclose(result.rms_size, [15.09, 7.69], rtol=1e-2)
        assert np.allclose(result.total_intensity, test_image.sum())
        assert np.allclose(result.image, test_image)

        # test plotting
        plot_image_projection_fit(result)

    def test_with_validation(self):
        test_image = np.zeros((100, 100))
        test_image[40:60, 30:70] = 255

        projection_fit = ImageProjectionFit(
            validate_fit=True,
        )
        result = projection_fit.fit_image(test_image)

        assert np.allclose(result.centroid, [np.nan, 49.5], equal_nan=True)
        assert np.allclose(result.rms_size, [np.nan, 7.692413702989997], rtol=1e-2, equal_nan=True)
        assert np.allclose(result.total_intensity, test_image.sum())
        assert np.allclose(result.image, test_image)
