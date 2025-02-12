from unittest import TestCase
from unittest.mock import patch, Mock, MagicMock

import numpy as np
import torch
from cheetah import Segment, Quadrupole, Drift, ParameterBeam

import matplotlib.pyplot as plt
from lcls_tools.common.devices.magnet import Magnet, MagnetMetadata
from lcls_tools.common.devices.reader import create_magnet
from lcls_tools.common.devices.screen import Screen
from lcls_tools.common.image.fit import ImageFitResult
from lcls_tools.common.measurements.screen_profile import ScreenBeamProfileMeasurement
from lcls_tools.common.image.roi import CircularROI, ROI

from lcls_tools.common.ml.automatic_emittance import (
MLQuadScanEmittance, calculate_bounding_box_penalty, calculate_bounding_box_coordinates
)



class MockBeamline:
    def __init__(self):
        """ create mock beamline, powered by cheetah"""
        self.beamline = Segment([
            Quadrupole(name=f"Q0", length=torch.tensor(0.1)),
            Drift(length=torch.tensor(1.0))
        ])

        self.magnet = MagicMock(spec=Magnet)

        # add a property to the magnet to control the quad strength
        type(self.magnet).bctrl = property(self.get_bctrl, self.set_bctrl)

        self.magnet.metadata = MagnetMetadata(
            area="test",
            beam_path=["test"],
            sum_l_meters=None,
            l_eff=0.1
        )

        self.screen_resolution = 1.0 # resolution of the screen in um / px
        self.beamsize_measurement = MagicMock(spec=ScreenBeamProfileMeasurement)
        self.beamsize_measurement.device = MagicMock(spec=Screen)
        self.beamsize_measurement.device.resolution = self.screen_resolution
        self.beamsize_measurement.device.image_processor = MagicMock()
        self.beamsize_measurement.device.image_processor.roi = CircularROI(center=[0, 0], radius=1000)
        self.beamsize_measurement.measure = MagicMock(
            side_effect=self.get_beamsize_measurement
        )

    def get_bctrl(self, *args):
        return self.beamline.Q0.k1.numpy()
        
    def set_bctrl(self, *args):
        # NOTE: this is a bit of a hack since the first argument is the MagicMock object
        self.beamline.Q0.k1 = torch.tensor(args[1])

    def get_beamsize_measurement(self, *args):
        """ define a mock beamsize measurement for the ScreenBeamProfileMeasurement -- returns image fit result in pixels"""
        incoming_beam = ParameterBeam.from_twiss(
            beta_x=torch.tensor(5.0),
            alpha_x=torch.tensor(0.0),
            emittance_x=torch.tensor(1e-8),
            beta_y=torch.tensor(5.0),
            alpha_y=torch.tensor(0.0),
            emittance_y=torch.tensor(2e-8),
        )
        outgoing_beam = self.beamline.track(incoming_beam)

        results = MagicMock(ImageFitResult)
        results.rms_size = [
            int(outgoing_beam.sigma_x*1e6 / self.screen_resolution), int(outgoing_beam.sigma_y*1e6 / self.screen_resolution)
        ]
        results.centroid = [0, 0]

        return {"fit_results": [results]}

class AutomaticEmittanceMeasurementTest(TestCase):
    def setUp(self) -> None:
        self.options = [
            "TRIM",
            "PERTURB",
            "BCON_TO_BDES",
            "SAVE_BDES",
            "LOAD_BDES",
            "UNDO_BDES",
            "DAC_ZERO",
            "CALIB",
            "STDZ",
            "RESET",
            "TURN_OFF",
            "TURN_ON",
            "DEGAUSS",
        ]
        self.ctrl_options_patch = patch("epics.PV.get_ctrlvars", new_callable=Mock)
        self.mock_ctrl_options = self.ctrl_options_patch.start()
        self.mock_ctrl_options.return_value = {"enum_strs": tuple(self.options)}
        self.magnet_collection = create_magnet(area="GUNB")
        return super().setUp()

    def test_automatic_emit_scan_with_mocked_beamsize_measurement(self):
        """
        Test to verify correct emittance calculation based on data generated from a
        basic cheetah simulation of a quad and drift element
        """
        mock_beamline = MockBeamline()

        rmat = np.array([[[1, 1.0], [0, 1]], [[1, 1.0], [0, 1]]])
        design_twiss = {
            "beta_x": 5.0,
            "alpha_x": 0.0,
            "beta_y": 1.0,
            "alpha_y": -1.0,
        }

        # Instantiate the QuadScanEmittance object
        quad_scan = MLQuadScanEmittance(
            energy=1e9 * 299.792458 / 1e3,
            magnet=mock_beamline.magnet,
            beamsize_measurement=mock_beamline.beamsize_measurement,
            n_measurement_shots=1,
            wait_time=1e-3,
            rmat=rmat,
            design_twiss=design_twiss,
            n_initial_samples=3,
            n_iterations=5,
            max_k_ranges=[-20,20],
        )

        # Call the measure method
        results = quad_scan.measure()

        quad_scan.xopt_object.data.plot(x="k", y=["x_rms_px","y_rms_px"], style="+")
        quad_scan.xopt_object.data.plot(x="k", y=["bb_penalty"], style="+")

        print(results["emittance"])

        plt.show()

        # Assertions
        assert "x_rms" in results
        assert "y_rms" in results
        assert len(results["x_rms"]) == len(quad_scan.scan_values)
        assert len(results["y_rms"]) == len(quad_scan.scan_values)

        # check resulting calculations against cheetah simulation ground truth
        assert np.allclose(
            results["emittance"],
            np.array([1.0e-2, 1.0e-2]).reshape(2, 1),
        )
        assert np.allclose(results["beam_matrix"], np.array(
            [[5.0e-2, -5.0e-2, 5.2e-2],
             [0.3, -0.3, 0.33333328]]
        ))
        assert np.allclose(results["BMAG"][:, 4], 1.0)
        
    def test_calculate_bounding_box_coordinates(self):
        # Mock ImageFitResult
        fit_result = MagicMock()
        fit_result.rms_size = [2, 4]
        fit_result.centroid = [1, 1]

        # Expected bounding box coordinates
        expected_bbox_coords = [
            np.array([0, -1]),
            np.array([2, 3]),
            np.array([0, 3]),
            np.array([2, -1])
        ]

        # Calculate bounding box coordinates
        bbox_coords = calculate_bounding_box_coordinates(fit_result, n_stds=1)

        # Assertions
        for coord, expected_coord in zip(bbox_coords, expected_bbox_coords):
            assert np.allclose(coord, expected_coord)

    def test_calculate_bounding_box_penalty(self):
            fit_result = MagicMock()
            fit_result.rms_size = [2, 4]
            fit_result.centroid = [1, 1]

            # test usage of CircularROI
            roi = CircularROI(center=[0, 0], radius=1)
            penalty = calculate_bounding_box_penalty(roi, fit_result)
            assert penalty == 1.0 - np.linalg.norm(roi.center - np.array((3.,5.)))

            # test usage of ROI
            roi = ROI(center=[0, 0], extent=[2, 2])
            beam_bbox_coords = np.array([0,0])
            penalty = calculate_bounding_box_penalty(roi, fit_result)
            assert penalty == 1.0 - np.linalg.norm(roi.center - np.array((3.,5.)))

            # test usage of unsupported ROI type
            roi = "unsupported"
            with self.assertRaises(ValueError):
                calculate_bounding_box_penalty(roi, fit_result)
