from abc import ABC, abstractmethod
from typing import Optional, List, Callable

import numpy as np
from numpy import ndarray
from pydantic import PositiveFloat, Field

from lcls_tools.common.data.fit.method_base import MethodBase
from lcls_tools.common.model.gaussian import fit
from lcls_tools.common.data.fit.projection import ProjectionFit
from lcls_tools.common.measurements.utils import NDArrayAnnotatedType
import lcls_tools


class ImageFitResult(lcls_tools.common.BaseModel):
    centroid: List[float] = Field(min_length=2, max_length=2)
    rms_size: List[float] = Field(min_length=2, max_length=2)
    total_intensity: PositiveFloat
    image: NDArrayAnnotatedType


class ImageProjectionFitResult(ImageFitResult):
    projection_fit_method: Callable
    x_projection_fit_parameters: dict[str, float]
    y_projection_fit_parameters: dict[str, float]


class ImageFit(lcls_tools.common.BaseModel, ABC):
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
    #Default is the fit method from model.gaussian, but any callable can be passed here.
    #maybe this should be restricted to a special type of fit_callable.
    #class fit(some_gauss):
        #def __call__(proj_data):
    # or we can decorate these methods in some way to make them a different type that we can restrict h
    projection_fit_method: Optional[Callable] = fit
    def p(self):
        print('this is correct')
    def _fit_image(self, image: ndarray) -> ImageProjectionFitResult:
        x_projection = np.array(np.sum(image, axis=0))
        y_projection = np.array(np.sum(image, axis=1))
        pos_x = np.linspace(0,len(x_projection), len(x_projection))
        pos_y = np.linspace(0,len(y_projection), len(y_projection))                   
        x_parameters = self.projection_fit_method(pos_x,x_projection)
        y_parameters = self.projection_fit_method(pos_y,y_projection)
        print(x_parameters)
        print(y_parameters)
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
