import numpy as np
from lcls_tools.common.frontend.plotting.image import plot_image_projection_fit
from lcls_tools.common.image.fit import ImageProjectionFit


class TestImageProjectionFit:
    def test_fit_and_visualization(self):
        test_image = np.zeros((10, 10))
        test_image[4:6, 4:6] = 255

        result = ImageProjectionFit().fit_image(test_image)

        assert np.allclose(result.centroid, [5, 5])
        assert np.allclose(result.rms_size, [1.16, 1.16])
        assert np.allclose(result.total_intensity, 1020.0)
        assert np.allclose(result.image, test_image)

        # test plotting
        plot_image_projection_fit(result)
