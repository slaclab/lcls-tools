from lcls_tools.common.devices.screen import Screen
from lcls_tools.common.image.fit import ImageProjectionFit, ImageFit
from lcls_tools.common.image.processing import ImageProcessor
from pydantic import ConfigDict
from typing import Optional

from lcls_tools.common.measurements.utils import NDArrayAnnotatedType

from lcls_tools.common.measurements.beam_profile import (
    BeamProfileMeasurement,
    BeamProfileMeasurementResult,
)
import numpy as np


class ScreenBeamProfileMeasurementResult(BeamProfileMeasurementResult):
    """
    Class that contains the results of a beam profile measurement

    Attributes
    ----------
    raw_images : ndarray
        Numpy array of raw images taken during the measurement
    processed_images : ndarray
        Numpy array of processed images taken during the measurement
    rms_sizes_all: ndarray
        Numpy array of rms sizes for all shots for each axis (um)

    Inherited Attributes
    ----------
    rms_sizes : ndarray
        Numpy array of rms sizes averaged over all shots in microns.
    centroids : ndarray
        Numpy array of centroids of the beam in microns.
    total_intensities : ndarray
        Numpy array of total intensities of the beam.
    metadata : Any
        Metadata information related to the measurement.

    """

    raw_images: NDArrayAnnotatedType
    processed_images: NDArrayAnnotatedType
    rms_sizes_all: NDArrayAnnotatedType

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
    measure: does multiple measurements and has an option to fit the image
             profiles
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    beam_profile_device: Screen
    n_shots: int = 1
    image_processor: Optional[ImageProcessor] = ImageProcessor()
    beam_fit: ImageFit = ImageProjectionFit()
    fit_profile: bool = True

    def measure(self) -> ScreenBeamProfileMeasurementResult:
        """
        Measurement takes self.n_shots number of images and stores them
        in a list, processes them, and if self.fit_profile = True,
        fits the profile of the beam for each image. The results are
        then returned in a ScreenBeamProfileMeasurementResult.
        """
        images = []
        while len(images) < self.n_shots:
            images.append(self.beam_profile_device.image)
            # TODO: need to add a wait statement in here for images to update

        processed_images, offsets = self.image_processor.process(
            images, return_offsets=True
        )

        if self.fit_profile:
            (
                rms_sizes_all,
                rms_sizes,
                centroids,
                total_intensities,
                signal_to_noise_ratios,
            ) = self.fit_data(processed_images, offsets)


        else:
            (
                rms_sizes_all,
                rms_sizes,
                centroids,
                total_intensities,
                signal_to_noise_ratios,
            ) = (None, None, None, None, None)

        return ScreenBeamProfileMeasurementResult(
            raw_images=images,
            processed_images=processed_images,
            rms_sizes_all=rms_sizes_all,
            rms_sizes=rms_sizes,
            centroids=centroids,
            total_intensities=total_intensities,
            signal_to_noise_ratios=signal_to_noise_ratios,
            metadata=self.model_dump(),
        )

    def fit_data(self, processed_images, offsets=None):
        """
        Fit the processed images and return the beam parameters

        Parameters
        ----------
        processed_images : ndarray
            Numpy array of processed images to be fitted
        offsets : ndarray, optional
            Offsets of the processed images with respect to the original images
            
        Returns
        -------
        rms_sizes_all : ndarray
            Numpy array of rms sizes for all shots for each axis (um)
        rms_sizes : ndarray
            Numpy array of rms sizes averaged over all shots in microns.
        centroids : ndarray
            Numpy array of centroids of the beam in microns.
        total_intensities : ndarray
            Numpy array of total intensities of the beam in arbitrary units.
        signal_to_noise_ratios : ndarray
            Numpy array of signal to noise ratios of the beam.
        """

        rms_sizes_all = []
        centroids_all = []
        total_intensities_all = []
        signal_to_noise_ratios_all = []

        # if not provided, set offsets to zero
        if offsets is None:
            offsets = 0.0

        for image in processed_images:
            fit_result = self.beam_fit.fit_image(image)
            rms_sizes_all.append(
                np.array(fit_result.rms_size)
            )
            centroids_all.append(
                np.array(fit_result.centroid)
            )
            total_intensities_all.append(fit_result.total_intensity)
            signal_to_noise_ratios_all.append(fit_result.signal_to_noise_ratio)

        rms_sizes = np.mean(rms_sizes_all, axis=0)
        centroids = np.mean(centroids_all + offsets, axis=0)

        # convert from pixels to microns
        rms_sizes_all = np.array(rms_sizes_all) * self.beam_profile_device.resolution
        rms_sizes = rms_sizes * self.beam_profile_device.resolution
        centroids = centroids * self.beam_profile_device.resolution

        total_intensities = np.mean(total_intensities_all, axis=0)
        signal_to_noise_ratios = np.mean(signal_to_noise_ratios_all, axis=0)

        return (
            rms_sizes_all,
            rms_sizes,
            centroids,
            total_intensities,
            signal_to_noise_ratios,
        )
