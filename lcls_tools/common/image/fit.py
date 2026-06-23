from abc import ABC, abstractmethod
import importlib
from typing import List, Optional

import numpy as np
from numpy import ndarray
from pydantic import PositiveFloat, Field, ConfigDict
from enum import Enum
from lcls_tools.common.measurements.utils import NDArrayAnnotatedType
import lcls_tools
import warnings


class ImageFitResult(lcls_tools.common.BaseModel):
    centroid: List[float] = Field(min_length=2, max_length=2)
    rms_size: List[float] = Field(min_length=2, max_length=2)
    total_intensity: PositiveFloat
    image: NDArrayAnnotatedType


class ImageProjectionFitFailureMode(Enum):
    """
    NONE : 0
        Flag for when the projection fitting had no validation errors
    BEAM_SIZE_TOO_SMALL : 1
        Flag for when the beam size from the fit is below the min_beam_size threshold
    BEAM_EXTENT_OFF_SCREEN : 2
        FLag for when the beam extends off the screen
    LOW_SIGNAL_TO_NOISE_RATIO : 3
        Flag for when the signal_to_noise_ratio is below the signal_to_noise_threshold
    """

    NONE = 0
    BEAM_SIZE_TOO_SMALL = 1
    BEAM_EXTENT_OFF_SCREEN = 2
    LOW_SIGNAL_TO_NOISE_RATIO = 3


class ImageProjectionFitResult(ImageFitResult):
    projection_fit_module: str
    projection_fit_parameters: List[dict[str, float]]
    signal_to_noise_ratio: NDArrayAnnotatedType = Field(
        description="Ratio of fit amplitude to noise std in the data"
    )
    beam_extent: NDArrayAnnotatedType = Field(
        description="Extent of the beam in the data, defined as mean +/- 2*sigma"
    )
    failure_mode: Optional[List[ImageProjectionFitFailureMode]] = Field(
        default=None,
        description="Reason for failure if either the x/y projection fit was rejected during fit validation",
    )


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
    the x/y projections of the input image, given as a 2d array of intensity per pixel.
    The default configuration uses a Gaussian fitting of the profile with prior distributions
    placed on the model parameters.

    Attributes
    ----------
    fit_module : str
        Name of the fitting module to use for the projections. Must be a module
        in lcls_tools.common.model.
    validate_fit : bool
        Whether to validate fit parameters after fitting. If True, fitting will return NaN values if
        the beam extent is off the screen or if the fit amplitude is below the noise threshold.
        Default is False.
    signal_to_noise_threshold : PositiveFloat
        Fit amplitude to noise threshold for the fit. If the amplitude of the fit is below this
        threshold times the noise standard deviation and `validate_fit` is True,
        the fit parameters will be set to NaN.
    min_beam_size : PositiveFloat
        Minimum beam size in pixels for the fit. If the beam size of the fit is below this threshold,
        and 'validate_fit' is True, the fit parameters will be set to NaN.
    beam_extent_n_stds : PositiveFloat
        Number of standard deviations on either side to use for the beam extent. If the beam
        extent is outside the image and `validate_fit` is True, the fit parameters will be set to NaN.
    use_prior : bool
        Whether to use prior distributions in the fit.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    fit_module: str = "gaussian"
    validate_fit: bool = Field(
        False, description="Whether to validate fit parameters after fitting."
    )
    signal_to_noise_threshold: PositiveFloat = Field(
        2.0, description="Fit amplitude to noise threshold for the fit"
    )
    min_beam_size: PositiveFloat = Field(
        1.0, description="Minimum beam size in pixels to accept for validation"
    )
    beam_extent_n_stds: PositiveFloat = Field(
        2.0,
        description="Number of standard deviations on either side to use for the beam extent",
    )
    use_prior: bool = Field(
        False, description="Whether to use prior distributions in the fit"
    )

    def _fit_image(self, image: ndarray) -> ImageProjectionFitResult:
        dimensions = ("x", "y")
        fit_parameters = []
        signal_to_noise_ratios = []
        beam_extent = []
        failure_mode = []

        module = importlib.import_module(f"lcls_tools.common.model.{self.fit_module}")

        for axis, dim in enumerate(dimensions):
            projection = np.array(np.sum(image, axis=axis))
            x = np.arange(len(projection))
            parameters = module.fit(x, projection, use_prior=self.use_prior)

            snr = module.signal_to_noise(parameters)

            # calculate the extent of the beam in the projection - scaled to the image size
            extent = module.extent(parameters, self.beam_extent_n_stds)

            # perform validation checks, modify parameters if checks fail
            if self.validate_fit:
                fmode = self._validate_parameters(
                    parameters, snr, extent, projection, dim
                )
                failure_mode.append(fmode)
            else:
                failure_mode = None

            fit_parameters.append(parameters)
            signal_to_noise_ratios.append(snr)
            beam_extent.append(extent)

        result = ImageProjectionFitResult(
            centroid=[ele["mean"] for ele in fit_parameters],
            rms_size=[ele["sigma"] for ele in fit_parameters],
            total_intensity=image.sum(),
            projection_fit_parameters=fit_parameters,
            image=image,
            projection_fit_module=self.fit_module,
            signal_to_noise_ratio=signal_to_noise_ratios,
            beam_extent=beam_extent,
            failure_mode=failure_mode,
        )

        return result

    def _validate_parameters(
        self, parameters, signal_to_noise_ratios, beam_extent, projection, dim
    ):
        # if the beam size is smaller than the specified minimum number of pixels, fits cannot be trusted
        if self.min_beam_size is not None:
            if parameters["sigma"] < self.min_beam_size:
                for name in parameters.keys():
                    parameters[name] = np.nan

                warnings.warn(
                    f"Projection in {dim} had too small a beam size, fit cannot be trusted"
                )
                return ImageProjectionFitFailureMode.BEAM_SIZE_TOO_SMALL

        # if the beam extent is outside the image then its off the screen etc. and fits cannot be trusted
        if self.beam_extent_n_stds is not None:
            if beam_extent[0] < 0 or beam_extent[1] > len(projection):
                for name in parameters.keys():
                    parameters[name] = np.nan

                warnings.warn(
                    f"Projection in {dim} was off the screen, fit cannot be trusted"
                )
                return ImageProjectionFitFailureMode.BEAM_EXTENT_OFF_SCREEN

        # if the amplitude of the the fit is smaller than noise then reject
        # moving this into a validate function to clean it up.
        if self.signal_to_noise_threshold is not None:
            if signal_to_noise_ratios < self.signal_to_noise_threshold:
                for name in parameters.keys():
                    parameters[name] = np.nan

                warnings.warn(
                    f"Projection in {dim} had a low amplitude relative to noise"
                )
                return ImageProjectionFitFailureMode.LOW_SIGNAL_TO_NOISE_RATIO

        return ImageProjectionFitFailureMode.NONE
