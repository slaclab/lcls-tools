from datetime import datetime, timedelta
from random import randint
from unittest import TestCase
from unittest.mock import MagicMock

from lcls_tools.common.controls.pyepics.utils import (
    EPICS_INVALID_VAL,
    EPICS_NO_ALARM_VAL,
)
from lcls_tools.superconducting.sc_cavity import Cavity
from lcls_tools.superconducting.sc_linac import MACHINE
from lcls_tools.superconducting.sc_linac_utils import (
    RF_MODE_CHIRP,
    RF_MODE_SEL,
    RF_MODE_SELA,
    RF_MODE_SELAP,
    LOADED_Q_LOWER_LIMIT,
    LOADED_Q_LOWER_LIMIT_HL,
    LOADED_Q_UPPER_LIMIT,
    LOADED_Q_UPPER_LIMIT_HL,
    CAVITY_SCALE_LOWER_LIMIT_HL,
    CAVITY_SCALE_UPPER_LIMIT_HL,
    CAVITY_SCALE_UPPER_LIMIT,
    CAVITY_SCALE_LOWER_LIMIT,
    CHARACTERIZATION_RUNNING_VALUE,
    CHARACTERIZATION_CRASHED_VALUE,
    HW_MODE_ONLINE_VALUE,
    HW_MODE_OFFLINE_VALUE,
    DetuneError,
    NOMINAL_PULSED_ONTIME,
    CavityHWModeError,
    TUNE_CONFIG_RESONANCE_VALUE,
    CavityAbortError,
    SAFE_PULSED_DRIVE_LEVEL,
    INTERLOCK_RESET_ATTEMPTS,
    CavityFaultError,
    CALIBRATION_COMPLETE_VALUE,
    CavityCharacterizationError,
    QuenchError,
)
from lcls_tools.superconducting.sc_stepper import StepperTuner


def make_mock_pv(pv_name: str = None, get_val=None) -> MagicMock:
    return MagicMock(
        pvname=pv_name,
        put=MagicMock(return_value=1),
        get=MagicMock(return_value=get_val),
    )


