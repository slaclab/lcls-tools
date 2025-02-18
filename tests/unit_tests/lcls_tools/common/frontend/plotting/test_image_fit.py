from lcls_tools.common.data.fit.methods import GaussianModel
from lcls_tools.common.frontend.plotting.image import plot_image_projection_fit
from lcls_tools.common.image.fit import ImageProjectionFitResult
import numpy as np


class TestImageFitPlotting:
    def test_image_projection_fit_plotting(self):
        x_projection_fit_parameters = {
            "mean": 0,
            "sigma": 1,
            "amplitude": 1,
            "offset": 0,
        }
        y_projection_fit_parameters = {
            "mean": 0,
            "sigma": 1,
            "amplitude": 1,
            "offset": 0,
        }
        image = np.random.rand(10, 10)
        result = ImageProjectionFitResult(
            centroid=[5, 5],
            rms_size=[1, 1],
            total_intensity=1,
            image=image,
            projection_fit_method=GaussianModel(use_priors=True),
            x_projection_fit_parameters=x_projection_fit_parameters,
            y_projection_fit_parameters=y_projection_fit_parameters,
        )
        plot_image_projection_fit(result)
