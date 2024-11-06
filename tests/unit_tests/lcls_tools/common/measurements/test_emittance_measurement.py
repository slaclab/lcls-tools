from unittest import TestCase
from unittest.mock import patch, Mock
import numpy as np

from lcls_tools.common.devices.reader import create_magnet
from lcls_tools.common.measurements.emittance_measurement import QuadScanEmittance
from lcls_tools.common.measurements.screen_profile import ScreenBeamProfileMeasurement


class EmittanceMeasurementTest(TestCase):
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

    @patch("lcls_tools.common.measurements.emittance_measurement.get_optics")
    @patch("lcls_tools.common.measurements.emittance_measurement.compute_emit_bmag")
    @patch(
        "lcls_tools.common.devices.magnet.Magnet.is_bact_settled",
        new_callable=Mock,
    )
    @patch("epics.PV.put", new_callable=Mock)
    @patch("lcls_tools.common.devices.magnet.Magnet.trim", new_callable=Mock)
    def test_quad_scan(self, mock_trim, mock_put, mock_bact_settle, mock_compute_emit_bmag, mock_get_optics):
        """Test quad scan emittance measurement"""
        rmat_mock = np.array([
            [2.52667046e+00, 4.21817732e+00, 0.00000000e+00, 0.00000000e+00, 1.68300181e-24, -1.03180226e-24],
            [3.67866188e-01, 1.00991619e+00, 0.00000000e+00, 0.00000000e+00, 3.83090380e-25, -6.94484939e-25],
            [0.00000000e+00, 0.00000000e+00, -5.16660571e-01, 4.13618612e+00, 0.00000000e+00, 0.00000000e+00],
            [0.00000000e+00, 0.00000000e+00, -3.65446389e-01, 9.90116596e-01, 0.00000000e+00, 0.00000000e+00],
            [3.50100414e-25, -2.58633175e-25, 0.00000000e+00, 0.00000000e+00, 1.00000000e+00, 5.98659826e-05],
            [-1.07994072e-24, -1.25510334e-25, 0.00000000e+00, 0.00000000e+00, -4.92137957e-08, 1.00000000e+00]
        ])
        twiss_dtype = np.dtype([('s', 'float32'), ('z', 'float32'), ('length', 'float32'),
                                ('p0c', 'float32'), ('alpha_x', 'float32'), ('beta_x', 'float32'),
                                ('eta_x', 'float32'), ('etap_x', 'float32'), ('psi_x', 'float32'),
                                ('alpha_y', 'float32'), ('beta_y', 'float32'), ('eta_y', 'float32'),
                                ('etap_y', 'float32'), ('psi_y', 'float32')])
        twiss_mock = np.array(
            [(11.977644, 2027.7198, 0.054, 1.3499904e+08, 3.9888208, 5.5319443,
              -6.172034e-18, 1.2438233e-17, 5.954487, 0.01185468, 5.314966, 0., 0., 3.5827537)],
            dtype=twiss_dtype
        )
        mock_get_optics.return_value = (rmat_mock, twiss_mock)
        mock_compute_emit_bmag.return_value = (1.5e-9, 1.5, None, None)
        mock_bact_settle.return_value = True
        beamline = "SC_DIAG0"
        energy = 3.0e9
        magnet_name = "CQ01B"
        magnet_length = 1.0
        scan_values = [-6.0, -3.0, 0.0]
        profmon_measurement = Mock(spec=ScreenBeamProfileMeasurement)
        profmon_measurement.device = Mock()
        profmon_measurement.device.name = "YAG01B"
        profmon_measurement.measure.return_value = {
            "Cx": [0.0],
            "Cy": [0.0],
            "Sx": [50.0],
            "Sy": [50.0],
            "bb_penalty": [0.0],
            "total_intensity": [1.0e6],
        }
        quad_scan = QuadScanEmittance(beamline=beamline, energy=energy, magnet_collection=self.magnet_collection,
                                      magnet_name=magnet_name, magnet_length=magnet_length, scan_values=scan_values,
                                      device_measurement=profmon_measurement)
        result_dict = quad_scan.measure()
        assert result_dict["emittance"] == mock_compute_emit_bmag.return_value[0]
        assert result_dict["BMAG"] == mock_compute_emit_bmag.return_value[1]
        mock_compute_emit_bmag.assert_called_once()
        mock_get_optics.assert_called_once()
        number_scan_values = len(scan_values)
        self.assertEqual(mock_put.call_count, number_scan_values)
        self.assertEqual(mock_trim.call_count, number_scan_values)
        self.assertEqual(mock_bact_settle.call_count, number_scan_values)
        assert profmon_measurement.measure.call_count == number_scan_values
