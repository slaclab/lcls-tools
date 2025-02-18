import numpy as np
from lcls_tools.common.data.fit.methods import GaussianModel
from lcls_tools.common.image.fit import ImageProjectionFit


class TestImageProjectionFit:      
    def test_fit(self):
        test_image = np.zeros((100, 100))
        test_image[40:60, 40:60] = 255

        image_fit = ImageProjectionFit()
        result = image_fit.fit_image(test_image)

        assert np.allclose(result.centroid, [50, 50])
        assert np.allclose(result.rms_size, [8.0347, 8.0347])
        assert np.allclose(result.total_intensity, 102000.0)
        assert np.allclose(result.image, test_image)
        assert isinstance(result.projection_fit_method, GaussianModel)

