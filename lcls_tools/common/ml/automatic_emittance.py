import numpy as np
from xopt import Xopt, Evaluator, VOCS
from xopt.generators.bayesian import UpperConfidenceBoundGenerator
from xopt.utils import get_local_region
from xopt.numerical_optimizer import GridOptimizer
from lcls_tools.common.measurements.emittance_measurement import QuadScanEmittance
from lcls_tools.common.image.roi import CircularROI, ROI
from typing import Optional
from lcls_tools.common.image.fit import ImageFitResult

from pydantic import validate_field

from lcls_tools.common.measurements.screen_profile import ScreenBeamProfileMeasurement

def calculate_bounding_box_coordinates(fit_result: ImageFitResult, n_stds: float) -> np.ndarray:
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
    return np.array([
        -1*np.array(fit_result.rms_size)*n_stds / 2 + np.array(fit_result.centroid),
        np.array(fit_result.rms_size)*n_stds / 2 + np.array(fit_result.centroid),
        np.array((-1,1))*np.array(fit_result.rms_size)*n_stds / 2 + np.array(fit_result.centroid),
        np.array((1,-1))*np.array(fit_result.rms_size)*n_stds / 2 + np.array(fit_result.centroid)
    ])

def calculate_bounding_box_penalty(roi: ROI, fit_result: ImageFitResult, n_stds:float=2.0) -> float:
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
    beam_bbox_coords = calculate_bounding_box_coordinates(
        fit_result, n_stds=n_stds
        )

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

    return roi_radius - max_distance


class MLQuadScanEmittance(QuadScanEmittance):
    scan_values: Optional[list[float]] = None
    bounding_box_factor: float = 2.0

    @validate_field("beamsize_measurement", mode="after")
    def validate_beamsize_measurement(cls, v, info):
        # check to make sure the the beamsize measurement screen has a region of interest 
        # (also requires ScreenBeamProfileMeasurement)
        if not isinstance(v["measurement"], ScreenBeamProfileMeasurement):
            raise ValueError("Beamsize measurement must be a ScreenBeamProfileMeasurement for MLQuadScanEmittance")

        # check to make sure the the beamsize measurement screen has a region of interest
        if not isinstance(v["measurement"].device.image_processor.roi, ROI):
            raise ValueError("Beamsize measurement screen must have a region of interest")
        return v

    def perform_beamsize_measurements(self):
        """
        Run BO-based exploration of the quadrupole strength to get beamsize measurements
        """
        vocs = VOCS(
            variables={"k": [-10, 10]},
            objectives={"total_size": "MINIMIZE"},
            constraints={"bb_penalty": ["LESS_THAN", 0.0]}
        )

        def evaluate(inputs):
            # set quadrupole strength
            self.magnet.bctrl = inputs["k"]

            # make beam size measurement
            self.measure_beamsize()
            fit_results = self._info[-1]

            # calculate bounding box penalty
            bb_penalty = calculate_bounding_box_penalty(
                self.beamsize_measurement.image_processor.roi,
                fit_results,

            )

            # collect results
            results = {
                "bb_penalty": bb_penalty,
                "x_rms": fit_results.rms_size[0],
                "y_rms": fit_results.rms_size[1],
                "total_size": np.linalg.norm(fit_results.rms_size)
            }

            return results

        evaluator = Evaluator(function=evaluate)

        generator = UpperConfidenceBoundGenerator(
            vocs=vocs, beta=10,
            numerical_optimizer=GridOptimizer(n_grid_points=50)
        )

        X = Xopt(vocs=vocs, evaluator=evaluator, generator=generator)

        # get local region around current value and make some samples
        local_region = get_local_region({"k": self.magnet.bctrl}, vocs)
        X.random_evaluate(3, custom_bounds=local_region)

        # run iterations
        for i in range(5):
            X.step()

        self.scan_values = X.data["k"].tolist()
