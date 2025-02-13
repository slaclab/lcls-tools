from unittest import TestCase
from unittest.mock import patch, Mock, MagicMock

import numpy as np
import torch
from cheetah import Segment, Quadrupole, Drift, ParameterBeam

from lcls_tools.common.devices.magnet import Magnet, MagnetMetadata
from lcls_tools.common.devices.reader import create_magnet
from lcls_tools.common.devices.screen import Screen
from lcls_tools.common.frontend.plotting.emittance import plot_quad_scan_result
from lcls_tools.common.measurements.emittance_measurement import (
    EmittanceMeasurementResult,
)
from lcls_tools.common.measurements.screen_profile import (
    ScreenBeamProfileMeasurement,
    ScreenBeamProfileMeasurementResult,
)
from lcls_tools.common.image.roi import CircularROI, ROI

from lcls_tools.common.ml.automatic_emittance import (
    MLQuadScanEmittance,
    calculate_bounding_box_penalty,
    calculate_bounding_box_coordinates,
)


class MockBeamline:
    def __init__(self, initial_beam: ParameterBeam):
        """create mock beamline, powered by cheetah"""
        self.beamline = Segment(
            [
                Quadrupole(name="Q0", length=torch.tensor(0.1)),
                Drift(length=torch.tensor(1.0)),
            ]
        )

        self.magnet = MagicMock(spec=Magnet)

        # add a property to the magnet to control the quad strength
        type(self.magnet).bctrl = property(self.get_bctrl, self.set_bctrl)

        self.magnet.metadata = MagnetMetadata(
            area="test", beam_path=["test"], sum_l_meters=None, l_eff=0.1
        )

        self.screen_resolution = 1.0  # resolution of the screen in um / px
        self.beamsize_measurement = MagicMock(spec=ScreenBeamProfileMeasurement)
        self.beamsize_measurement.device = MagicMock(spec=Screen)
        self.beamsize_measurement.device.resolution = self.screen_resolution
        self.beamsize_measurement.image_processor = MagicMock()
        self.beamsize_measurement.image_processor.roi = CircularROI(
            center=[0, 0], radius=1000
        )
        self.beamsize_measurement.measure = MagicMock(
            side_effect=self.get_beamsize_measurement
        )

        self.initial_beam = initial_beam

    def get_bctrl(self, *args):
        return self.beamline.Q0.k1.numpy()

    def set_bctrl(self, *args):
        # NOTE: this is a bit of a hack since the first argument is the MagicMock object
        self.beamline.Q0.k1 = torch.tensor(args[1])

    def get_beamsize_measurement(self, *args):
        """define a mock beamsize measurement for the
        ScreenBeamProfileMeasurement -- returns image fit result in pixels"""
        outgoing_beam = self.beamline.track(self.initial_beam)

        sigma_x = (
            outgoing_beam.sigma_x * 1e6 / self.screen_resolution
            + 5.0 * np.random.randn(args[0])
        )
        sigma_y = (
            outgoing_beam.sigma_y * 1e6 / self.screen_resolution
            + 5.0 * np.random.randn(args[0])
        )

        result = MagicMock(ScreenBeamProfileMeasurementResult)
        result.rms_sizes = np.stack([sigma_x, sigma_y]).T
        result.centroids = np.zeros((args[0], 2))

        return result


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
        rmat = np.array([[[1, 1.0], [0, 1]], [[1, 1.0], [0, 1]]])
        design_twiss = {
            "beta_x": 0.2452,
            "alpha_x": -0.1726,
            "beta_y": 0.5323,
            "alpha_y": -1.0615,
        }

        # run test with and without design_twiss
        for design_twiss_ele in [None, design_twiss]:
            for n_shots in [1, 3]:
                initial_beam = ParameterBeam.from_twiss(
                    beta_x=torch.tensor(5.0),
                    alpha_x=torch.tensor(5.0),
                    emittance_x=torch.tensor(1e-8),
                    beta_y=torch.tensor(3.0),
                    alpha_y=torch.tensor(3.0),
                    emittance_y=torch.tensor(1e-7),
                )

                mock_beamline = MockBeamline(initial_beam)

                # Instantiate the QuadScanEmittance object
                quad_scan = MLQuadScanEmittance(
                    energy=1e9 * 299.792458 / 1e3,
                    magnet=mock_beamline.magnet,
                    beamsize_measurement=mock_beamline.beamsize_measurement,
                    n_measurement_shots=n_shots,
                    wait_time=1e-3,
                    rmat=rmat,
                    design_twiss=design_twiss_ele,
                    n_initial_samples=3,
                    n_iterations=5,
                    max_k_ranges=[-10, 10],
                )

                # Call the measure method
                result = quad_scan.measure()

                plot_quad_scan_result(result)
                import matplotlib.pyplot as plt

                plt.show()

                # Check the results
                assert isinstance(result, EmittanceMeasurementResult)
                assert hasattr(result, "x_rms")
                assert hasattr(result, "y_rms")
                assert len(result.x_rms) == len(quad_scan.scan_values)
                assert len(result.y_rms) == len(quad_scan.scan_values)

                # check resulting calculations against cheetah simulation ground truth
                print(result.emittance)
                assert np.allclose(
                    result.emittance,
                    np.array([1.0e-2, 1.0e-1]).reshape(2, 1),
                    rtol=1e-1,
                )
                assert np.allclose(
                    result.beam_matrix,
                    np.array([[5.0e-2, -5.0e-2, 5.2e-2], [0.3, -0.3, 0.33333328]]),
                    rtol=1e-1,
                )

    def test_calculate_bounding_box_coordinates(self):
        # Mock ImageFitResult
        fit_result = MagicMock()
        fit_result.rms_sizes = np.array([2, 4]).reshape(1, 2)
        fit_result.centroids = np.array([1, 1]).reshape(1, 2)

        # Expected bounding box coordinates
        expected_bbox_coords = [
            np.array([0, -1]),
            np.array([2, 3]),
            np.array([0, 3]),
            np.array([2, -1]),
        ]

        # Calculate bounding box coordinates
        bbox_coords = calculate_bounding_box_coordinates(fit_result, n_stds=1)

        # Assertions
        for coord, expected_coord in zip(bbox_coords, expected_bbox_coords):
            assert np.allclose(coord, expected_coord)

    def test_calculate_bounding_box_penalty(self):
        fit_result = MagicMock()
        fit_result.rms_sizes = np.array([2, 4]).reshape(1, 2)
        fit_result.centroids = np.array([1, 1]).reshape(1, 2)

        # test usage of CircularROI
        roi = CircularROI(center=[0, 0], radius=1)
        penalty = calculate_bounding_box_penalty(roi, fit_result)
        assert penalty == np.linalg.norm(roi.center - np.array((3.0, 5.0))) - 1.0

        # test usage of ROI
        roi = ROI(center=[0, 0], extent=[2, 2])
        penalty = calculate_bounding_box_penalty(roi, fit_result)
        assert penalty == np.linalg.norm(roi.center - np.array((3.0, 5.0))) - 1.0

        # test usage of unsupported ROI type
        roi = "unsupported"
        with self.assertRaises(ValueError):
            calculate_bounding_box_penalty(roi, fit_result)
