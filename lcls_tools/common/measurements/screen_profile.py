from lcls_tools.common.devices.screen import Screen
from lcls_tools.common.image.fit import ImageProjectionFit, ImageFit
from lcls_tools.common.image.processing import ImageProcessor
import numpy as np
from pydantic import (
    ConfigDict,
)
from typing import Optional

from lcls_tools.common.measurements.utils import NDArrayAnnotatedType

from lcls_tools.common.measurements.beam_profile import (
    BeamProfileMeasurement, 
    BeamProfileMeasurementResult,
)


class ScreenBeamProfileMeasurementResult(BeamProfileMeasurementResult):
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

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class ScreenBeamProfileMeasurement(BeamProfileMeasurement):
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
    beam_profile_device: Screen
    n_shots: int = 1
    image_processor: Optional[ImageProcessor] = ImageProcessor()
    beam_fit: ImageFit = ImageProjectionFit()
    fit_profile: bool = True

    def measure(self) -> ScreenBeamProfileMeasurementResult:
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
        while len(images) < self.n_shots:
            images.append(self.beam_profile_device.image)
            # TODO: need to add a wait statement in here for images to update

        processed_images = [
            self.image_processor.auto_process(image) for image in images
        ]

        if self.fit_profile:
            rms_sizes_all = []
            centroids_all = []
            total_intensities_all = []
            for image in processed_images:
                fit_result = self.beam_fit.fit_image(image)
                rms_sizes_all.append(
                    fit_result.rms_size * self.beam_profile_device.resolution
                )
                centroids_all.append(
                    fit_result.centroid * self.beam_profile_device.resolution
                )
                total_intensities_all.append(fit_result.total_intensity)
            rms_sizes = np.mean(np.array(rms_sizes_all), axis=0)
            centroids = np.mean(np.array(centroids_all), axis=0)
            total_intensities = np.mean(np.array(total_intensities_all), axis=0)

        return ScreenBeamProfileMeasurementResult(
            raw_images=images,
            processed_images=processed_images,
            rms_sizes=rms_sizes or None,
            centroids=centroids or None,
            total_intensities=total_intensities or None,
            metadata=self.model_dump(),
        )
