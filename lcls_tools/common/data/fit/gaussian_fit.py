import numpy as np
from pydantic import BaseModel, ConfigDict, PositiveFloat
from typing import Optional
from lcls_tools.common.data.fit.projection import ProjectionFit
from lcls_tools.common.image.processing import ImageProcessor


class GaussianFit(BaseModel):
    # should rename to BeamsizeEvaluator or something ?
    """
    Gaussian Fitting class that takes in a fitting tool (with method),
    ImageProcessor, and Image and returns the beamsize and position.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    processor: ImageProcessor = ImageProcessor()
    fit: ProjectionFit = ProjectionFit()
    min_log_intensity: float = 4.0
    bounding_box_half_width: PositiveFloat = 3.0
    apply_bounding_box_constraint: bool = True
    image: Optional[np.ndarray] = None

    @property
    def beamsize(self):
        beamspot_chars = self.gaussian_fit(self.image)
        beamsize = self.calculate_beamsize(beamspot_chars)
        return beamsize

    def gaussian_fit(self, image):
        self.processor.auto_process(image)
        x_proj, y_proj = self.get_projections(image)
        x_parameters = self.fit.fit_projection(x_proj)
        y_parameters = self.fit.fit_projection(y_proj)

        return {
            "centroid": np.array((x_parameters["mean"], y_parameters["mean"])),
            "rms_sizes": np.array((x_parameters["sigma"], y_parameters["sigma"])),
            "total_intensity": image.sum(),
        }

    def get_projections(self, image):
        x_projection = np.array(np.sum(image, axis=0))
        y_projection = np.array(np.sum(image, axis=1))
        return x_projection, y_projection

    def calculate_beamsize(self, beamspot_chars: dict):
        """
        Conditional beamsize calculation:
        if condition1 (total_intensity is to small): then return NULL result.
        else: do beamsize calculation and check that the beamspot is
        within the ROI
        """
        if np.log10(beamspot_chars["total_intensity"]) < self.min_log_intensity:
            # TODO: character count is really not liking this one line
            print(
                (
                    "log10 image intensity"
                    + f"{np.log10(beamspot_chars['total_intensity'])}"
                    + "below threshold"
                )
            )
            result = {
                "Cx": np.NaN,
                "Cy": np.NaN,
                "Sx": np.NaN,
                "Sy": np.NaN,
                "bb_penalty": np.NaN,
                "total_intensity": beamspot_chars["total_intensity"],
            }
            return result
        else:
            centroid = beamspot_chars["centroid"]
            sizes = beamspot_chars["rms_sizes"]

            if np.all(~np.isnan(np.stack((centroid, sizes)))):
                # get beam region bounding box
                n_stds = self.bounding_box_half_width

                bounding_box_corner_pts = np.array(
                    (
                        centroid - n_stds * sizes,
                        centroid + n_stds * sizes,
                        centroid - n_stds * sizes * np.array((-1, 1)),
                        centroid + n_stds * sizes * np.array((-1, 1)),
                    )
                )

                if self.processor.roi is not None:
                    roi_radius = self.processor.roi.radius
                else:
                    roi_radius = np.min(np.array(self.image.shape) / 1.5)
                    # TODO: maybe need to change this ^^^

                # This is a check whether or not the beamspot is within
                # the bounding box.
                temp = bounding_box_corner_pts - np.array((roi_radius, roi_radius))
                distances = np.linalg.norm(temp, axis=1)
                bounding_box_penalty = np.max(distances) - roi_radius

                result = {
                    "Cx": centroid[0],
                    "Cy": centroid[1],
                    "Sx": sizes[0],
                    "Sy": sizes[1],
                    "bb_penalty": bounding_box_penalty,
                    "total_intensity": beamspot_chars["total_intensity"],
                }

                # set results to none if the beam extends beyond the roi
                # and the bounding box constraint is active
                if bounding_box_penalty > 0 and self.apply_bounding_box_constraint:
                    for name in ["Cx", "Cy", "Sx", "Sy"]:
                        result[name] = np.NaN

            else:
                result = {
                    "Cx": np.NaN,
                    "Cy": np.NaN,
                    "Sx": np.NaN,
                    "Sy": np.NaN,
                    "bb_penalty": np.NaN,
                    "total_intensity": beamspot_chars["total_intensity"],
                }

            return result
