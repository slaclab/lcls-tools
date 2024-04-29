from datetime import datetime, timedelta
from random import randint
from unittest import TestCase
from unittest.mock import MagicMock

from lcls_tools.common.controls.pyepics.utils import (
    EPICS_INVALID_VAL,
    EPICS_NO_ALARM_VAL,
)
from lcls_tools.superconducting.sc_cryomodule import Cryomodule
from lcls_tools.superconducting.sc_linac import MACHINE
from lcls_tools.superconducting.sc_linac_utils import (
    LOADED_Q_LOWER_LIMIT,
    LOADED_Q_LOWER_LIMIT_HL,
    LOADED_Q_UPPER_LIMIT,
    LOADED_Q_UPPER_LIMIT_HL,
    RF_MODE_CHIRP,
    RF_MODE_SEL,
    RF_MODE_SELA,
    RF_MODE_SELAP,
    CAVITY_SCALE_LOWER_LIMIT_HL,
    CAVITY_SCALE_UPPER_LIMIT_HL,
    CAVITY_SCALE_LOWER_LIMIT,
    CAVITY_SCALE_UPPER_LIMIT,
    CHARACTERIZATION_RUNNING_VALUE,
    CHARACTERIZATION_CRASHED_VALUE,
    HW_MODE_ONLINE_VALUE,
    HW_MODE_OFFLINE_VALUE,
    TUNE_CONFIG_RESONANCE_VALUE,
    DetuneError,
    NOMINAL_PULSED_ONTIME,
    CavityHWModeError,
    CavityAbortError,
    SAFE_PULSED_DRIVE_LEVEL,
    CavityFaultError,
    INTERLOCK_RESET_ATTEMPTS,
    CALIBRATION_COMPLETE_VALUE,
    CavityCharacterizationError,
    QuenchError,
)
from tests.unit_tests.lcls_tools.superconducting.test_sc_linac import make_mock_pv

non_hl_cavities = []
hl_cavities = []

for non_hl_cm_num in range(1, 36):
    cm_obj: Cryomodule = MACHINE.cryomodules[f"{non_hl_cm_num:02d}"]
    for cavity_obj in cm_obj.cavities.values():
        non_hl_cavities.append(cavity_obj)

for i in range(1, 3):
    hl_obj: Cryomodule = MACHINE.cryomodules[f"H{i}"]
    for hl_cavity in hl_obj.cavities.values():
        hl_cavities.append(hl_cavity)

# TODO handle hitting end of list
# An iterator so that we use a different cavity for every test to make
# sure that there isn't "cross contamination"
cavity_iterator = iter(non_hl_cavities)
hl_cavity_iterator = iter(hl_cavities)


