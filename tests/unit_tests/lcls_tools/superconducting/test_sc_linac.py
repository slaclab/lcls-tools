import datetime
from random import randint
from unittest import TestCase
from unittest.mock import MagicMock

from lcls_tools.common.controls.pyepics.utils import (
    EPICS_INVALID_VAL,
    EPICS_NO_ALARM_VAL,
)
from lcls_tools.superconducting.sc_linac import Cavity, MACHINE, StepperTuner
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
)


def make_mock_pv(pv_name: str, get_val=None) -> MagicMock:
    return MagicMock(
        pvname=pv_name,
        put=MagicMock(return_value=1),
        get=MagicMock(return_value=get_val),
    )


class TestCavity(TestCase):
    def setUp(self):
        self.cavity: Cavity = MACHINE.cryomodules["01"].cavities[1]
        self.hl_cavity: Cavity = MACHINE.cryomodules["H1"].cavities[1]
        self.cavity._rf_mode_pv_obj = make_mock_pv(self.cavity.rf_mode_pv)
        self.cavity._rf_mode_ctrl_pv_obj = make_mock_pv(self.cavity.rf_mode_ctrl_pv)
        self.cavity._detune_chirp_pv_obj = make_mock_pv(self.cavity.detune_chirp_pv)
        self.cavity._detune_best_pv_obj = make_mock_pv(self.cavity.detune_best_pv)

        self.hz_per_microstep = 0.00540801
        self.measured_loaded_q = 4.41011e07

    def test_pv_prefix(self):
        self.assertEqual(self.cavity.pv_prefix, "ACCL:L0B:0110:")

    def test_loaded_q_limits(self):
        self.assertEqual(self.cavity.loaded_q_lower_limit, LOADED_Q_LOWER_LIMIT)
        self.assertEqual(self.hl_cavity.loaded_q_lower_limit, LOADED_Q_LOWER_LIMIT_HL)

        self.assertEqual(self.cavity.loaded_q_upper_limit, LOADED_Q_UPPER_LIMIT)
        self.assertEqual(self.hl_cavity.loaded_q_upper_limit, LOADED_Q_UPPER_LIMIT_HL)

    def test_microsteps_per_hz(self):
        self.cavity.stepper_tuner._hz_per_microstep_pv_obj = make_mock_pv(
            self.cavity.stepper_tuner.hz_per_microstep_pv, get_val=self.hz_per_microstep
        )
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
            self.cavity.edm_macro_string, "C=1,RFS=1A,R=A,CM=ACCL:L0B:01,ID=01,CH=1"
        )

    def test_edm_macro_string_rack_b(self):
        cav = MACHINE.cryomodules["01"].cavities[5]
        self.assertEqual(
            cav.edm_macro_string, "C=5,RFS=1B,R=B,CM=ACCL:L0B:01,ID=01,CH=1"
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

    def test_move_to_resonance(self):
        self.fail()
        self.cavity.move_to_resonance()

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

    def test__auto_tune(self):
        self.cavity._rf_mode_pv_obj.get = MagicMock(return_value=RF_MODE_CHIRP)
        self.cavity._detune_chirp_pv_obj.severity = EPICS_INVALID_VAL
        self.assertRaises(DetuneError, self.cavity._auto_tune, None)

    def test_check_detune(self):
        self.fail()

    def test_check_and_set_on_time(self):
        self.fail()

    def test_push_go_button(self):
        self.fail()

    def test_turn_on(self):
        self.fail()

    def test_turn_off(self):
        self.fail()

    def test_setup_selap(self):
        self.fail()

    def test_setup_sela(self):
        self.fail()

    def test_check_abort(self):
        self.fail()

    def test_setup_rf(self):
        self.fail()

    def test_reset_data_decimation(self):
        self.fail()

    def test_setup_tuning(self):
        self.fail()

    def test_find_chirp_range(self):
        self.fail()

    def test_reset_interlocks(self):
        self.fail()

    def test_characterization_timestamp(self):
        self.fail()

    def test_characterize(self):
        self.fail()

    def test_finish_characterization(self):
        self.fail()

    def test_walk_amp(self):
        self.fail()


class TestStepperTuner(TestCase):
    def setUp(self):
        self.stepper_tuner: StepperTuner = (
            MACHINE.cryomodules["02"].cavities[2].stepper_tuner
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
