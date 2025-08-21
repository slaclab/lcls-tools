from random import randint, uniform
from unittest import TestCase
from unittest.mock import MagicMock

from lcls_tools.common.controls.epics import make_mock_pv
from lcls_tools.superconducting.sc_linac import CavityIterator, MACHINE
from lcls_tools.superconducting.sc_linac_utils import (
    SSA_STATUS_ON_VALUE,
    SSA_STATUS_RESETTING_FAULTS_VALUE,
    SSA_STATUS_FAULTED_VALUE,
    SSA_STATUS_FAULT_RESET_FAILED_VALUE,
    SSACalibrationError,
    SSAFaultError,
    SSA_CALIBRATION_RUNNING_VALUE,
    SSA_CALIBRATION_CRASHED_VALUE,
    SSA_RESULT_GOOD_STATUS_VALUE,
    SSA_SLOPE_LOWER_LIMIT,
    SSA_SLOPE_UPPER_LIMIT,
    SSACalibrationToleranceError,
)

cavity_iterator = CavityIterator()


class TestSSA(TestCase):
    def test_pv_prefix(self):
        ssa = MACHINE.cryomodules["01"].cavities[1].ssa
        self.assertEqual(ssa.pv_prefix, "ACCL:L0B:0110:SSA:")

    def test_pv_addr(self):
        ssa = MACHINE.cryomodules["01"].cavities[1].ssa
        suffix = "test"
        self.assertEqual(ssa.pv_addr(suffix), f"ACCL:L0B:0110:SSA:{suffix}")

    def test_status_message(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        ssa._status_pv_obj = make_mock_pv(get_val=SSA_STATUS_ON_VALUE)
        self.assertEqual(ssa.status_message, SSA_STATUS_ON_VALUE)

    def test_is_on(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        status = randint(0, 11)
        ssa._status_pv_obj = make_mock_pv(get_val=status)
        if status == SSA_STATUS_ON_VALUE:
            self.assertTrue(ssa.is_on)
        else:
            self.assertFalse(ssa.is_on)

    def test_is_resetting(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        status = randint(0, 11)
        ssa._status_pv_obj = make_mock_pv(get_val=status)
        if status == SSA_STATUS_RESETTING_FAULTS_VALUE:
            self.assertTrue(ssa.is_resetting)
        else:
            self.assertFalse(ssa.is_resetting)

    def test_is_faulted(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        status = randint(0, 11)
        ssa._status_pv_obj = make_mock_pv(get_val=status)
        if status in [
            SSA_STATUS_FAULTED_VALUE,
            SSA_STATUS_FAULT_RESET_FAILED_VALUE,
        ]:
            self.assertTrue(ssa.is_faulted)
        else:
            self.assertFalse(ssa.is_faulted)

    def test_max_fwd_pwr(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        pwr = randint(2000, 4000)
        ssa._max_fwd_pwr_pv_obj = make_mock_pv(get_val=pwr)
        self.assertEqual(ssa.max_fwd_pwr, pwr)

    def test_drive_max_saved(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        drive = uniform(0.5, 1)
        ssa._saved_drive_max_pv_obj = make_mock_pv(get_val=drive)
        self.assertEqual(ssa.drive_max, drive)

    def test_drive_max_not_saved(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        ssa._saved_drive_max_pv_obj = make_mock_pv(get_val=None)
        self.assertEqual(ssa.drive_max, 0.8)

    def test_drive_max_not_saved_hl(self):
        ssa_hl = next(cavity_iterator.hl_iterator).ssa
        ssa_hl._saved_drive_max_pv_obj = make_mock_pv(get_val=None)
        self.assertEqual(ssa_hl.drive_max, 1)

    def test_calibrate_low_drive(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        self.assertRaises(SSACalibrationError, ssa.calibrate, uniform(0, 0.3))

    def test_calibrate(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        ssa.run_calibration = MagicMock()
        ssa._drive_max_setpoint_pv_obj = make_mock_pv()
        drive = uniform(0.5, 1)
        ssa.calibrate(drive)
        ssa._drive_max_setpoint_pv_obj.put.assert_called_with(drive)
        ssa.run_calibration.assert_called()

    def test_ps_volt_setpoint2_pv_obj(self):
        ssa = next(cavity_iterator.hl_iterator).ssa
        ssa._ps_volt_setpoint2_pv_obj = make_mock_pv()
        self.assertEqual(ssa.ps_volt_setpoint2_pv_obj, ssa._ps_volt_setpoint2_pv_obj)

    def test_ps_volt_setpoint1_pv_obj(self):
        ssa = next(cavity_iterator.hl_iterator).ssa
        ssa._ps_volt_setpoint1_pv_obj = make_mock_pv()
        self.assertEqual(ssa.ps_volt_setpoint1_pv_obj, ssa._ps_volt_setpoint1_pv_obj)

    def test_turn_on_pv_obj(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        ssa._turn_on_pv_obj = make_mock_pv()
        self.assertEqual(ssa.turn_on_pv_obj, ssa._turn_on_pv_obj)

    def test_turn_off_pv_obj(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        ssa._turn_off_pv_obj = make_mock_pv()
        self.assertEqual(ssa.turn_off_pv_obj, ssa._turn_off_pv_obj)

    def test_reset_pv_obj(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        ssa._reset_pv_obj = make_mock_pv()
        self.assertEqual(ssa.reset_pv_obj, ssa._reset_pv_obj)

    def test_reset(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        ssa._status_pv_obj = make_mock_pv(get_val=SSA_STATUS_FAULTED_VALUE)
        ssa._reset_pv_obj = make_mock_pv()
        self.assertRaises(SSAFaultError, ssa.reset)
        ssa._reset_pv_obj.put.assert_called_with(1)

    def test_start_calibration(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        ssa._calibration_start_pv_obj = make_mock_pv()
        ssa.start_calibration()
        ssa._calibration_start_pv_obj.put.assert_called_with(1)

    def test_calibration_status(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        status = randint(0, 2)
        ssa._calibration_status_pv_obj = make_mock_pv(get_val=status)
        self.assertEqual(ssa.calibration_status, status)

    def test_calibration_running(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        status = randint(0, 2)
        ssa._calibration_status_pv_obj = make_mock_pv(get_val=status)
        if status == SSA_CALIBRATION_RUNNING_VALUE:
            self.assertTrue(ssa.calibration_running)
        else:
            self.assertFalse(ssa.calibration_running)

    def test_calibration_crashed(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        status = randint(0, 2)
        ssa._calibration_status_pv_obj = make_mock_pv(get_val=status)
        if status == SSA_CALIBRATION_CRASHED_VALUE:
            self.assertTrue(ssa.calibration_crashed)
        else:
            self.assertFalse(ssa.calibration_crashed)

    def test_cal_result_status_pv_obj(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        ssa._cal_result_status_pv_obj = make_mock_pv()
        self.assertEqual(ssa.cal_result_status_pv_obj, ssa._cal_result_status_pv_obj)

    def test_calibration_result_good(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        status = randint(0, 2)
        ssa._cal_result_status_pv_obj = make_mock_pv(get_val=status)
        if status == SSA_RESULT_GOOD_STATUS_VALUE:
            self.assertTrue(ssa.calibration_result_good)
        else:
            self.assertFalse(ssa.calibration_result_good)

    def test_run_calibration(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        ssa.reset = MagicMock()
        ssa.turn_on = MagicMock()
        ssa.cavity.reset_interlocks = MagicMock()
        ssa.start_calibration = MagicMock()
        ssa._calibration_status_pv_obj = make_mock_pv(get_val=1)

        ssa._cal_result_status_pv_obj = make_mock_pv(
            get_val=SSA_RESULT_GOOD_STATUS_VALUE
        )
        ssa._max_fwd_pwr_pv_obj = make_mock_pv(get_val=ssa.fwd_power_lower_limit * 2)
        ssa._measured_slope_pv_obj = make_mock_pv(
            get_val=uniform(SSA_SLOPE_LOWER_LIMIT, SSA_SLOPE_UPPER_LIMIT)
        )
        ssa.cavity.push_ssa_slope = MagicMock()

        ssa.run_calibration()

        ssa.reset.assert_called()
        ssa.turn_on.assert_called()
        ssa.cavity.reset_interlocks.assert_called()
        ssa.start_calibration.assert_called()
        ssa.cavity.push_ssa_slope.assert_called()

    def test_run_calibration_crashed(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        ssa.reset = MagicMock()
        ssa.turn_on = MagicMock()
        ssa.cavity.reset_interlocks = MagicMock()
        ssa.start_calibration = MagicMock()
        ssa._calibration_status_pv_obj = make_mock_pv(
            get_val=SSA_CALIBRATION_CRASHED_VALUE
        )
        self.assertRaises(SSACalibrationError, ssa.run_calibration)

    def test_run_calibration_bad_result(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        ssa.reset = MagicMock()
        ssa.turn_on = MagicMock()
        ssa.cavity.reset_interlocks = MagicMock()
        ssa.start_calibration = MagicMock()
        ssa._calibration_status_pv_obj = make_mock_pv(get_val=1)
        ssa._cal_result_status_pv_obj = make_mock_pv(get_val=1)
        self.assertRaises(SSACalibrationError, ssa.run_calibration)

    def test_run_calibration_low_fwd_pwr(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        ssa.reset = MagicMock()
        ssa.turn_on = MagicMock()
        ssa.cavity.reset_interlocks = MagicMock()
        ssa.start_calibration = MagicMock()
        ssa._calibration_status_pv_obj = make_mock_pv(get_val=1)
        ssa._cal_result_status_pv_obj = make_mock_pv(
            get_val=SSA_RESULT_GOOD_STATUS_VALUE
        )
        ssa._max_fwd_pwr_pv_obj = make_mock_pv(get_val=ssa.fwd_power_lower_limit / 2)
        self.assertRaises(SSACalibrationToleranceError, ssa.run_calibration)

    def test_run_calibration_bad_slope(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        ssa.reset = MagicMock()
        ssa.turn_on = MagicMock()
        ssa.cavity.reset_interlocks = MagicMock()
        ssa.start_calibration = MagicMock()
        ssa._calibration_status_pv_obj = make_mock_pv(get_val=1)
        ssa._cal_result_status_pv_obj = make_mock_pv(
            get_val=SSA_RESULT_GOOD_STATUS_VALUE
        )
        ssa._max_fwd_pwr_pv_obj = make_mock_pv(get_val=ssa.fwd_power_lower_limit * 2)
        ssa._measured_slope_pv_obj = make_mock_pv(get_val=SSA_SLOPE_LOWER_LIMIT / 2)
        self.assertRaises(SSACalibrationToleranceError, ssa.run_calibration)

    def test_measured_slope(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        slope = uniform(SSA_SLOPE_LOWER_LIMIT, SSA_SLOPE_UPPER_LIMIT)
        ssa._measured_slope_pv_obj = make_mock_pv(get_val=slope)
        self.assertEqual(ssa.measured_slope, slope)

    def test_measured_slope_in_tolerance(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        slope = uniform(SSA_SLOPE_LOWER_LIMIT, SSA_SLOPE_UPPER_LIMIT)
        ssa._measured_slope_pv_obj = make_mock_pv(get_val=slope)
        self.assertTrue(ssa.measured_slope_in_tolerance)

    def test_measured_slope_low(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        slope = SSA_SLOPE_LOWER_LIMIT / 2
        ssa._measured_slope_pv_obj = make_mock_pv(get_val=slope)
        self.assertFalse(ssa.measured_slope_in_tolerance)

    def test_measured_slope_high(self):
        ssa = next(cavity_iterator.non_hl_iterator).ssa
        slope = SSA_SLOPE_UPPER_LIMIT * 2
        ssa._measured_slope_pv_obj = make_mock_pv(get_val=slope)
        self.assertFalse(ssa.measured_slope_in_tolerance)