class TestCavity(TestCase):
    def setUp(self):
        self.cavity: Cavity = MACHINE.cryomodules["01"].cavities[1]
        self.hl_cavity: Cavity = MACHINE.cryomodules["H1"].cavities[1]
        self.cavity._rf_control_pv_obj = make_mock_pv(self.cavity.rf_control_pv)
        self.cavity._rf_mode_pv_obj = make_mock_pv(self.cavity.rf_mode_pv)
        self.cavity._rf_mode_ctrl_pv_obj = make_mock_pv(self.cavity.rf_mode_ctrl_pv)
        self.cavity._detune_chirp_pv_obj = make_mock_pv(self.cavity.detune_chirp_pv)
        self.cavity._detune_best_pv_obj = make_mock_pv(self.cavity.detune_best_pv)

        self.hz_per_microstep = 0.00540801
        self.cavity.stepper_tuner._hz_per_microstep_pv_obj = make_mock_pv(
            self.cavity.stepper_tuner.hz_per_microstep_pv, get_val=self.hz_per_microstep
        )
        self.cavity.stepper_tuner.move = MagicMock()
        self.cavity._tune_config_pv_obj = make_mock_pv(self.cavity.tune_config_pv)

        self.measured_loaded_q = 4.41011e07

        self.detune_calls = 0

    def test_pv_prefix(self):
        self.assertEqual(self.cavity.pv_prefix, "ACCL:L0B:0110:")

    def test_loaded_q_limits(self):
        self.assertEqual(self.cavity.loaded_q_lower_limit, LOADED_Q_LOWER_LIMIT)
        self.assertEqual(self.hl_cavity.loaded_q_lower_limit, LOADED_Q_LOWER_LIMIT_HL)

        self.assertEqual(self.cavity.loaded_q_upper_limit, LOADED_Q_UPPER_LIMIT)
        self.assertEqual(self.hl_cavity.loaded_q_upper_limit, LOADED_Q_UPPER_LIMIT_HL)

    def test_microsteps_per_hz(self):
        self.assertEqual(self.cavity.microsteps_per_hz, 1 / self.hz_per_microstep)

    def test_start_characterization(self):
        self.cavity._characterization_start_pv_obj = make_mock_pv(
            self.cavity.characterization_start_pv
        )
        self.cavity.start_characterization()
        self.cavity._characterization_start_pv_obj.put.assert_called_with(1)

    def test_cw_data_decimation(self):
        val = randint(0, 256)
        self.cavity._cw_data_decim_pv_obj = make_mock_pv(
            self.cavity.cw_data_decimation_pv, get_val=val
        )
        self.assertEqual(self.cavity.cw_data_decimation, val)

    def test_pulsed_data_decimation(self):
        val = randint(0, 256)
        self.cavity._pulsed_data_decim_pv_obj = make_mock_pv(
            self.cavity.pulsed_data_decimation_pv, get_val=val
        )
        self.assertEqual(self.cavity.pulsed_data_decimation, val)

    def test_rf_control(self):
        self.cavity._rf_control_pv_obj = make_mock_pv(
            self.cavity.rf_control_pv, get_val=1
        )
        self.assertEqual(self.cavity.rf_control, 1)

    def test_rf_mode(self):
        mode = randint(0, 6)
        self.cavity._rf_mode_pv_obj.get = MagicMock(return_value=mode)
        self.assertEqual(self.cavity.rf_mode, mode)

    def test_set_chirp_mode(self):
        self.cavity.set_chirp_mode()
        self.cavity._rf_mode_ctrl_pv_obj.put.assert_called_with(RF_MODE_CHIRP)

    def test_set_sel_mode(self):
        self.cavity.set_sel_mode()
        self.cavity._rf_mode_ctrl_pv_obj.put.assert_called_with(RF_MODE_SEL)

    def test_set_sela_mode(self):
        self.cavity.set_sela_mode()
        self.cavity._rf_mode_ctrl_pv_obj.put.assert_called_with(RF_MODE_SELA)

    def test_set_selap_mode(self):
        self.cavity.set_selap_mode()
        self.cavity._rf_mode_ctrl_pv_obj.put.assert_called_with(
            RF_MODE_SELAP, use_caput=False
        )

    def test_drive_level(self):
        val = randint(0, 100)
        self.cavity._drive_level_pv_obj = make_mock_pv(
            self.cavity.drive_level_pv, get_val=val
        )
        self.assertEqual(self.cavity.drive_level, val)

    def test_push_ssa_slope(self):
        self.cavity._push_ssa_slope_pv_obj = make_mock_pv(self.cavity.push_ssa_slope_pv)
        self.cavity.push_ssa_slope()
        self.cavity._push_ssa_slope_pv_obj.put.assert_called_with(1)

    def test_save_ssa_slope(self):
        self.cavity._save_ssa_slope_pv_obj = make_mock_pv(self.cavity.save_ssa_slope_pv)
        self.cavity.save_ssa_slope()
        self.cavity._save_ssa_slope_pv_obj.put.assert_called_with(1)

    def test_measured_loaded_q(self):
        self.cavity._measured_loaded_q_pv_obj = make_mock_pv(
            self.cavity.measured_loaded_q_pv, get_val=self.measured_loaded_q
        )
        self.assertEqual(self.cavity.measured_loaded_q, self.measured_loaded_q)

    def test_measured_loaded_q_in_tolerance(self):
        in_tol_val = randint(LOADED_Q_LOWER_LIMIT, LOADED_Q_UPPER_LIMIT)
        self.cavity._measured_loaded_q_pv_obj = make_mock_pv(
            self.cavity.measured_loaded_q_pv, get_val=in_tol_val
        )
        self.assertTrue(
            self.cavity.measured_loaded_q_in_tolerance,
            msg=f"loaded q {in_tol_val} should be in tolerance",
        )

    def test_measured_loaded_q_in_tolerance_hl(self):
        in_tol_val = randint(LOADED_Q_LOWER_LIMIT_HL, LOADED_Q_UPPER_LIMIT_HL)
        self.hl_cavity._measured_loaded_q_pv_obj = make_mock_pv(
            self.hl_cavity.measured_loaded_q_pv, get_val=in_tol_val
        )
        self.assertTrue(
            self.hl_cavity.measured_loaded_q_in_tolerance,
            msg=f"loaded q {in_tol_val} should be in tolerance",
        )

    def test_loaded_q_high(self):
        high_val = randint(LOADED_Q_UPPER_LIMIT, LOADED_Q_UPPER_LIMIT * 10)
        self.cavity._measured_loaded_q_pv_obj = make_mock_pv(
            self.cavity.measured_loaded_q_pv, get_val=high_val
        )
        self.assertFalse(
            self.cavity.measured_loaded_q_in_tolerance,
            msg=f"loaded q {high_val} should be out of tolerance",
        )

    def test_loaded_q_high_hl(self):
        high_val = randint(LOADED_Q_UPPER_LIMIT_HL, LOADED_Q_UPPER_LIMIT_HL * 10)
        self.hl_cavity._measured_loaded_q_pv_obj = make_mock_pv(
            self.hl_cavity.measured_loaded_q_pv, get_val=high_val
        )
        self.assertFalse(
            self.hl_cavity.measured_loaded_q_in_tolerance,
            msg=f"loaded q {high_val} should be out of tolerance",
        )

    def test_loaded_q_low(self):
        low_val = randint(0, LOADED_Q_LOWER_LIMIT)
        self.cavity._measured_loaded_q_pv_obj = make_mock_pv(
            self.cavity.measured_loaded_q_pv, get_val=low_val
        )
        self.assertFalse(
            self.cavity.measured_loaded_q_in_tolerance,
            msg=f"loaded q {low_val} should be out of tolerance",
        )

    def test_loaded_q_low_hl(self):
        low_val = randint(0, LOADED_Q_LOWER_LIMIT_HL)
        self.hl_cavity._measured_loaded_q_pv_obj = make_mock_pv(
            self.hl_cavity.measured_loaded_q_pv, get_val=low_val
        )
        self.assertFalse(
            self.hl_cavity.measured_loaded_q_in_tolerance,
            msg=f"loaded q {low_val} should be out of tolerance",
        )

    def test_push_loaded_q(self):
        self.cavity._push_loaded_q_pv_obj = make_mock_pv(self.cavity.push_loaded_q_pv)
        self.cavity.push_loaded_q()
        self.cavity._push_loaded_q_pv_obj.put.assert_called_with(1)

    def test_measured_scale_factor(self):
        val = randint(CAVITY_SCALE_LOWER_LIMIT_HL, CAVITY_SCALE_UPPER_LIMIT_HL)
        self.cavity._measured_scale_factor_pv_obj = make_mock_pv(
            self.cavity.measured_scale_factor_pv, get_val=val
        )
        self.assertEqual(self.cavity.measured_scale_factor, val)

    def test_measured_scale_factor_in_tolerance_hl(self):
        val = randint(CAVITY_SCALE_LOWER_LIMIT_HL, CAVITY_SCALE_UPPER_LIMIT_HL)
        self.hl_cavity._measured_scale_factor_pv_obj = make_mock_pv(
            self.hl_cavity.measured_scale_factor_pv, get_val=val
        )
        self.assertTrue(self.hl_cavity.measured_scale_factor_in_tolerance)

    def test_measured_scale_factor_in_tolerance(self):
        val = randint(CAVITY_SCALE_LOWER_LIMIT, CAVITY_SCALE_UPPER_LIMIT)
        self.cavity._measured_scale_factor_pv_obj = make_mock_pv(
            self.cavity.measured_scale_factor_pv, get_val=val
        )
        self.assertTrue(self.cavity.measured_scale_factor_in_tolerance)

    def test_scale_factor_high(self):
        val = randint(CAVITY_SCALE_UPPER_LIMIT, CAVITY_SCALE_UPPER_LIMIT * 2)
        self.cavity._measured_scale_factor_pv_obj = make_mock_pv(
            self.cavity.measured_scale_factor_pv, get_val=val
        )
        self.assertFalse(self.cavity.measured_scale_factor_in_tolerance)

    def test_scale_factor_high_hl(self):
        val = randint(CAVITY_SCALE_UPPER_LIMIT_HL, CAVITY_SCALE_UPPER_LIMIT_HL * 2)
        self.hl_cavity._measured_scale_factor_pv_obj = make_mock_pv(
            self.hl_cavity.measured_scale_factor_pv, get_val=val
        )
        self.assertFalse(self.hl_cavity.measured_scale_factor_in_tolerance)

    def test_scale_factor_low(self):
        val = randint(0, CAVITY_SCALE_LOWER_LIMIT)
        self.cavity._measured_scale_factor_pv_obj = make_mock_pv(
            self.cavity.measured_scale_factor_pv, get_val=val
        )
        self.assertFalse(self.cavity.measured_scale_factor_in_tolerance)

    def test_scale_factor_low_hl(self):
        val = randint(0, CAVITY_SCALE_LOWER_LIMIT_HL)
        self.hl_cavity._measured_scale_factor_pv_obj = make_mock_pv(
            self.hl_cavity.measured_scale_factor_pv, get_val=val
        )
        self.assertFalse(self.hl_cavity.measured_scale_factor_in_tolerance)

    def test_push_scale_factor(self):
        self.cavity._push_scale_factor_pv_obj = make_mock_pv(
            self.cavity.push_scale_factor_pv
        )
        self.cavity.push_scale_factor()
        self.cavity._push_scale_factor_pv_obj.put.assert_called_with(1)

    def test_characterization_status(self):
        val = randint(0, 3)
        self.cavity._characterization_status_pv_obj = make_mock_pv(
            self.cavity.characterization_status_pv, get_val=val
        )
        self.assertEqual(self.cavity.characterization_status, val)

    def test_characterization_running(self):
        self.cavity._characterization_status_pv_obj = make_mock_pv(
            self.cavity.characterization_status_pv,
            get_val=CHARACTERIZATION_RUNNING_VALUE,
        )
        self.assertTrue(
            self.cavity.characterization_running,
        )

        self.cavity._characterization_status_pv_obj = make_mock_pv(
            self.cavity.characterization_status_pv,
            get_val=CHARACTERIZATION_CRASHED_VALUE,
        )
        self.assertFalse(
            self.cavity.characterization_running,
        )

    def test_characterization_crashed(self):
        self.cavity._characterization_status_pv_obj = make_mock_pv(
            self.cavity.characterization_status_pv,
            get_val=CHARACTERIZATION_CRASHED_VALUE,
        )
        self.assertTrue(
            self.cavity.characterization_crashed,
        )

        self.cavity._characterization_status_pv_obj = make_mock_pv(
            self.cavity.characterization_status_pv,
            get_val=CHARACTERIZATION_RUNNING_VALUE,
        )
        self.assertFalse(
            self.cavity.characterization_crashed,
        )

    def test_pulse_on_time(self):
        self.cavity._pulse_on_time_pv_obj = make_mock_pv(
            self.cavity.pulse_on_time_pv, 70
        )
        self.assertEqual(self.cavity.pulse_on_time, 70)

    def test_pulse_status(self):
        val = randint(0, 5)
        self.cavity._pulse_status_pv_obj = make_mock_pv(
            self.cavity.pulse_status_pv, get_val=val
        )
        self.assertEqual(self.cavity.pulse_status, val)

    def test_rf_permit(self):
        self.cavity._rf_permit_pv_obj = make_mock_pv(
            self.cavity.rf_permit_pv, get_val=1
        )
        self.assertEqual(self.cavity.rf_permit, 1)

    def test_rf_inhibited(self):
        self.cavity._rf_permit_pv_obj = make_mock_pv(
            self.cavity.rf_permit_pv, get_val=1
        )
        self.assertFalse(self.cavity.rf_inhibited)

        self.cavity._rf_permit_pv_obj = make_mock_pv(
            self.cavity.rf_permit_pv, get_val=0
        )
        self.assertTrue(self.cavity.rf_inhibited)

    def test_ades(self):
        val = randint(0, 21)
        self.cavity._ades_pv_obj = make_mock_pv(self.cavity.ades_pv, get_val=val)
        self.assertEqual(self.cavity.ades, val)

    def test_acon(self):
        val = randint(0, 21)
        self.cavity._acon_pv_obj = make_mock_pv(self.cavity.acon_pv, get_val=val)
        self.assertEqual(self.cavity.acon, val)

    def test_aact(self):
        val = randint(0, 21)
        self.cavity._aact_pv_obj = make_mock_pv(self.cavity.aact_pv, get_val=val)
        self.assertEqual(self.cavity.aact, val)

    def test_ades_max(self):
        val = randint(0, 21)
        self.cavity._ades_max_pv_obj = make_mock_pv(
            self.cavity.ades_max_pv, get_val=val
        )
        self.assertEqual(self.cavity.ades_max, val)

    def test_edm_macro_string(self):
        self.assertEqual(
            self.cavity.edm_macro_string, f"C=1,RFS=1A,R=A,CM=ACCL:L0B:01,ID=01,CH=1"
        )

    def test_edm_macro_string_rack_b(self):
        cav = MACHINE.cryomodules["01"].cavities[5]
        self.assertEqual(
            cav.edm_macro_string, f"C=5,RFS=1B,R=B,CM=ACCL:L0B:01,ID=01,CH=1"
        )

    def test_hw_mode(self):
        self.cavity._hw_mode_pv_obj = make_mock_pv(
            self.cavity.hw_mode_pv, get_val=HW_MODE_ONLINE_VALUE
        )
        self.assertEqual(self.cavity.hw_mode, HW_MODE_ONLINE_VALUE)

    def test_is_online(self):
        self.cavity._hw_mode_pv_obj = make_mock_pv(
            self.cavity.hw_mode_pv, get_val=HW_MODE_ONLINE_VALUE
        )
        self.assertTrue(self.cavity.is_online)

        self.cavity._hw_mode_pv_obj = make_mock_pv(
            self.cavity.hw_mode_pv, get_val=HW_MODE_OFFLINE_VALUE
        )
        self.assertFalse(self.cavity.is_online)

    def test_chirp_freq_start(self):
        val = -200000
        self.cavity._chirp_freq_start_pv_obj = make_mock_pv(
            self.cavity.chirp_freq_start_pv, get_val=val
        )
        self.assertEqual(self.cavity.chirp_freq_start, val)

        new_val = -400000
        self.cavity.chirp_freq_start = new_val
        self.cavity._chirp_freq_start_pv_obj.put.assert_called_with(new_val)

    def test_chirp_freq_stop(self):
        val = 200000
        self.cavity._freq_stop_pv_obj = make_mock_pv(
            self.cavity.freq_stop_pv, get_val=val
        )
        self.assertEqual(self.cavity.chirp_freq_stop, val)

        new_val = 400000
        self.cavity.chirp_freq_stop = new_val
        self.cavity._freq_stop_pv_obj.put.assert_called_with(new_val)

    def test_calculate_probe_q(self):
        self.cavity._calc_probe_q_pv_obj = make_mock_pv(self.cavity.calc_probe_q_pv)
        self.cavity.calculate_probe_q()
        self.cavity._calc_probe_q_pv_obj.put.assert_called_with(1)

    def test_set_chirp_range(self):
        self.cavity._chirp_freq_start_pv_obj = make_mock_pv(
            self.cavity.chirp_freq_start_pv
        )
        self.cavity._freq_stop_pv_obj = make_mock_pv(self.cavity.freq_stop_pv)
        offset = randint(-400000, 0)
        self.cavity.set_chirp_range(offset)
        self.cavity._chirp_freq_start_pv_obj.put.assert_called_with(offset)
        self.cavity._freq_stop_pv_obj.put.assert_called_with(-offset)

    def test_rf_state(self):
        self.cavity._rf_state_pv_obj = make_mock_pv(self.cavity.rf_state_pv, get_val=1)
        self.assertEqual(self.cavity.rf_state, 1)

    def test_is_on(self):
        self.cavity._rf_state_pv_obj = make_mock_pv(self.cavity.rf_state_pv, get_val=1)
        self.assertTrue(self.cavity.is_on)

        self.cavity._rf_state_pv_obj = make_mock_pv(self.cavity.rf_state_pv, get_val=0)
        self.assertFalse(self.cavity.is_on)

    def mock_detune(self):
        """
        Ham fisted way of having the cavity report as detuned the first loop
        and tuned the second
        """
        self.detune_calls += 1
        print(f"Mock detune called {self.detune_calls}x")

        if self.detune_calls > 1:
            return randint(-50, 50)

        else:
            return randint(500, 1000)

    def test_move_to_resonance(self):
        cavity = MACHINE.cryomodules["01"].cavities[4]
        cavity._tune_config_pv_obj = make_mock_pv()

        cavity.setup_tuning = MagicMock()
        cavity._auto_tune = MagicMock()

        cavity.move_to_resonance()
        cavity.setup_tuning.assert_called()
        cavity._auto_tune.assert_called()
        cavity._tune_config_pv_obj.put.assert_called_with(TUNE_CONFIG_RESONANCE_VALUE)

    def test_detune_best(self):
        val = self.set_detune_best()
        self.assertEqual(self.cavity.detune_best, val)

    def set_detune_best(self):
        val = randint(-400000, 400000)
        self.cavity._detune_best_pv_obj.get = MagicMock(return_value=val)
        return val

    def test_detune_chirp(self):
        val = self.set_chirp_detune()
        self.assertEqual(self.cavity.detune_chirp, val)

    def test_detune(self):
        self.cavity._rf_mode_pv_obj.get = MagicMock(return_value=RF_MODE_SELA)
        val = self.set_detune_best()
        self.assertEqual(self.cavity.detune, val)

    def test_detune_in_chirp(self):
        self.cavity._rf_mode_pv_obj.get = MagicMock(return_value=RF_MODE_CHIRP)
        val = self.set_chirp_detune()
        self.assertEqual(self.cavity.detune, val)

    def set_chirp_detune(self):
        val = randint(-400000, 400000)
        self.cavity._detune_chirp_pv_obj.get = MagicMock(return_value=val)
        return val

    def test_detune_invalid(self):
        self.cavity._detune_best_pv_obj.severity = EPICS_INVALID_VAL
        self.cavity._rf_mode_pv_obj.get = MagicMock(return_value=RF_MODE_SELA)
        self.assertTrue(self.cavity.detune_invalid)

        self.cavity._detune_best_pv_obj.severity = EPICS_NO_ALARM_VAL
        self.assertFalse(self.cavity.detune_invalid)

    def test_detune_invalid_chirp(self):
        self.cavity._detune_chirp_pv_obj.severity = EPICS_INVALID_VAL
        self.cavity._rf_mode_pv_obj.get = MagicMock(return_value=RF_MODE_CHIRP)
        self.assertTrue(self.cavity.detune_invalid)

        self.cavity._detune_chirp_pv_obj.severity = EPICS_NO_ALARM_VAL
        self.assertFalse(self.cavity.detune_invalid)

    def test__auto_tune_invalid(self):
        """
        TODO figure out how to test the guts when detune > tolerance
        """
        self.cavity._rf_mode_pv_obj.get = MagicMock(return_value=RF_MODE_CHIRP)
        self.cavity._detune_chirp_pv_obj.severity = EPICS_INVALID_VAL

        # delta_hz_func argument is unnecessary
        self.assertRaises(DetuneError, self.cavity._auto_tune, None)

    def test__auto_tune_out_of_tol(self):
        self.cavity._rf_mode_pv_obj.get = MagicMock(return_value=RF_MODE_CHIRP)
        self.cavity._detune_chirp_pv_obj.severity = EPICS_NO_ALARM_VAL

        self.detune_calls = 0
        self.cavity._auto_tune(delta_hz_func=self.mock_detune)
        self.cavity.stepper_tuner.move.assert_called()
        self.assertEqual(self.detune_calls, 2)

    def test_check_detune(self):
        self.cavity._rf_mode_pv_obj.get = MagicMock(return_value=RF_MODE_CHIRP)
        self.cavity._detune_chirp_pv_obj.severity = EPICS_INVALID_VAL
        self.cavity._chirp_freq_start_pv_obj = make_mock_pv(
            self.cavity.chirp_freq_start_pv, get_val=50000
        )
        self.cavity.find_chirp_range = MagicMock()
        self.cavity.check_detune()
        self.cavity.find_chirp_range.assert_called_with(50000 * 1.1)

    def test_check_detune_sela(self):
        self.cavity._rf_mode_pv_obj.get = MagicMock(return_value=RF_MODE_SELA)
        self.cavity._detune_best_pv_obj.severity = EPICS_INVALID_VAL
        self.assertRaises(DetuneError, self.cavity.check_detune)

    def test_check_and_set_on_time(self):
        cavity = MACHINE.cryomodules["01"].cavities[5]
        cavity._pulse_on_time_pv_obj = make_mock_pv(
            cavity.pulse_on_time_pv, NOMINAL_PULSED_ONTIME * 0.9
        )
        cavity.push_go_button = MagicMock()
        cavity.check_and_set_on_time()
        cavity._pulse_on_time_pv_obj.put.assert_called_with(NOMINAL_PULSED_ONTIME)
        cavity.push_go_button.assert_called()

    def test_push_go_button(self):
        self.cavity._pulse_status_pv_obj = make_mock_pv(
            self.cavity.pulse_status_pv, get_val=2
        )
        self.cavity._pulse_go_pv_obj = make_mock_pv(self.cavity.pulse_go_pv)
        self.cavity.push_go_button()
        self.cavity._pulse_go_pv_obj.put.assert_called_with(1)

    def test_turn_on_not_online(self):
        for hw_status in range(1, 5):
            self.cavity._hw_mode_pv_obj = make_mock_pv(
                self.cavity.hw_mode_pv, get_val=hw_status
            )
            self.assertRaises(CavityHWModeError, self.cavity.turn_on)

    def test_turn_on(self):
        cavity = MACHINE.cryomodules["01"].cavities[6]
        cavity._hw_mode_pv_obj = make_mock_pv(get_val=HW_MODE_ONLINE_VALUE)
        cavity.ssa.turn_on = MagicMock()
        cavity.reset_interlocks = MagicMock()
        cavity._rf_state_pv_obj = make_mock_pv(self.cavity.rf_state_pv, get_val=1)
        cavity._rf_control_pv_obj = make_mock_pv()

        cavity.turn_on()
        cavity.ssa.turn_on.assert_called()
        cavity.reset_interlocks.assert_called()
        cavity._rf_state_pv_obj.get.assert_called()
        cavity._rf_control_pv_obj.put.assert_called_with(1)

    def test_turn_off(self):
        self.cavity._rf_state_pv_obj = make_mock_pv(self.cavity.rf_state_pv, get_val=0)
        self.cavity.turn_off()
        self.cavity._rf_control_pv_obj.put.assert_called_with(0)
        self.cavity._rf_state_pv_obj.get.assert_called()

    def test_setup_selap(self):
        cavity = MACHINE.cryomodules["01"].cavities[7]
        cavity.setup_rf = MagicMock()
        cavity.set_selap_mode = MagicMock()
        cavity.setup_selap(5)
        cavity.setup_rf.assert_called_with(5)
        cavity.set_selap_mode.assert_called()

    def test_setup_sela(self):
        cavity = MACHINE.cryomodules["01"].cavities[8]
        cavity.setup_rf = MagicMock()
        cavity.set_sela_mode = MagicMock()
        cavity.setup_sela(5)
        cavity.setup_rf.assert_called_with(5)
        cavity.set_sela_mode.assert_called()

    def test_check_abort(self):
        self.cavity.abort_flag = True
        self.cavity._rf_state_pv_obj = make_mock_pv(self.cavity.rf_state_pv, get_val=0)
        self.assertRaises(CavityAbortError, self.cavity.check_abort)

        try:
            self.cavity.abort_flag = False
            self.cavity.check_abort()
        except CavityAbortError:
            self.fail("Cavity abort error raised when flag not set")

    def test_setup_rf(self):
        self.cavity.ssa.calibrate = MagicMock()
        self.cavity.setup_rf(5)
        self.cavity.ssa.calibrate.assert_called()

    def test_reset_data_decimation(self):
        self.cavity._cw_data_decim_pv_obj = make_mock_pv()
        self.cavity._pulsed_data_decim_pv_obj = make_mock_pv()
        self.cavity.reset_data_decimation()
        self.cavity._cw_data_decim_pv_obj.put.assert_called_with(255)
        self.cavity._pulsed_data_decim_pv_obj.put.assert_called_with(255)

    def test_setup_tuning_sela(self):
        cavity = MACHINE.cryomodules["01"].cavities[2]
        cavity.piezo.enable = MagicMock()
        cavity.piezo.enable_feedback = MagicMock()
        cavity.set_sela_mode = MagicMock()
        cavity.turn_on = MagicMock()

        cavity.setup_tuning(use_sela=True)
        cavity.piezo.enable.assert_called()
        cavity.piezo.enable_feedback.assert_called()
        cavity.turn_on.assert_called()

    def test_setup_tuning_not_sela(self):
        cavity = MACHINE.cryomodules["01"].cavities[3]
        cavity.piezo.enable = MagicMock()
        cavity.set_sela_mode = MagicMock()
        cavity.turn_on = MagicMock()
        cavity.piezo.disable_feedback = MagicMock()
        cavity.piezo._dc_setpoint_pv_obj = make_mock_pv()
        cavity._drive_level_pv_obj = make_mock_pv()
        cavity.set_chirp_mode = MagicMock()
        cavity.find_chirp_range = MagicMock()

        cavity.setup_tuning(use_sela=False)
        cavity.piezo.enable.assert_called()
        cavity.turn_on.assert_called()
        cavity.piezo._dc_setpoint_pv_obj.put.assert_called_with(0)
        cavity._drive_level_pv_obj.put.assert_called_with(SAFE_PULSED_DRIVE_LEVEL)
        cavity.set_chirp_mode.assert_called()
        cavity.find_chirp_range.assert_called()

    def test_find_chirp_range_valid(self):
        cavity = MACHINE.cryomodules["02"].cavities[1]
        cavity.check_abort = MagicMock()
        cavity.set_chirp_range = MagicMock()
        cavity._rf_mode_pv_obj = make_mock_pv(get_val=RF_MODE_CHIRP)
        cavity._detune_chirp_pv_obj = make_mock_pv()
        cavity._detune_chirp_pv_obj.severity = EPICS_NO_ALARM_VAL

        cavity.find_chirp_range(50000)
        cavity.check_abort.assert_called()
        cavity.set_chirp_range.assert_called_with(50000)

    def test_reset_interlocks(self):
        self.cavity._interlock_reset_pv_obj = make_mock_pv()
        self.cavity._rf_permit_pv_obj = make_mock_pv(get_val=0)
        self.assertRaises(
            CavityFaultError,
            self.cavity.reset_interlocks,
            attempt=INTERLOCK_RESET_ATTEMPTS,
        )
        self.cavity._interlock_reset_pv_obj.put.assert_called_with(1)

    def test_characterization_timestamp(self):
        self.cavity._char_timestamp_pv_obj = make_mock_pv(get_val="2024-04-11-15:17:17")
        self.assertEqual(
            self.cavity.characterization_timestamp, datetime(2024, 4, 11, 15, 17, 17)
        )

    def test_characterize(self):
        """
        TODO test characterization running
        """
        cavity = MACHINE.cryomodules["02"].cavities[2]
        cavity.reset_interlocks = MagicMock()
        cavity._drive_level_pv_obj = make_mock_pv()
        char_time = (datetime.now() - timedelta(seconds=100)).strftime(
            "%Y-%m-%d-%H:%M:%S"
        )
        cavity._char_timestamp_pv_obj = make_mock_pv(get_val=char_time)
        cavity.finish_characterization = MagicMock()
        cavity.start_characterization = MagicMock()
        cavity._characterization_status_pv_obj = make_mock_pv(
            get_val=CALIBRATION_COMPLETE_VALUE
        )

        cavity.characterize()
        cavity.reset_interlocks.assert_called()
        cavity._drive_level_pv_obj.put.assert_called_with(SAFE_PULSED_DRIVE_LEVEL)
        cavity.start_characterization.assert_called()
        cavity.finish_characterization.assert_called()

    def test_characterize_fail(self):
        cavity = MACHINE.cryomodules["02"].cavities[4]
        cavity.reset_interlocks = MagicMock()
        cavity._drive_level_pv_obj = make_mock_pv()
        char_time = (datetime.now() - timedelta(seconds=100)).strftime(
            "%Y-%m-%d-%H:%M:%S"
        )
        cavity._char_timestamp_pv_obj = make_mock_pv(get_val=char_time)
        cavity.start_characterization = MagicMock()
        cavity._characterization_status_pv_obj = make_mock_pv(
            get_val=CHARACTERIZATION_CRASHED_VALUE
        )

        self.assertRaises(CavityCharacterizationError, cavity.characterize)
        cavity.reset_interlocks.assert_called()
        cavity._drive_level_pv_obj.put.assert_called_with(SAFE_PULSED_DRIVE_LEVEL)
        cavity.start_characterization.assert_called()

    def test_characterize_recent(self):
        cavity = MACHINE.cryomodules["02"].cavities[3]
        cavity.reset_interlocks = MagicMock()
        cavity._drive_level_pv_obj = make_mock_pv()
        char_time = (datetime.now() - timedelta(seconds=10)).strftime(
            "%Y-%m-%d-%H:%M:%S"
        )
        cavity._char_timestamp_pv_obj = make_mock_pv(get_val=char_time)
        cavity.finish_characterization = MagicMock()
        cavity._characterization_status_pv_obj = make_mock_pv(
            get_val=CALIBRATION_COMPLETE_VALUE
        )

        cavity.characterize()
        cavity.reset_interlocks.assert_called()
        cavity._drive_level_pv_obj.put.assert_called_with(SAFE_PULSED_DRIVE_LEVEL)
        cavity.finish_characterization.assert_called()

    def test_finish_characterization(self):
        cavity = MACHINE.cryomodules["02"].cavities[5]
        cavity._measured_loaded_q_pv_obj = make_mock_pv(
            get_val=randint(cavity.loaded_q_lower_limit, cavity.loaded_q_upper_limit)
        )
        cavity.push_loaded_q = MagicMock()
        cavity._measured_scale_factor_pv_obj = make_mock_pv(
            get_val=randint(
                cavity.scale_factor_lower_limit, cavity.scale_factor_upper_limit
            )
        )
        cavity.push_scale_factor = MagicMock()
        cavity.reset_data_decimation = MagicMock()
        cavity.piezo._feedback_setpoint_pv_obj = make_mock_pv()

        cavity.finish_characterization()
        cavity.push_loaded_q.assert_called()
        cavity.push_scale_factor.assert_called()
        cavity.reset_data_decimation.assert_called()
        cavity.piezo._feedback_setpoint_pv_obj.put.assert_called_with(0)

    def test_walk_amp_quench(self):
        self.cavity._quench_latch_pv_obj = make_mock_pv(get_val=1)
        self.cavity._ades_pv_obj = make_mock_pv(get_val=16)
        self.assertRaises(QuenchError, self.cavity.walk_amp, 16.6, 0.1)

    def test_walk_amp(self):
        self.cavity._quench_latch_pv_obj = make_mock_pv(get_val=0)
        self.cavity._ades_pv_obj = make_mock_pv(get_val=16.05)
        self.cavity.walk_amp(16.1, 0.1)
        self.cavity._ades_pv_obj.put.assert_called_with(16.1)


class TestStepperTuner(TestCase):
    def setUp(self):
        self.stepper_tuner: StepperTuner = (
            MACHINE.cryomodules["03"].cavities[1].stepper_tuner
        )
        self.step_scale = -0.00589677
        self.stepper_tuner._hz_per_microstep_pv_obj = make_mock_pv(
            self.stepper_tuner.hz_per_microstep_pv, get_val=self.step_scale
        )

    def test_pv_prefix(self):
        self.fail()

    def test_hz_per_microstep(self):
        self.assertEqual(self.stepper_tuner.hz_per_microstep, abs(self.step_scale))

    def test_check_abort(self):
        self.fail()

    def test_abort(self):
        self.fail()

    def test_move_positive(self):
        self.fail()

    def test_move_negative(self):
        self.fail()

    def test_step_des(self):
        self.fail()

    def test_motor_moving(self):
        self.fail()

    def test_reset_signed_steps(self):
        self.fail()

    def test_on_limit_switch(self):
        self.fail()

    def test_max_steps(self):
        self.fail()

    def test_speed(self):
        self.fail()

    def test_restore_defaults(self):
        self.fail()

    def test_move(self):
        self.fail()

    def test_issue_move_command(self):
        self.fail()