class TestCavity(TestCase):
    def setUp(self):
        self.hz_per_microstep = 0.00540801
        self.measured_loaded_q = 4.41011e07

        self.detune_calls = 0

    def test_pv_prefix(self):
        cavity = MACHINE.cryomodules["01"].cavities[1]
        self.assertEqual(cavity.pv_prefix, "ACCL:L0B:0110:")

    def test_loaded_q_limits(self):
        cavity = next(cavity_iterator)
        self.assertEqual(cavity.loaded_q_lower_limit, LOADED_Q_LOWER_LIMIT)
        self.assertEqual(cavity.loaded_q_upper_limit, LOADED_Q_UPPER_LIMIT)

    def test_microsteps_per_hz(self):
        cavity = next(cavity_iterator)
        cavity.stepper_tuner._hz_per_microstep_pv_obj = make_mock_pv(
            get_val=self.hz_per_microstep
        )
        self.assertEqual(cavity.microsteps_per_hz, 1 / self.hz_per_microstep)

    def test_start_characterization(self):
        cavity = next(cavity_iterator)
        cavity._characterization_start_pv_obj = make_mock_pv()
        cavity.start_characterization()
        cavity._characterization_start_pv_obj.put.assert_called_with(1)

    def test_cw_data_decimation(self):
        cavity = next(cavity_iterator)
        val = randint(0, 256)
        cavity._cw_data_decim_pv_obj = make_mock_pv(get_val=val)
        self.assertEqual(cavity.cw_data_decimation, val)

    def test_pulsed_data_decimation(self):
        cavity = next(cavity_iterator)
        val = randint(0, 256)
        cavity._pulsed_data_decim_pv_obj = make_mock_pv(get_val=val)
        self.assertEqual(cavity.pulsed_data_decimation, val)

    def test_rf_control(self):
        cavity = next(cavity_iterator)
        cavity._rf_control_pv_obj = make_mock_pv(get_val=1)
        self.assertEqual(cavity.rf_control, 1)

    def test_rf_mode(self):
        cavity = next(cavity_iterator)
        mode = randint(0, 6)
        cavity._rf_mode_pv_obj = make_mock_pv(get_val=mode)
        self.assertEqual(cavity.rf_mode, mode)

    def test_set_chirp_mode(self):
        cavity = next(cavity_iterator)
        cavity._rf_control_pv_obj = make_mock_pv()
        cavity._rf_mode_ctrl_pv_obj = make_mock_pv()
        cavity.set_chirp_mode()
        cavity._rf_mode_ctrl_pv_obj.put.assert_called_with(RF_MODE_CHIRP)

    def test_set_sel_mode(self):
        cavity = next(cavity_iterator)
        cavity._rf_mode_ctrl_pv_obj = make_mock_pv()
        cavity.set_sel_mode()
        cavity._rf_mode_ctrl_pv_obj.put.assert_called_with(RF_MODE_SEL)

    def test_set_sela_mode(self):
        cavity = next(cavity_iterator)
        cavity._rf_mode_ctrl_pv_obj = make_mock_pv()
        cavity.set_sela_mode()
        cavity._rf_mode_ctrl_pv_obj.put.assert_called_with(RF_MODE_SELA)

    def test_set_selap_mode(self):
        cavity = next(cavity_iterator)
        cavity._rf_mode_ctrl_pv_obj = make_mock_pv()
        cavity.set_selap_mode()
        cavity._rf_mode_ctrl_pv_obj.put.assert_called_with(
            RF_MODE_SELAP, use_caput=False
        )

    def test_drive_level(self):
        cavity = next(cavity_iterator)
        val = randint(0, 100)
        cavity._drive_level_pv_obj = make_mock_pv(get_val=val)
        self.assertEqual(cavity.drive_level, val)

    def test_push_ssa_slope(self):
        cavity = next(cavity_iterator)
        cavity._push_ssa_slope_pv_obj = make_mock_pv()
        cavity.push_ssa_slope()
        cavity._push_ssa_slope_pv_obj.put.assert_called_with(1)

    def test_save_ssa_slope(self):
        cavity = next(cavity_iterator)
        cavity._save_ssa_slope_pv_obj = make_mock_pv()
        cavity.save_ssa_slope()
        cavity._save_ssa_slope_pv_obj.put.assert_called_with(1)

    def test_measured_loaded_q(self):
        cavity = next(cavity_iterator)
        cavity._measured_loaded_q_pv_obj = make_mock_pv(get_val=self.measured_loaded_q)
        self.assertEqual(cavity.measured_loaded_q, self.measured_loaded_q)

    def test_measured_loaded_q_in_tolerance(self):
        cavity = next(cavity_iterator)
        in_tol_val = randint(LOADED_Q_LOWER_LIMIT, LOADED_Q_UPPER_LIMIT)
        cavity._measured_loaded_q_pv_obj = make_mock_pv(get_val=in_tol_val)
        self.assertTrue(
            cavity.measured_loaded_q_in_tolerance,
            msg=f"loaded q {in_tol_val} should be in tolerance",
        )

    def test_measured_loaded_q_in_tolerance_hl(self):
        in_tol_val = randint(LOADED_Q_LOWER_LIMIT_HL, LOADED_Q_UPPER_LIMIT_HL)
        hl_cavity = next(hl_cavity_iterator)
        hl_cavity._measured_loaded_q_pv_obj = make_mock_pv(get_val=in_tol_val)
        self.assertTrue(
            hl_cavity.measured_loaded_q_in_tolerance,
            msg=f"loaded q {in_tol_val} should be in tolerance",
        )

    def test_loaded_q_high(self):
        cavity = next(cavity_iterator)
        high_val = randint(LOADED_Q_UPPER_LIMIT, LOADED_Q_UPPER_LIMIT * 10)
        cavity._measured_loaded_q_pv_obj = make_mock_pv(get_val=high_val)
        self.assertFalse(
            cavity.measured_loaded_q_in_tolerance,
            msg=f"loaded q {high_val} should be out of tolerance",
        )

    def test_loaded_q_high_hl(self):
        hl_cavity = next(hl_cavity_iterator)
        high_val = randint(LOADED_Q_UPPER_LIMIT_HL, LOADED_Q_UPPER_LIMIT_HL * 10)
        hl_cavity._measured_loaded_q_pv_obj = make_mock_pv(get_val=high_val)
        self.assertFalse(
            hl_cavity.measured_loaded_q_in_tolerance,
            msg=f"loaded q {high_val} should be out of tolerance",
        )

    def test_loaded_q_low(self):
        cavity = next(cavity_iterator)
        low_val = randint(0, LOADED_Q_LOWER_LIMIT)
        cavity._measured_loaded_q_pv_obj = make_mock_pv(get_val=low_val)
        self.assertFalse(
            cavity.measured_loaded_q_in_tolerance,
            msg=f"loaded q {low_val} should be out of tolerance",
        )

    def test_loaded_q_low_hl(self):
        hl_cavity = next(hl_cavity_iterator)
        low_val = randint(0, LOADED_Q_LOWER_LIMIT_HL)
        hl_cavity._measured_loaded_q_pv_obj = make_mock_pv(get_val=low_val)
        self.assertFalse(
            hl_cavity.measured_loaded_q_in_tolerance,
            msg=f"loaded q {low_val} should be out of tolerance",
        )

    def test_push_loaded_q(self):
        cavity = next(cavity_iterator)
        cavity._push_loaded_q_pv_obj = make_mock_pv()
        cavity.push_loaded_q()
        cavity._push_loaded_q_pv_obj.put.assert_called_with(1)

    def test_measured_scale_factor(self):
        cavity = next(cavity_iterator)
        val = randint(CAVITY_SCALE_LOWER_LIMIT_HL, CAVITY_SCALE_UPPER_LIMIT_HL)
        cavity._measured_scale_factor_pv_obj = make_mock_pv(get_val=val)
        self.assertEqual(cavity.measured_scale_factor, val)

    def test_measured_scale_factor_in_tolerance_hl(self):
        hl_cavity = next(hl_cavity_iterator)
        val = randint(CAVITY_SCALE_LOWER_LIMIT_HL, CAVITY_SCALE_UPPER_LIMIT_HL)
        hl_cavity._measured_scale_factor_pv_obj = make_mock_pv(get_val=val)
        self.assertTrue(hl_cavity.measured_scale_factor_in_tolerance)

    def test_measured_scale_factor_in_tolerance(self):
        cavity = next(cavity_iterator)
        val = randint(CAVITY_SCALE_LOWER_LIMIT, CAVITY_SCALE_UPPER_LIMIT)
        cavity._measured_scale_factor_pv_obj = make_mock_pv(get_val=val)
        self.assertTrue(cavity.measured_scale_factor_in_tolerance)

    def test_scale_factor_high(self):
        cavity = next(cavity_iterator)
        val = randint(CAVITY_SCALE_UPPER_LIMIT, CAVITY_SCALE_UPPER_LIMIT * 2)
        cavity._measured_scale_factor_pv_obj = make_mock_pv(get_val=val)
        self.assertFalse(cavity.measured_scale_factor_in_tolerance)

    def test_scale_factor_high_hl(self):
        hl_cavity = next(hl_cavity_iterator)
        val = randint(CAVITY_SCALE_UPPER_LIMIT_HL, CAVITY_SCALE_UPPER_LIMIT_HL * 2)
        hl_cavity._measured_scale_factor_pv_obj = make_mock_pv(get_val=val)
        self.assertFalse(hl_cavity.measured_scale_factor_in_tolerance)

    def test_scale_factor_low(self):
        cavity = next(cavity_iterator)
        val = randint(0, CAVITY_SCALE_LOWER_LIMIT)
        cavity._measured_scale_factor_pv_obj = make_mock_pv(get_val=val)
        self.assertFalse(cavity.measured_scale_factor_in_tolerance)

    def test_scale_factor_low_hl(self):
        hl_cavity = next(hl_cavity_iterator)
        val = randint(0, CAVITY_SCALE_LOWER_LIMIT_HL)
        hl_cavity._measured_scale_factor_pv_obj = make_mock_pv(get_val=val)
        self.assertFalse(hl_cavity.measured_scale_factor_in_tolerance)

    def test_push_scale_factor(self):
        cavity = next(cavity_iterator)
        cavity._push_scale_factor_pv_obj = make_mock_pv()
        cavity.push_scale_factor()
        cavity._push_scale_factor_pv_obj.put.assert_called_with(1)

    def test_characterization_status(self):
        cavity = next(cavity_iterator)
        val = randint(0, 3)
        cavity._characterization_status_pv_obj = make_mock_pv(get_val=val)
        self.assertEqual(cavity.characterization_status, val)

    def test_characterization_running(self):
        cavity = next(cavity_iterator)
        cavity._characterization_status_pv_obj = make_mock_pv(
            get_val=CHARACTERIZATION_RUNNING_VALUE,
        )
        self.assertTrue(
            cavity.characterization_running,
        )

        cavity._characterization_status_pv_obj = make_mock_pv(
            get_val=CHARACTERIZATION_CRASHED_VALUE,
        )
        self.assertFalse(
            cavity.characterization_running,
        )

    def test_characterization_crashed(self):
        cavity = next(cavity_iterator)
        cavity._characterization_status_pv_obj = make_mock_pv(
            get_val=CHARACTERIZATION_CRASHED_VALUE,
        )
        self.assertTrue(
            cavity.characterization_crashed,
        )

        cavity._characterization_status_pv_obj = make_mock_pv(
            get_val=CHARACTERIZATION_RUNNING_VALUE,
        )
        self.assertFalse(
            cavity.characterization_crashed,
        )

    def test_pulse_on_time(self):
        cavity = next(cavity_iterator)
        cavity._pulse_on_time_pv_obj = make_mock_pv(get_val=70)
        self.assertEqual(cavity.pulse_on_time, 70)

    def test_pulse_status(self):
        cavity = next(cavity_iterator)
        val = randint(0, 5)
        cavity._pulse_status_pv_obj = make_mock_pv(get_val=val)
        self.assertEqual(cavity.pulse_status, val)

    def test_rf_permit(self):
        cavity = next(cavity_iterator)
        cavity._rf_permit_pv_obj = make_mock_pv(get_val=1)
        self.assertEqual(cavity.rf_permit, 1)

    def test_rf_inhibited(self):
        cavity = next(cavity_iterator)
        cavity._rf_permit_pv_obj = make_mock_pv(get_val=1)
        self.assertFalse(cavity.rf_inhibited)

        cavity._rf_permit_pv_obj = make_mock_pv(get_val=0)
        self.assertTrue(cavity.rf_inhibited)

    def test_ades(self):
        cavity = next(cavity_iterator)
        val = randint(0, 21)
        cavity._ades_pv_obj = make_mock_pv(get_val=val)
        self.assertEqual(cavity.ades, val)

    def test_acon(self):
        cavity = next(cavity_iterator)
        val = randint(0, 21)
        cavity._acon_pv_obj = make_mock_pv(get_val=val)
        self.assertEqual(cavity.acon, val)

    def test_aact(self):
        cavity = next(cavity_iterator)
        val = randint(0, 21)
        cavity._aact_pv_obj = make_mock_pv(get_val=val)
        self.assertEqual(cavity.aact, val)

    def test_ades_max(self):
        cavity = next(cavity_iterator)
        val = randint(0, 21)
        cavity._ades_max_pv_obj = make_mock_pv(get_val=val)
        self.assertEqual(cavity.ades_max, val)

    def test_edm_macro_string(self):
        cavity = MACHINE.cryomodules["01"].cavities[1]
        self.assertEqual(
            cavity.edm_macro_string, "C=1,RFS=1A,R=A,CM=ACCL:L0B:01,ID=01,CH=1"
        )

    def test_edm_macro_string_rack_b(self):
        cav = MACHINE.cryomodules["01"].cavities[5]
        self.assertEqual(
            cav.edm_macro_string, "C=5,RFS=1B,R=B,CM=ACCL:L0B:01,ID=01,CH=1"
        )

    def test_hw_mode(self):
        cavity = next(cavity_iterator)
        cavity._hw_mode_pv_obj = make_mock_pv(get_val=HW_MODE_ONLINE_VALUE)
        self.assertEqual(cavity.hw_mode, HW_MODE_ONLINE_VALUE)

    def test_is_online(self):
        cavity = next(cavity_iterator)
        cavity._hw_mode_pv_obj = make_mock_pv(get_val=HW_MODE_ONLINE_VALUE)
        self.assertTrue(cavity.is_online)

        cavity._hw_mode_pv_obj = make_mock_pv(get_val=HW_MODE_OFFLINE_VALUE)
        self.assertFalse(cavity.is_online)

    def test_chirp_freq_start(self):
        cavity = next(cavity_iterator)
        val = -200000
        cavity._chirp_freq_start_pv_obj = make_mock_pv(get_val=val)
        self.assertEqual(cavity.chirp_freq_start, val)

        new_val = -400000
        cavity.chirp_freq_start = new_val
        cavity._chirp_freq_start_pv_obj.put.assert_called_with(new_val)

    def test_chirp_freq_stop(self):
        cavity = next(cavity_iterator)
        val = 200000
        cavity._freq_stop_pv_obj = make_mock_pv(get_val=val)
        self.assertEqual(cavity.chirp_freq_stop, val)

        new_val = 400000
        cavity.chirp_freq_stop = new_val
        cavity._freq_stop_pv_obj.put.assert_called_with(new_val)

    def test_calculate_probe_q(self):
        cavity = next(cavity_iterator)
        cavity._calc_probe_q_pv_obj = make_mock_pv()
        cavity.calculate_probe_q()
        cavity._calc_probe_q_pv_obj.put.assert_called_with(1)

    def test_set_chirp_range(self):
        cavity = next(cavity_iterator)
        cavity._chirp_freq_start_pv_obj = make_mock_pv()
        cavity._freq_stop_pv_obj = make_mock_pv()
        offset = randint(-400000, 0)
        cavity.set_chirp_range(offset)
        cavity._chirp_freq_start_pv_obj.put.assert_called_with(offset)
        cavity._freq_stop_pv_obj.put.assert_called_with(-offset)

    def test_rf_state(self):
        cavity = next(cavity_iterator)
        cavity._rf_state_pv_obj = make_mock_pv(get_val=1)
        self.assertEqual(cavity.rf_state, 1)

    def test_is_on(self):
        cavity = next(cavity_iterator)
        cavity._rf_state_pv_obj = make_mock_pv(get_val=1)
        self.assertTrue(cavity.is_on)

        cavity._rf_state_pv_obj = make_mock_pv(cavity.rf_state_pv, get_val=0)
        self.assertFalse(cavity.is_on)

    def mock_detune(self):
        """
        Ham-fisted way of having the cavity report as detuned the first loop
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
        cavity = next(cavity_iterator)
        val = randint(-400000, 400000)
        cavity._detune_best_pv_obj = make_mock_pv(get_val=val)
        self.assertEqual(cavity.detune_best, val)

    def test_detune_chirp(self):
        cavity = next(cavity_iterator)
        val = randint(-400000, 400000)
        cavity._detune_chirp_pv_obj = make_mock_pv(get_val=val)
        self.assertEqual(cavity.detune_chirp, val)

    def test_detune(self):
        cavity = next(cavity_iterator)
        cavity._rf_mode_pv_obj = make_mock_pv(get_val=RF_MODE_SELA)
        val = randint(-400000, 400000)
        cavity._detune_best_pv_obj = make_mock_pv(get_val=val)
        self.assertEqual(cavity.detune, val)

    def test_detune_in_chirp(self):
        cavity = next(cavity_iterator)
        cavity._rf_mode_pv_obj = make_mock_pv(get_val=RF_MODE_CHIRP)
        val = randint(-400000, 400000)
        cavity._detune_chirp_pv_obj = make_mock_pv(get_val=val)
        self.assertEqual(cavity.detune, val)

    def test_detune_invalid(self):
        cavity = next(cavity_iterator)
        cavity._detune_best_pv_obj = make_mock_pv(severity=EPICS_INVALID_VAL)
        cavity._rf_mode_pv_obj = make_mock_pv(get_val=RF_MODE_SELA)
        self.assertTrue(cavity.detune_invalid)

        cavity._detune_best_pv_obj.severity = EPICS_NO_ALARM_VAL
        self.assertFalse(cavity.detune_invalid)

    def test_detune_invalid_chirp(self):
        cavity = next(cavity_iterator)
        cavity._detune_chirp_pv_obj = make_mock_pv(severity=EPICS_INVALID_VAL)
        cavity._rf_mode_pv_obj = make_mock_pv(get_val=RF_MODE_CHIRP)
        self.assertTrue(cavity.detune_invalid)

        cavity._detune_chirp_pv_obj.severity = EPICS_NO_ALARM_VAL
        self.assertFalse(cavity.detune_invalid)

    def test__auto_tune_invalid(self):
        cavity = next(cavity_iterator)
        """
        TODO figure out how to test the guts when detune > tolerance
        """
        cavity._rf_mode_pv_obj = make_mock_pv(get_val=RF_MODE_CHIRP)
        cavity._detune_chirp_pv_obj = make_mock_pv(severity=EPICS_INVALID_VAL)

        # delta_hz_func argument is unnecessary
        self.assertRaises(DetuneError, cavity._auto_tune, None)

    def test__auto_tune_out_of_tol(self):
        cavity = next(cavity_iterator)
        cavity._rf_mode_pv_obj = make_mock_pv(get_val=RF_MODE_CHIRP)
        cavity._detune_chirp_pv_obj = make_mock_pv(severity=EPICS_NO_ALARM_VAL)
        cavity.stepper_tuner.move = MagicMock()
        cavity.stepper_tuner._hz_per_microstep_pv_obj = make_mock_pv(
            get_val=self.hz_per_microstep
        )
        cavity._tune_config_pv_obj = make_mock_pv(get_val=HW_MODE_ONLINE_VALUE)

        self.detune_calls = 0
        cavity._auto_tune(delta_hz_func=self.mock_detune)
        cavity.stepper_tuner.move.assert_called()
        self.assertEqual(self.detune_calls, 2)

    def test_check_detune(self):
        cavity = next(cavity_iterator)
        cavity._rf_mode_pv_obj = make_mock_pv(get_val=RF_MODE_CHIRP)
        cavity._detune_chirp_pv_obj = make_mock_pv(severity=EPICS_INVALID_VAL)
        cavity._chirp_freq_start_pv_obj = make_mock_pv(
            cavity.chirp_freq_start_pv, get_val=50000
        )
        cavity.find_chirp_range = MagicMock()
        cavity.check_detune()
        cavity.find_chirp_range.assert_called_with(50000 * 1.1)

    def test_check_detune_sela(self):
        cavity = next(cavity_iterator)
        cavity._rf_mode_pv_obj = make_mock_pv(get_val=RF_MODE_SELA)
        cavity._detune_best_pv_obj = make_mock_pv(severity=EPICS_INVALID_VAL)
        self.assertRaises(DetuneError, cavity.check_detune)

    def test_check_and_set_on_time(self):
        cavity = next(cavity_iterator)
        cavity._pulse_on_time_pv_obj = make_mock_pv(
            cavity.pulse_on_time_pv, NOMINAL_PULSED_ONTIME * 0.9
        )
        cavity.push_go_button = MagicMock()
        cavity.check_and_set_on_time()
        cavity._pulse_on_time_pv_obj.put.assert_called_with(NOMINAL_PULSED_ONTIME)
        cavity.push_go_button.assert_called()

    def test_push_go_button(self):
        cavity = next(cavity_iterator)
        cavity._pulse_status_pv_obj = make_mock_pv(cavity.pulse_status_pv, get_val=2)
        cavity._pulse_go_pv_obj = make_mock_pv(cavity.pulse_go_pv)
        cavity.push_go_button()
        cavity._pulse_go_pv_obj.put.assert_called_with(1)

    def test_turn_on_not_online(self):
        cavity = next(cavity_iterator)
        for hw_status in range(1, 5):
            cavity._hw_mode_pv_obj = make_mock_pv(get_val=hw_status)
            self.assertRaises(CavityHWModeError, cavity.turn_on)

    def test_turn_on(self):
        cavity = next(cavity_iterator)
        cavity._hw_mode_pv_obj = make_mock_pv(get_val=HW_MODE_ONLINE_VALUE)
        cavity.ssa.turn_on = MagicMock()
        cavity.reset_interlocks = MagicMock()
        cavity._rf_state_pv_obj = make_mock_pv(cavity.rf_state_pv, get_val=1)
        cavity._rf_control_pv_obj = make_mock_pv()

        cavity.turn_on()
        cavity.ssa.turn_on.assert_called()
        cavity.reset_interlocks.assert_called()
        cavity._rf_state_pv_obj.get.assert_called()
        cavity._rf_control_pv_obj.put.assert_called_with(1)

    def test_turn_off(self):
        cavity = next(cavity_iterator)
        cavity._rf_control_pv_obj = make_mock_pv()
        cavity._rf_state_pv_obj = make_mock_pv(get_val=0)
        cavity.turn_off()
        cavity._rf_control_pv_obj.put.assert_called_with(0)
        cavity._rf_state_pv_obj.get.assert_called()

    def test_setup_selap(self):
        cavity = next(cavity_iterator)
        cavity.setup_rf = MagicMock()
        cavity.set_selap_mode = MagicMock()
        cavity.setup_selap(5)
        cavity.setup_rf.assert_called_with(5)
        cavity.set_selap_mode.assert_called()

    def test_setup_sela(self):
        cavity = next(cavity_iterator)
        cavity.setup_rf = MagicMock()
        cavity.set_sela_mode = MagicMock()
        cavity.setup_sela(5)
        cavity.setup_rf.assert_called_with(5)
        cavity.set_sela_mode.assert_called()

    def test_check_abort(self):
        cavity = next(cavity_iterator)
        cavity.abort_flag = True
        cavity._rf_control_pv_obj = make_mock_pv()
        cavity._rf_state_pv_obj = make_mock_pv(get_val=0)
        self.assertRaises(CavityAbortError, cavity.check_abort)

        try:
            cavity.abort_flag = False
            cavity.check_abort()
        except CavityAbortError:
            self.fail("Cavity abort error raised when flag not set")

    def test_setup_rf(self):
        cavity = next(cavity_iterator)
        cavity.turn_off = MagicMock()
        cavity.ssa.calibrate = MagicMock()
        cavity._ades_max_pv_obj = make_mock_pv(get_val=21)
        cavity.ssa._saved_drive_max_pv_obj = make_mock_pv(get_val=0.8)
        cavity.move_to_resonance = MagicMock()
        cavity.characterize = MagicMock()
        cavity.calculate_probe_q = MagicMock()
        cavity.reset_data_decimation = MagicMock()
        cavity.check_abort = MagicMock()
        cavity._ades_pv_obj = make_mock_pv(get_val=5)
        cavity.set_sel_mode = MagicMock()
        cavity.piezo.enable_feedback = MagicMock()
        cavity.set_sela_mode = MagicMock()
        cavity.walk_amp = MagicMock()

        cavity.setup_rf(5)
        cavity.ssa.calibrate.assert_called()

    def test_reset_data_decimation(self):
        cavity = next(cavity_iterator)
        cavity._cw_data_decim_pv_obj = make_mock_pv()
        cavity._pulsed_data_decim_pv_obj = make_mock_pv()
        cavity.reset_data_decimation()
        cavity._cw_data_decim_pv_obj.put.assert_called_with(255)
        cavity._pulsed_data_decim_pv_obj.put.assert_called_with(255)

    def test_setup_tuning_sela(self):
        cavity = next(cavity_iterator)
        cavity.piezo.enable = MagicMock()
        cavity.piezo.enable_feedback = MagicMock()
        cavity.set_sela_mode = MagicMock()
        cavity.turn_on = MagicMock()

        cavity.setup_tuning(use_sela=True)
        cavity.piezo.enable.assert_called()
        cavity.piezo.enable_feedback.assert_called()
        cavity.turn_on.assert_called()

    def test_setup_tuning_not_sela(self):
        cavity = next(cavity_iterator)
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
        cavity = next(cavity_iterator)
        cavity.set_chirp_range = MagicMock()
        cavity._rf_mode_pv_obj = make_mock_pv(get_val=RF_MODE_CHIRP)
        cavity._detune_chirp_pv_obj = make_mock_pv(severity=EPICS_NO_ALARM_VAL)

        cavity.find_chirp_range(50000)
        cavity.set_chirp_range.assert_called_with(50000)

    def test_reset_interlocks(self):
        cavity = next(cavity_iterator)
        cavity._interlock_reset_pv_obj = make_mock_pv()
        cavity._rf_permit_pv_obj = make_mock_pv(get_val=0)
        self.assertRaises(
            CavityFaultError,
            cavity.reset_interlocks,
            attempt=INTERLOCK_RESET_ATTEMPTS,
        )
        cavity._interlock_reset_pv_obj.put.assert_called_with(1)

    def test_characterization_timestamp(self):
        cavity = next(cavity_iterator)
        cavity._char_timestamp_pv_obj = make_mock_pv(get_val="2024-04-11-15:17:17")
        self.assertEqual(
            cavity.characterization_timestamp, datetime(2024, 4, 11, 15, 17, 17)
        )

    def test_characterize(self):
        """
        TODO test characterization running
        """
        cavity = next(cavity_iterator)
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
        cavity = next(cavity_iterator)
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
        cavity = next(cavity_iterator)
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
        cavity = next(cavity_iterator)
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
        cavity = next(cavity_iterator)
        cavity._ades_pv_obj = make_mock_pv(get_val=0)
        cavity._quench_latch_pv_obj = make_mock_pv(get_val=1)
        cavity._ades_pv_obj = make_mock_pv(get_val=16)
        self.assertRaises(QuenchError, cavity.walk_amp, 16.6, 0.1)

    def test_walk_amp(self):
        cavity = next(cavity_iterator)
        cavity._quench_latch_pv_obj = make_mock_pv(get_val=0)
        cavity._ades_pv_obj = make_mock_pv(get_val=16.05)
        cavity.walk_amp(16.1, 0.1)
        cavity._ades_pv_obj.put.assert_called_with(16.1)
