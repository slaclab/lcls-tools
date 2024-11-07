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
            [2.5, 4.2, 0.0, 0.0, 1.6, -1.0],
            [3.6, 1.0, 0.0, 0.0, 3.8, -6.9],
            [0.0, 0.0, -5.1, 4.1, 0.0, 0.0],
            [0.0, 0.0, -3.6, 9.9, 0.0, 0.0],
            [3.5, -2.5, 0.0, 0.0, 1.0, 5.9],
            [-1.0, -1.2, 0.0, 0.0, -4.9, 1.0]
        ])
        twiss_dtype = np.dtype([('s', 'float32'), ('z', 'float32'), ('length', 'float32'),
                                ('p0c', 'float32'), ('alpha_x', 'float32'), ('beta_x', 'float32'),
                                ('eta_x', 'float32'), ('etap_x', 'float32'), ('psi_x', 'float32'),
                                ('alpha_y', 'float32'), ('beta_y', 'float32'), ('eta_y', 'float32'),
                                ('etap_y', 'float32'), ('psi_y', 'float32')])
        twiss_mock = np.array(
            [(11.9, 2027.7, 0.05, 1.3, 3.9, 5.5,
              -6.1, 1.2, 5.9, 0.01, 5.3, 0., 0., 3.5)],
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
        number_scan_values = len(scan_values)
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
        assert result_dict["x_rms"] == [profmon_measurement.measure.return_value["Sx"]] * number_scan_values
        assert result_dict["y_rms"] == [profmon_measurement.measure.return_value["Sy"]] * number_scan_values
        mock_compute_emit_bmag.assert_called_once()
        mock_get_optics.assert_called_once()
        self.assertEqual(mock_put.call_count, number_scan_values)
        self.assertEqual(mock_trim.call_count, number_scan_values)
        self.assertEqual(mock_bact_settle.call_count, number_scan_values)
        assert profmon_measurement.measure.call_count == number_scan_values
