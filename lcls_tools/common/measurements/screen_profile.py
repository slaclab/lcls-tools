from typing import Any

from lcls_tools.common.devices.screen import Screen
from lcls_tools.common.image.fit import ImageProjectionFit, ImageFit
from lcls_tools.common.image.processing import ImageProcessor
from lcls_tools.common.measurements.measurement import Measurement
import numpy as np
from pydantic import (
    ConfigDict,
    SerializeAsAny,
)
from typing import Optional

from lcls_tools.common.measurements.utils import NDArrayAnnotatedType
import lcls_tools


class ScreenBeamProfileMeasurementResult(lcls_tools.common.BaseModel):
    """
    Class that contains the results of a beam profile measurement

    Attributes
    ----------
    raw_images : ndarray
        Numpy array of raw images taken during the measurement
    processed_images : ndarray
        Numpy array of processed images taken during the measurement
    rms_sizes : ndarray
        Numpy array of rms sizes of the beam in microns.
    centroids : ndarray
        Numpy array of centroids of the beam in microns.
    total_intensities : ndarray
        Numpy array of total intensities of the beam.
    metadata : Any
        Metadata information related to the measurement.

    """

    raw_images: NDArrayAnnotatedType
    processed_images: NDArrayAnnotatedType
    rms_sizes: Optional[NDArrayAnnotatedType] = None
    centroids: Optional[NDArrayAnnotatedType] = None
    total_intensities: Optional[NDArrayAnnotatedType] = None
    metadata: SerializeAsAny[Any]

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ScreenBeamProfileMeasurement(Measurement):
    """
    Class that allows for beam profile measurements and fitting
    ------------------------
    Arguments:
    name: str (name of measurement default is beam_profile),
    device: Screen (device that will be performing the measurement),
    beam_fit: method for performing beam profile fit, default is gfit
    fit_profile: bool = True
    ------------------------
    Methods:
    single_measure: measures device and returns raw and processed image
    measure: does multiple measurements and has an option to fit the image
             profiles

    #TODO: DumpController?
    #TODO: return images flag
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str = "beam_profile"
    device: Screen
    image_processor: Optional[ImageProcessor] = ImageProcessor()
    beam_fit: ImageFit = ImageProjectionFit()
    fit_profile: bool = True

    def measure(self, n_shots: int = 1) -> dict:
        """
        Measurement function that takes in n_shots as argument
        where n_shots is the number of image profiles
        we would like to measure. Invokes single_measure per shot,
        storing them in a dictionary sorted by shot number
        Then if self.fit_profile = True, fits the profile of the beam
        and concatenates results with the image dictionary sorted by
        shot number
        """
        images = []
        while len(images) < n_shots:
            images.append(self.device.image)
            # TODO: need to add a wait statement in here for images to update

        processed_images = [
            self.image_processor.auto_process(image) for image in images
        ]

        if self.fit_profile:
            rms_sizes = []
            centroids = []
            total_intensities = []
            for image in processed_images:
                fit_result = self.beam_fit.fit_image(image)
                rms_sizes.append(
                    np.array(fit_result.rms_size) * self.device.resolution
                )  # units of microns
                centroids.append(np.array(fit_result.centroid) * self.device.resolution)
                total_intensities.append(fit_result.total_intensity)

        return ScreenBeamProfileMeasurementResult(
            raw_images=images,
            processed_images=processed_images,
            rms_sizes=rms_sizes or None,
            centroids=centroids or None,
            total_intensities=total_intensities or None,
            metadata=self.model_dump(),
        )
