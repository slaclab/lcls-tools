import warnings
from abc import ABC, abstractmethod
from typing import Optional

import numpy as np
from numpy import ndarray
from pydantic import BaseModel, ConfigDict, PositiveFloat

from lcls_tools.common.data.fit.method_base import MethodBase
from lcls_tools.common.data.fit.methods import GaussianModel
from lcls_tools.common.data.fit.projection import ProjectionFit
from lcls_tools.common.image.processing import ImageProcessor


class ImageFit(BaseModel, ABC):
    """
    Abstract class for determining beam properties from an image
    """
    image_processor: Optional[ImageProcessor] = ImageProcessor()
    min_log_intensity: Optional[float] = 4.0
    bounding_box_half_width: Optional[PositiveFloat] = 3.0
    apply_bounding_box_constraint: Optional[bool] = False

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def fit_image(self, image: ndarray) -> dict:
        """
        Public method to determine beam properties from an image, including initial
        image processing, internal image fitting method, and image validation.

        """
        image = self.image_processor.auto_process(image)
        fit_result = self._fit_image(image)
        fit_result = self._validate_results(image, fit_result)
        fit_result.update({"processed_image": image})
        return fit_result

    @abstractmethod
    def _fit_image(self, image: ndarray) -> dict:
        """
        Private image fitting method to be overwritten by subclasses. Expected to
        return a dictonary containing the following keys:
        - centroid: 2 element array containing centroid x/y values
        - rms_sizes: 2 element array containing x/y RMS beamsize values
        - total_intensity: total pixel intensity
        """
        ...

    def _validate_results(self, image: ndarray, fit_results: dict) -> dict:
        """
        determine if the image satisfies specified constraints, including:
        - minimum intensity threshold reached
        - beam is fully inside the image boundary (if not, RMS measurements are invalid)

        If the beam image does not satisfy these constraints Nan's are returned for
        beamsize properties and a warning is raised.
        """
        if np.log10(fit_results["total_intensity"]) < self.min_log_intensity:
            # TODO: character count is really not liking this one line
            warnings.warn(
                (
                    "log10 image intensity"
                    + f"{np.log10(fit_results['total_intensity'])}"
                    + "below threshold"
                )
            )
            fit_results["centroid"] = np.array((np.Nan, np.Nan))
            fit_results["rms_sizes"] = np.array((np.Nan, np.Nan))
            fit_results["bb_penalty"] = np.Nan

        else:
            centroid = fit_results["centroid"]
            sizes = fit_results["rms_sizes"]

            if np.all(~np.isnan(np.stack((centroid, sizes)))):
                # get bounding box penalty
                bounding_box_penalty = self._calculate_bounding_box_penalty(
                    image, centroid, sizes,
                )
                fit_results["bb_penalty"] = bounding_box_penalty

                # set results to none if the beam extends beyond the roi
                # and the bounding box constraint is active
                if bounding_box_penalty > 0 and self.apply_bounding_box_constraint:
                    fit_results["centroid"] = np.array((np.Nan, np.Nan))
                    fit_results["rms_sizes"] = np.array((np.Nan, np.Nan))

                    warnings.warn(
                        f"Beam bounding box is outside the image, penalty value: "
                        f"{bounding_box_penalty}"
                    )

            else:
                fit_results["centroid"] = np.array((np.Nan, np.Nan))
                fit_results["rms_sizes"] = np.array((np.Nan, np.Nan))
                fit_results["bb_penalty"] = np.Nan

                warnings.warn(
                    "Image fits returned Nan values"
                )

        return fit_results

    def _calculate_bounding_box_penalty(self, image, centroid, sizes):
        """
        Calculate bounding box penalty which determines if the beam bounding box is
        inside or outside the image. Value is < 0 if inside and > 0 if outside /
        partically outside.

        Note: bounding box penalty function should be continuous to be an effective
        constraint. See https://www.mdpi.com/2410-390X/7/3/29 for details.
        """
        n_stds = self.bounding_box_half_width

        bounding_box_corner_pts = np.array(
            (
                centroid - n_stds * sizes,
                centroid + n_stds * sizes,
                centroid - n_stds * sizes * np.array((-1, 1)),
                centroid + n_stds * sizes * np.array((-1, 1)),
            )
        )

        if self.image_processor.roi is not None:
            roi_radius = self.image_processor.roi.radius
        else:
            roi_radius = np.min(np.array(image.shape) / 1.5)
            # TODO: maybe need to change this ^^^

        # This is a check whether or not the beamspot is within
        # the bounding box.
        temp = bounding_box_corner_pts - np.array((roi_radius, roi_radius))
        distances = np.linalg.norm(temp, axis=1)
        bounding_box_penalty = np.max(distances) - roi_radius

        return bounding_box_penalty


class ImageProjectionFit(ImageFit):
    """
    Image fitting class that gets the beam size and location by independently fitting
    the x/y projections. The default configuration uses a Gaussian fitting of the
    profile with prior distributions placed on the model parameters.
    """
    projection_fit_method: Optional[MethodBase] = GaussianModel(use_priors=True)
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _fit_image(self, image: ndarray) -> dict:
        x_projection = np.array(np.sum(image, axis=0))
        y_projection = np.array(np.sum(image, axis=1))

        proj_fit = ProjectionFit(model=self.projection_fit_method)

        x_parameters = proj_fit.fit_projection(x_projection)
        y_parameters = proj_fit.fit_projection(y_projection)

        results = {
            "centroid": np.array((x_parameters["mean"], y_parameters["mean"])),
            "rms_sizes": np.array((x_parameters["sigma"], y_parameters["sigma"])),
            "total_intensity": image.sum(),
            "projection_fit_parameters": {"x": x_parameters, "y": y_parameters},
        }

        return results
