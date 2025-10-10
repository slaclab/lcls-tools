from abc import ABC, abstractmethod
from typing import Optional, List, Callable

import numpy as np
from numpy import ndarray
from pydantic import PositiveFloat, Field, NonNegativeFloat, ConfigDict

from lcls_tools.common.data.fit.method_base import MethodBase
from lcls_tools.common.model.gaussian import fit, curve
from lcls_tools.common.data.fit.projection import ProjectionFit
from lcls_tools.common.measurements.utils import NDArrayAnnotatedType
import lcls_tools
import warnings

class ImageFitResult(lcls_tools.common.BaseModel):
    centroid: List[float] = Field(min_length=2, max_length=2)
    rms_size: List[float] = Field(min_length=2, max_length=2)
    total_intensity: PositiveFloat
    image: NDArrayAnnotatedType



class ImageProjectionFitResult(ImageFitResult):
    projection_fit_method: Callable
    curve: Callable
    validation_method: Optional[Callable] = None
    #total_intensity: NonNegativeFloat --> is this duplicated
    projection_fit_parameters: List[dict[str, float]]
    noise_std: NDArrayAnnotatedType = Field(
        description="Standard deviation of the noise in the data"
    )
    signal_to_noise_ratio: NDArrayAnnotatedType = Field(
        description="Ratio of fit amplitude to noise std in the data"
    )
    beam_extent: NDArrayAnnotatedType = Field(
        description="Extent of the beam in the data, defined as mean +/- 2*sigma"
    )
'''

class ImageProjectionFitResult(ImageFitResult):
    projection_fit_method: Callable
    projection_fit_parameters: List[dict,[str,float]]
'''

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
    @abstractmethod
    def _validate_parameters(self, parameters: list[float]):
        """
        Private method to be overwritten by subclasses.
        Expected to validate parameters.
        return bool stating validity
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
    model_config = ConfigDict(arbitrary_types_allowed=True)
    projection_fit_method: Optional[Callable] = fit
    curve: Optional[Callable] = curve
    signal_to_noise_threshold: PositiveFloat = Field(
        4.0, description="Fit amplitude to noise threshold for the fit"
    )
    beam_extent_n_stds: PositiveFloat = Field(
        2.0,
        description="Number of standard deviations on either side to use for the beam extent",
    )

    def _fit_image(self, image: ndarray) -> ImageProjectionFitResult:
        directions = ('x','y')
        fit_parameters = []
        noise_stds = []
        signal_to_noise_ratios = []
        beam_extent = []

        for axis, dir in enumerate(directions):
            projection = np.array(np.sum(image, axis=axis))
            x = np.arange(len(projection))
            parameters = self.projection_fit_method(x, projection)
            print(parameters)
            # determine the noise around the projection fit
    
            noise_std = np.std(
                self.curve(x, **parameters) - projection
            )
            noise_stds.append(noise_std)
            signal_to_noise_ratios.append(parameters["amp"] / noise_std)

            # calculate the extent of the beam in the projection - scaled to the image size
            beam_extent.append(
                [
                    parameters["mean"] - self.beam_extent_n_stds * parameters["sigma"],
                    parameters["mean"] + self.beam_extent_n_stds * parameters["sigma"],
                ]
            )
            # if the amplitude of the the fit is smaller than noise then reject
            #moving this into a validate function to clean it up.
            if signal_to_noise_ratios[-1] < self.signal_to_noise_threshold:
                #for name in parameters.keys():
                #    parameters[name] = np.nan

                warnings.warn(
                    f"Projection in {dir} had a low amplitude relative to noise"
                )

            # if the beam extent is outside the image then its off the screen etc. and fits cannot be trusted
            if beam_extent[-1][0] < 0 or beam_extent[-1][1] > len(projection):
                #for name in parameters.keys():
                #    parameters[name] = np.nan

                warnings.warn(
                    f"Projection in {dir} was off the screen, fit cannot be trusted"
                )

            fit_parameters.append(parameters)

        result = ImageProjectionFitResult(
            centroid=[ele["mean"] for ele in fit_parameters],
            rms_size=[ele["sigma"] for ele in fit_parameters],
            total_intensity=image.sum(),
            projection_fit_parameters=fit_parameters,
            curve=self.curve,
            image=image,
            projection_fit_method=self.projection_fit_method,
            noise_std=noise_stds,
            signal_to_noise_ratio=signal_to_noise_ratios,
            beam_extent=beam_extent,
        )

        return result    

    def _validate_parameters(self):
        pass
        




