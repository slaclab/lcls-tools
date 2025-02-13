import warnings
import numpy as np
from xopt import Xopt, Evaluator, VOCS
from xopt.generators.bayesian import UpperConfidenceBoundGenerator
from xopt.utils import get_local_region
from xopt.numerical_optimizer import GridOptimizer
from lcls_tools.common.measurements.emittance_measurement import QuadScanEmittance
from lcls_tools.common.image.roi import CircularROI, ROI
from typing import Optional
from lcls_tools.common.image.fit import ImageFitResult

from pydantic import PositiveInt, field_validator

from lcls_tools.common.measurements.screen_profile import ScreenBeamProfileMeasurementResult, ScreenBeamProfileMeasurement


def calculate_bounding_box_coordinates(
    screen_measurement_result: ScreenBeamProfileMeasurementResult, n_stds: float
) -> np.ndarray:
    """
    Calculate the corners of a bounding box given the fit results.

    Parameters
    ----------
    fit_result : ImageFitResult
        The fit results.
    n_stds : float
        Number of standard deviations to use for the bounding box.

    Returns
    -------
    np.ndarray
        The calculated bounding box coordinates.
    """
    rms_size = np.mean(screen_measurement_result.rms_sizes, axis=0)
    centroid = np.mean(screen_measurement_result.centroids, axis=0)
    return np.array(
        [
            -1 * rms_size * n_stds / 2 + centroid,
            rms_size * n_stds / 2 + centroid,
            np.array((-1, 1)) * rms_size * n_stds / 2 + centroid,
            np.array((1, -1)) * rms_size * n_stds / 2 + centroid,
        ]
    )


def calculate_bounding_box_penalty(
    roi: ROI, fit_result: ImageFitResult, n_stds: float = 2.0
) -> float:
    """
    Calculate the penalty based on the maximum distance between the center of the ROI
    and the beam bounding box corners.

    Parameters
    ----------
    roi : ROI
        Region of interest, can be either CircularROI or ROI.
    fit_result : ImageFitResult
        The fit results from image fitting.
    n_stds : float, optional
        Number of standard deviations to use for the bounding box, default is 2.0.

    Returns
    -------
    float
        The calculated penalty value.

    Raises
    ------
    ValueError
        If the ROI type is not supported.
    """
    # calculate the corners of a bounding box given the fit results
    beam_bbox_coords = calculate_bounding_box_coordinates(fit_result, n_stds=n_stds)

    if isinstance(roi, CircularROI):
        roi_radius = roi.radius[0]
    elif isinstance(roi, ROI):
        roi_radius = np.min(np.array(roi.extent) / 2)
    else:
        raise ValueError(f"ROI type {type(roi)} is not supported for ")

    roi_center = roi.center

    # calculate the max distance from the center of the ROI to the corner of the bounding box
    max_distance = np.max(
        np.array([np.linalg.norm(roi_center - corner) for corner in beam_bbox_coords])
    )

    return max_distance - roi_radius


class MLQuadScanEmittance(QuadScanEmittance):
    scan_values: Optional[list[float]] = None
    bounding_box_factor: float = 2.0
    n_initial_samples: PositiveInt = 3
    n_iterations: PositiveInt = 5
    max_k_ranges: Optional[list[float]] = None
    xopt_object: Optional[Xopt] = None

    @field_validator("beamsize_measurement", mode="after")
    def validate_beamsize_measurement(cls, v, info):
        # check to make sure the the beamsize measurement screen has a region of interest
        # (also requires ScreenBeamProfileMeasurement)
        if not isinstance(v, ScreenBeamProfileMeasurement):
            raise ValueError(
                "Beamsize measurement must be a ScreenBeamProfileMeasurement for MLQuadScanEmittance"
            )

        # check to make sure the the beamsize measurement screen has a region of interest
        if not isinstance(v.image_processor.roi, ROI):
            raise ValueError(
                "Beamsize measurement screen must have a region of interest"
            )
        return v

    def perform_beamsize_measurements(self):
        """
        Run BO-based exploration of the quadrupole strength to get beamsize measurements
        """
        # define the optimization problem
        k_range = self.max_k_ranges if self.max_k_ranges is not None else [-10, 10]
        vocs = VOCS(
            variables={"k": k_range},
            objectives={"x_rms_px": "MINIMIZE"},
            constraints={"bb_penalty": ["LESS_THAN", 0.0]},
        )

        scan_values = []

        def evaluate(inputs):
            # set quadrupole strength
            self.magnet.bctrl = inputs["k"]
            scan_values.append(inputs["k"])

            # make beam size measurement
            self.measure_beamsize()
            fit_result = self._info[-1]

            # calculate bounding box penalty
            bb_penalty = calculate_bounding_box_penalty(
                self.beamsize_measurement.image_processor.roi,
                fit_result,
            )

            # collect results
            results = {
                "bb_penalty": bb_penalty,
                "x_rms_px": fit_result.rms_sizes[:, 0],
                "y_rms_px": fit_result.rms_sizes[:, 1],
            }

            return results

        evaluator = Evaluator(function=evaluate)

        # ignore warnings from UCB generator and Xopt
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            generator = UpperConfidenceBoundGenerator(
                vocs=vocs,
                beta=100,
                numerical_optimizer=GridOptimizer(n_grid_points=50),
                n_interpolate_points=5,
                n_monte_carlo_samples=64,
            )

            X = Xopt(vocs=vocs, evaluator=evaluator, generator=generator)

            # get local region around current value and make some samples
            local_region = get_local_region({"k": self.magnet.bctrl}, vocs)
            X.random_evaluate(self.n_initial_samples, custom_bounds=local_region)

            # run iterations for x -- ignore warnings from UCB generator
            for i in range(self.n_iterations):
                X.step()

            # run iterations for y
            new_vocs = VOCS(
                variables={"k": k_range},
                objectives={"y_rms_px": "MINIMIZE"},
                constraints={"bb_penalty": ["LESS_THAN", 0.0]},
            )

                
            X.vocs = new_vocs
            X.generator.vocs = new_vocs

            for i in range(self.n_iterations):
                X.step()

        self.scan_values = scan_values

        self.xopt_object = X
