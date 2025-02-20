from abc import ABC, abstractmethod
from typing import Optional, List

import numpy as np
from numpy import ndarray
from pydantic import PositiveFloat, Field

from lcls_tools.common.data.fit.method_base import MethodBase
from lcls_tools.common.data.fit.methods import GaussianModel
from lcls_tools.common.data.fit.projection import ProjectionFit
from lcls_tools.common.measurements.utils import NDArrayAnnotatedType
from lcls_tools.common.pydantic import LCLSToolsBaseModel


class ImageFitResult(LCLSToolsBaseModel):
    centroid: List[float] = Field(min_length=2, max_length=2)
    rms_size: List[float] = Field(min_length=2, max_length=2)
    total_intensity: PositiveFloat
    image: NDArrayAnnotatedType


class ImageProjectionFitResult(ImageFitResult):
    projection_fit_method: MethodBase
    x_projection_fit_parameters: dict[str, float]
    y_projection_fit_parameters: dict[str, float]


class ImageFit(LCLSToolsBaseModel, ABC):
    """
    Abstract class for determining beam properties from an image
    """
    def fit_image(self, image: ndarray) -> ImageFitResult:
        """
        Public method to determine beam properties from an image, including initial
        image processing, internal image fitting method, and image validation.

        """
        fit_result = self._fit_image(image)
        return fit_result

    @abstractmethod
    def _fit_image(self, image: ndarray) -> ImageFitResult:
        """
        Private image fitting method to be overwritten by subclasses. Expected to
        return a ImageFitResult dataclass.
        """
        ...


class ImageProjectionFit(ImageFit):
    """
    Image fitting class that gets the beam size and location by independently fitting
    the x/y projections. The default configuration uses a Gaussian fitting of the
    profile with prior distributions placed on the model parameters.
    """
    projection_fit_method: Optional[MethodBase] = GaussianModel(use_priors=True)

    def _fit_image(self, image: ndarray) -> ImageProjectionFitResult:
        x_projection = np.array(np.sum(image, axis=0))
        y_projection = np.array(np.sum(image, axis=1))

        proj_fit = ProjectionFit(model=self.projection_fit_method)

        x_parameters = proj_fit.fit_projection(x_projection)
        y_parameters = proj_fit.fit_projection(y_projection)

        result = ImageProjectionFitResult(
            centroid=[x_parameters["mean"], y_parameters["mean"]],
            rms_size=[x_parameters["sigma"], y_parameters["sigma"]],
            total_intensity=image.sum(),
            x_projection_fit_parameters=x_parameters,
            y_projection_fit_parameters=y_parameters,
            image=image,
            projection_fit_method=self.projection_fit_method,
        )

        return result
