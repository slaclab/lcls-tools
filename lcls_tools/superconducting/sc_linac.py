################################################################################
# Utility classes for superconducting linac
# NOTE: For some reason, using python 3 style type annotations causes circular
#       import issues, so leaving as python 2 style for now
################################################################################
from datetime import datetime
from time import sleep
from typing import Callable, Dict, List, Optional, Type

from numpy import sign

import lcls_tools.superconducting.sc_linac_utils as utils
from lcls_tools.common.controls.pyepics.utils import EPICS_INVALID_VAL, PV


class SSA(utils.SCLinacObject):
    """
    Python representation of LCLS II SSAs. This class provides utility functions
    for powering off/on, resetting, and calibrating

    """

    def __init__(self, cavity):
        # type: (Cavity) -> None
        """
        @param cavity: the cavity object powered by this SSA
        """

        self.cavity: Cavity = cavity
        self._pv_prefix = self.cavity.pv_addr("SSA:")

        # HL cryomodules only have 4 physical SSAs such that they each power two
        # cavities (SSA 1 powers cavities 1 and 5, SSA 2 powers cavities 2 and 6,
        # etc.) Because of that, HL cavities have a subset of shared SSA
        # controls (on/off/reset/voltage). HL SSAs also have a lower expected
        # forward power.
        if self.cavity.cryomodule.is_harmonic_linearizer:
            cavity_num = utils.HL_SSA_MAP[self.cavity.number]
            self.hl_prefix = "ACCL:{LINAC}:{CRYOMODULE}{CAVITY}0:SSA:".format(
                LINAC=self.cavity.linac.name,
                CRYOMODULE=self.cavity.cryomodule.name,
                CAVITY=cavity_num,
            )
            self.fwd_power_lower_limit = 500

            self.ps_volt_setpoint1_pv: str = self.hl_prefix + "PSVoltSetpt1"
            self._ps_volt_setpoint1_pv_obj: Optional[PV] = None

            self.ps_volt_setpoint2_pv: str = self.hl_prefix + "PSVoltSetpt2"
            self._ps_volt_setpoint2_pv_obj: Optional[PV] = None

            self.status_pv: str = self.hl_prefix + "StatusMsg"
            self.turn_on_pv: str = self.hl_prefix + "PowerOn"
            self.turn_off_pv: str = self.hl_prefix + "PowerOff"
            self.reset_pv: str = self.hl_prefix + "FaultReset"

        else:
            self.fwd_power_lower_limit = 3000
            self.status_pv: str = self.pv_addr("StatusMsg")
            self.turn_on_pv: str = self.pv_addr("PowerOn")
            self.turn_off_pv: str = self.pv_addr("PowerOff")
            self.reset_pv: str = self.pv_addr("FaultReset")

        self._status_pv_obj: Optional[PV] = None
        self._turn_on_pv_obj: Optional[PV] = None
        self._turn_off_pv_obj: Optional[PV] = None
        self._reset_pv_obj: Optional[PV] = None

        self.calibration_start_pv: str = self.pv_addr("CALSTRT")
        self._calibration_start_pv_obj: Optional[PV] = None

        self.calibration_status_pv: str = self.pv_addr("CALSTS")
        self._calibration_status_pv_obj: Optional[PV] = None

        self.cal_result_status_pv: str = self.pv_addr("CALSTAT")
        self._cal_result_status_pv_obj: Optional[PV] = None

        self.current_slope_pv: str = self.pv_addr("SLOPE")

        self.measured_slope_pv: str = self.pv_addr("SLOPE_NEW")
        self._measured_slope_pv_obj: Optional[PV] = None

        self.drive_max_setpoint_pv: str = self.pv_addr("DRV_MAX_REQ")
        self._drive_max_setpoint_pv_obj: Optional[PV] = None

        self.saved_drive_max_pv: str = self.pv_addr("DRV_MAX_SAVE")
        self._saved_drive_max_pv_obj: Optional[PV] = None

        self.max_fwd_pwr_pv: str = self.pv_addr("CALPWR")
        self._max_fwd_pwr_pv_obj: Optional[PV] = None

    def __str__(self):
        return f"{self.cavity} SSA"

    @property
    def pv_prefix(self):
        return self._pv_prefix

    def pv_addr(self, suffix: str):
        """
        @param suffix: The specific PV signal to be appended to the appropriate
                       prefix (that will depend on if the signal is shared
                       between HL SSAs)
        @return: Full PV address of the form ACCL:L{X}B:{CM}{CAV}0:SSA:SUFFIX
        """
        if (
            self.cavity.cryomodule.is_harmonic_linearizer
            and suffix in utils.HL_SSA_SHARED_PVS
        ):
            return self.hl_prefix + suffix
        else:
            return self.pv_prefix + suffix

    @property
    def status_message(self):
        if not self._status_pv_obj:
            self._status_pv_obj = PV(self.status_pv)
        return self._status_pv_obj.get()

    @property
    def is_on(self) -> bool:
        return self.status_message == utils.SSA_STATUS_ON_VALUE

    @property
    def is_resetting(self) -> bool:
        return self.status_message == utils.SSA_STATUS_RESETTING_FAULTS_VALUE

    @property
    def is_faulted(self) -> bool:
        return self.status_message in [
            utils.SSA_STATUS_FAULTED_VALUE,
            utils.SSA_STATUS_FAULT_RESET_FAILED_VALUE,
        ]

    @property
    def max_fwd_pwr(self):
        if not self._max_fwd_pwr_pv_obj:
            self._max_fwd_pwr_pv_obj = PV(self.max_fwd_pwr_pv)
        return self._max_fwd_pwr_pv_obj.get()

    @property
    def drive_max(self):
        if not self._saved_drive_max_pv_obj:
            self._saved_drive_max_pv_obj = PV(self.saved_drive_max_pv)
        saved_val = self._saved_drive_max_pv_obj.get()
        return (
            saved_val
            if saved_val
            else (1 if self.cavity.cryomodule.is_harmonic_linearizer else 0.8)
        )

    @drive_max.setter
    def drive_max(self, value: float):
        if not self._drive_max_setpoint_pv_obj:
            self._drive_max_setpoint_pv_obj = PV(self.drive_max_setpoint_pv)
        self._drive_max_setpoint_pv_obj.put(value)

    def calibrate(self, drive_max, attempt=0):
        """
        @param drive_max: drive max to use for SSA calibration
        @param attempt: recursively incremented upon calibration failure
        @return: None
        """
        print(f"Trying {self} calibration with drive max {drive_max}")
        if drive_max < 0.4:
            raise utils.SSACalibrationError(f"Requested {self} drive max too low")

        print(f"Setting {self} max drive")
        self.drive_max = drive_max

        try:
            self.cavity.check_abort()
            self.run_calibration()

        except (utils.SSACalibrationToleranceError, utils.SSACalibrationError) as e:
            if attempt < 3:
                self.calibrate(drive_max, attempt + 1)
            else:
                raise utils.SSACalibrationError(e)

    @property
    def ps_volt_setpoint2_pv_obj(self):
        if not self._ps_volt_setpoint2_pv_obj:
            self._ps_volt_setpoint2_pv_obj = PV(self.ps_volt_setpoint2_pv)
        return self._ps_volt_setpoint2_pv_obj

    @property
    def ps_volt_setpoint1_pv_obj(self):
        if not self._ps_volt_setpoint1_pv_obj:
            self._ps_volt_setpoint1_pv_obj = PV(self.ps_volt_setpoint1_pv)
        return self._ps_volt_setpoint1_pv_obj

    @property
    def turn_on_pv_obj(self) -> PV:
        if not self._turn_on_pv_obj:
            self._turn_on_pv_obj = PV(self.turn_on_pv)
        return self._turn_on_pv_obj

    def turn_on(self):
        if not self.is_on:
            # Check to see if SSA is hard faulted first (self.reset() tries a set
            # number of times before raising an error)
            self.reset()

            print(f"Turning {self} on")
            self.turn_on_pv_obj.put(1)

            while not self.is_on:
                self.cavity.check_abort()
                print(f"waiting for {self} to turn on")
                sleep(1)

        if self.cavity.cryomodule.is_harmonic_linearizer:
            self.ps_volt_setpoint2_pv_obj.put(utils.HL_SSA_PS_SETPOINT)
            self.ps_volt_setpoint1_pv_obj.put(utils.HL_SSA_PS_SETPOINT)

        print(f"{self} on")

    @property
    def turn_off_pv_obj(self) -> PV:
        if not self._turn_off_pv_obj:
            self._turn_off_pv_obj = PV(self.turn_off_pv)
        return self._turn_off_pv_obj

    def turn_off(self):
        if self.is_on:
            print(f"Turning {self} off")
            self.turn_off_pv_obj.put(1)

            while self.is_on:
                self.cavity.check_abort()
                print(f"waiting for {self} to turn off")
                sleep(1)

        print(f"{self} off")

    @property
    def reset_pv_obj(self) -> PV:
        if not self._reset_pv_obj:
            self._reset_pv_obj = PV(self.reset_pv)
        return self._reset_pv_obj

    def reset(self):
        reset_attempt = 0
        while self.is_faulted:
            print(f"Resetting {self}...")
            self.reset_pv_obj.put(1)

            while self.is_resetting:
                sleep(1)

            if self.is_faulted and reset_attempt >= utils.INTERLOCK_RESET_ATTEMPTS:
                raise utils.SSAFaultError(
                    f"{self} failed to reset {utils.INTERLOCK_RESET_ATTEMPTS}x"
                )

            reset_attempt += 1

        print(f"{self} reset")

    def start_calibration(self):
        if not self._calibration_start_pv_obj:
            self._calibration_start_pv_obj = PV(self.calibration_start_pv)
        self._calibration_start_pv_obj.put(1)

    @property
    def calibration_status(self):
        if not self._calibration_status_pv_obj:
            self._calibration_status_pv_obj = PV(self.calibration_status_pv)
        return self._calibration_status_pv_obj.get()

    @property
    def calibration_running(self) -> bool:
        return self.calibration_status == utils.SSA_CALIBRATION_RUNNING_VALUE

    @property
    def calibration_crashed(self) -> bool:
        return self.calibration_status == utils.SSA_CALIBRATION_CRASHED_VALUE

    @property
    def cal_result_status_pv_obj(self) -> PV:
        if not self._cal_result_status_pv_obj:
            self._cal_result_status_pv_obj = PV(self.cal_result_status_pv)
        return self._cal_result_status_pv_obj

    @property
    def calibration_result_good(self) -> bool:
        return self.cal_result_status_pv_obj.get() == utils.SSA_RESULT_GOOD_STATUS_VALUE

    def run_calibration(self, save_slope: bool = False):
        """
        Runs the SSA through its range and finds the slope that describes
        the relationship between SSA drive signal and output power
        @param save_slope: Whether to update the saved slope PV with the newly
                           calculated value or not
        @return: None
        """

        self.reset()
        self.turn_on()

        self.cavity.reset_interlocks()

        print(f"Starting {self} calibration")
        self.start_calibration()
        sleep(2)

        while self.calibration_running:
            print(f"waiting for {self} calibration to stop running", datetime.now())
            sleep(1)
        sleep(2)

        if self.calibration_crashed:
            raise utils.SSACalibrationError(f"{self} calibration crashed")

        if not self.calibration_result_good:
            raise utils.SSACalibrationError(f"{self} calibration result not good")

        if self.max_fwd_pwr < self.fwd_power_lower_limit:
            raise utils.SSACalibrationToleranceError(
                f"{self.cavity} SSA forward power too low"
            )

        if not self.measured_slope_in_tolerance:
            raise utils.SSACalibrationToleranceError(
                f"{self.cavity} SSA Slope out of tolerance"
            )

        print(f"Pushing SSA calibration results for {self.cavity}")
        self.cavity.push_ssa_slope()

        if save_slope:
            self.cavity.save_ssa_slope()

    @property
    def measured_slope(self):
        if not self._measured_slope_pv_obj:
            self._measured_slope_pv_obj = PV(self.measured_slope_pv)
        return self._measured_slope_pv_obj.get()

    @property
    def measured_slope_in_tolerance(self) -> bool:
        return (
            utils.SSA_SLOPE_LOWER_LIMIT
            < self.measured_slope
            < utils.SSA_SLOPE_UPPER_LIMIT
        )


class StepperTuner(utils.SCLinacObject):
    """
    Python representation of LCLS II stepper tuners. This class provides wrappers
    for common stepper controls including sending move commands, checking movement
    status, and retrieving stored movement parameters
    """

    def __init__(self, cavity):
        # type (Cavity) -> None
        """
        @param cavity: the cavity object tuned by this stepper
        """

        self.cavity: Cavity = cavity
        self._pv_prefix: str = self.cavity.pv_addr("STEP:")

        self.move_pos_pv: str = self.pv_addr("MOV_REQ_POS")
        self._move_pos_pv_obj: Optional[PV] = None

        self.move_neg_pv: str = self.pv_addr("MOV_REQ_NEG")
        self._move_neg_pv_obj: Optional[PV] = None

        self.abort_pv: str = self.pv_addr("ABORT_REQ")
        self._abort_pv_obj: Optional[PV] = None

        self.step_des_pv: str = self.pv_addr("NSTEPS")
        self._step_des_pv_obj: Optional[PV] = None

        self.max_steps_pv: str = self.pv_addr("NSTEPS.DRVH")
        self._max_steps_pv_obj: Optional[PV] = None

        self.speed_pv: str = self.pv_addr("VELO")
        self._speed_pv_obj: Optional[PV] = None

        self.step_tot_pv: str = self.pv_addr("REG_TOTABS")
        self.step_signed_pv: str = self.pv_addr("REG_TOTSGN")
        self.reset_tot_pv: str = self.pv_addr("TOTABS_RESET")

        self.reset_signed_pv: str = self.pv_addr("TOTSGN_RESET")
        self._reset_signed_pv_obj: Optional[PV] = None

        self.steps_cold_landing_pv: str = self.pv_addr("NSTEPS_COLD")
        self.push_signed_cold_pv: str = self.pv_addr("PUSH_NSTEPS_COLD.PROC")
        self.push_signed_park_pv: str = self.pv_addr("PUSH_NSTEPS_PARK.PROC")

        self.motor_moving_pv: str = self.pv_addr("STAT_MOV")
        self._motor_moving_pv_obj: Optional[PV] = None

        self.motor_done_pv: str = self.pv_addr("STAT_DONE")

        self.limit_switch_a_pv: str = self.pv_addr("STAT_LIMA")
        self._limit_switch_a_pv_obj: Optional[PV] = None

        self.limit_switch_b_pv: str = self.pv_addr("STAT_LIMB")
        self._limit_switch_b_pv_obj: Optional[PV] = None

        self.hz_per_microstep_pv: str = self.pv_addr("SCALE")
        self._hz_per_microstep_pv_obj: Optional[PV] = None

        self.abort_flag: bool = False

    def __str__(self):
        return f"{self.cavity} Stepper Tuner"

    @property
    def pv_prefix(self):
        return self._pv_prefix

    @property
    def hz_per_microstep_pv_obj(self) -> PV:
        if not self._hz_per_microstep_pv_obj:
            self._hz_per_microstep_pv_obj = PV(self.hz_per_microstep_pv)
        return self._hz_per_microstep_pv_obj

    @property
    def hz_per_microstep(self):
        return abs(self.hz_per_microstep_pv_obj.get())

    def check_abort(self):
        """
        This function raises an error if either a stepper abort or a cavity abort
        has been requested.
        @return: None
        """
        self.cavity.check_abort()
        if self.abort_flag:
            self.abort()
            self.abort_flag = False
            raise utils.StepperAbortError(f"Abort requested for {self}")

    def abort(self):
        if not self._abort_pv_obj:
            self._abort_pv_obj = PV(self.abort_pv)
        self._abort_pv_obj.put(1)

    def move_positive(self):
        if not self._move_pos_pv_obj:
            self._move_pos_pv_obj = PV(self.move_pos_pv)
        self._move_pos_pv_obj.put(1)

    def move_negative(self):
        if not self._move_neg_pv_obj:
            self._move_neg_pv_obj = PV(self.move_neg_pv)
        self._move_neg_pv_obj.put(1)

    @property
    def step_des_pv_obj(self):
        if not self._step_des_pv_obj:
            self._step_des_pv_obj = PV(self.step_des_pv)
        return self._step_des_pv_obj

    @property
    def step_des(self):
        return self.step_des_pv_obj.get()

    @step_des.setter
    def step_des(self, value: int):
        self.step_des_pv_obj.put(value)

    @property
    def motor_moving(self) -> bool:
        if not self._motor_moving_pv_obj:
            self._motor_moving_pv_obj = PV(self.motor_moving_pv)
        return self._motor_moving_pv_obj.get() == 1

    def reset_signed_steps(self):
        if not self._reset_signed_pv_obj:
            self._reset_signed_pv_obj = PV(self.reset_signed_pv)
        self._reset_signed_pv_obj.put(0)

    @property
    def limit_switch_a_pv_obj(self):
        if not self._limit_switch_a_pv_obj:
            self._limit_switch_a_pv_obj = PV(self.limit_switch_a_pv)
        return self._limit_switch_a_pv_obj

    @property
    def limit_switch_b_pv_obj(self):
        if not self._limit_switch_b_pv_obj:
            self._limit_switch_b_pv_obj = PV(self.limit_switch_b_pv)
        return self._limit_switch_b_pv_obj

    @property
    def on_limit_switch(self) -> bool:
        return (
            self.limit_switch_a_pv_obj.get() == utils.STEPPER_ON_LIMIT_SWITCH_VALUE
            or self.limit_switch_b_pv_obj.get() == utils.STEPPER_ON_LIMIT_SWITCH_VALUE
        )

    @property
    def max_steps_pv_obj(self) -> PV:
        if not self._max_steps_pv_obj:
            self._max_steps_pv_obj = PV(self.max_steps_pv)
        return self._max_steps_pv_obj

    @property
    def max_steps(self):
        return self.max_steps_pv_obj.get()

    @max_steps.setter
    def max_steps(self, value: int):
        self.max_steps_pv_obj.put(value)

    @property
    def speed_pv_obj(self):
        if not self._speed_pv_obj:
            self._speed_pv_obj = PV(self.speed_pv)
        return self._speed_pv_obj

    @property
    def speed(self):
        return self.speed_pv_obj.get()

    @speed.setter
    def speed(self, value: int):
        self.speed_pv_obj.put(value)

    def restore_defaults(self):
        self.max_steps = utils.DEFAULT_STEPPER_MAX_STEPS
        self.speed = utils.DEFAULT_STEPPER_SPEED

    def move(
        self,
        num_steps: int,
        max_steps: int = utils.DEFAULT_STEPPER_MAX_STEPS,
        speed: int = utils.DEFAULT_STEPPER_SPEED,
        change_limits: bool = True,
        check_detune: bool = True,
    ):
        """
        :param num_steps: positive for increasing cavity length, negative for decreasing
        :param max_steps: the maximum number of steps allowed at once
        :param speed: the speed of the motor in steps/second
        :param change_limits: whether to change the speed and steps
        :param check_detune: whether to check for valid detune after each move
        :return: None
        """

        self.check_abort()
        max_steps = abs(max_steps)

        if change_limits:
            # on the off chance that someone tries to write a negative maximum
            self.max_steps = max_steps

            # make sure that we don't exceed the speed limit as defined by the tuner experts
            self.speed = (
                speed if speed < utils.MAX_STEPPER_SPEED else utils.MAX_STEPPER_SPEED
            )

        if abs(num_steps) <= max_steps:
            print(f"{self.cavity} {abs(num_steps)} steps <= {max_steps} max")
            self.step_des = abs(num_steps)
            self.issue_move_command(num_steps, check_detune=check_detune)
            self.restore_defaults()
        else:
            print(f"{self.cavity} {abs(num_steps)} steps > {max_steps} max")
            self.step_des = max_steps
            self.issue_move_command(num_steps, check_detune=check_detune)
            print(f"{self.cavity} moving {num_steps - (sign(num_steps) * max_steps)}")
            self.move(
                num_steps - (sign(num_steps) * max_steps),
                max_steps,
                speed,
                change_limits=False,
                check_detune=check_detune,
            )

    def issue_move_command(self, num_steps: int, check_detune: bool = True):
        """
        Determine whether to move positive or negative depending on the requested
        number of steps
        @param num_steps: Signed number of steps to move the stepper
        @param check_detune: Whether to check for a valid detune during move
                             (this should only be false when we cannot see
                             cavity frequency, i.e. when we are not at 2 K)
        @return: None
        """

        # this is necessary because the tuners for the HLs move the other direction
        if self.cavity.cryomodule.is_harmonic_linearizer:
            num_steps *= -1

        if sign(num_steps) == 1:
            self.move_positive()
        else:
            self.move_negative()

        print(f"Waiting 5s for {self.cavity} motor to start moving")
        sleep(5)

        while self.motor_moving:
            self.check_abort()
            if check_detune:
                self.cavity.check_detune()
            print(f"{self} motor still moving, waiting 5s", datetime.now())
            sleep(5)

        print(f"{self} motor done moving")

        # the motor can be done moving for good OR bad reasons
        if self.on_limit_switch:
            raise utils.StepperError(f"{self.cavity} stepper motor on limit switch")


class Piezo(utils.SCLinacObject):
    """
    Python representation of LCLS II piezo tuners. This class provides utility
    functions for toggling feedback mode and changing bias voltage and DC offset

    """

    def __init__(self, cavity):
        # type (Cavity) -> None
        """
        @param cavity: The cavity object tuned by this piezo
        """

        self.cavity: Cavity = cavity
        self._pv_prefix: str = self.cavity.pv_addr("PZT:")

        self.enable_pv: str = self.pv_addr("ENABLE")
        self._enable_pv_obj: Optional[PV] = None

        self.enable_stat_pv: str = self.pv_addr("ENABLESTAT")
        self._enable_stat_pv_obj: Optional[PV] = None

        self.feedback_control_pv: str = self.pv_addr("MODECTRL")
        self._feedback_control_pv_obj: Optional[PV] = None

        self.feedback_stat_pv: str = self.pv_addr("MODESTAT")
        self._feedback_stat_pv_obj: Optional[PV] = None

        self.feedback_setpoint_pv: str = self.pv_addr("INTEG_SP")
        self._feedback_setpoint_pv_obj: Optional[PV] = None

        self.dc_setpoint_pv: str = self.pv_addr("DAC_SP")
        self._dc_setpoint_pv_obj: Optional[PV] = None

        self.bias_voltage_pv: str = self.pv_addr("BIAS")
        self._bias_voltage_pv_obj: Optional[PV] = None

        self.voltage_pv: str = self.pv_addr("V")
        self._voltage_pv_obj: Optional[PV] = None

    def __str__(self):
        return self.cavity.__str__() + " Piezo"

    @property
    def pv_prefix(self):
        return self._pv_prefix

    @property
    def voltage_pv_obj(self):
        if not self._voltage_pv_obj:
            self._voltage_pv_obj = PV(self.voltage_pv)
        return self._voltage_pv_obj

    @property
    def voltage(self):
        return self.voltage_pv_obj.get()

    @property
    def bias_voltage_pv_obj(self):
        if not self._bias_voltage_pv_obj:
            self._bias_voltage_pv_obj = PV(self.bias_voltage_pv)
        return self._bias_voltage_pv_obj

    @property
    def bias_voltage(self):
        return self.bias_voltage_pv_obj.get()

    @bias_voltage.setter
    def bias_voltage(self, value):
        self.bias_voltage_pv_obj.put(value)

    @property
    def dc_setpoint_pv_obj(self) -> PV:
        if not self._dc_setpoint_pv_obj:
            self._dc_setpoint_pv_obj = PV(self.dc_setpoint_pv)
        return self._dc_setpoint_pv_obj

    @property
    def dc_setpoint(self):
        return self.dc_setpoint_pv_obj.get()

    @dc_setpoint.setter
    def dc_setpoint(self, value: float):
        self.dc_setpoint_pv_obj.put(value)

    @property
    def feedback_setpoint_pv_obj(self) -> PV:
        if not self._feedback_setpoint_pv_obj:
            self._feedback_setpoint_pv_obj = PV(self.feedback_setpoint_pv)
        return self._feedback_setpoint_pv_obj

    @property
    def feedback_setpoint(self):
        return self.feedback_setpoint_pv_obj.get()

    @feedback_setpoint.setter
    def feedback_setpoint(self, value):
        self.feedback_setpoint_pv_obj.put(value)

    @property
    def enable_pv_obj(self) -> PV:
        if not self._enable_pv_obj:
            self._enable_pv_obj = PV(self._pv_prefix + "ENABLE")
        return self._enable_pv_obj

    @property
    def is_enabled(self) -> bool:
        if not self._enable_stat_pv_obj:
            self._enable_stat_pv_obj = PV(self.enable_stat_pv)
        return self._enable_stat_pv_obj.get() == utils.PIEZO_ENABLE_VALUE

    @property
    def feedback_control_pv_obj(self) -> PV:
        if not self._feedback_control_pv_obj:
            self._feedback_control_pv_obj = PV(self.feedback_control_pv)
        return self._feedback_control_pv_obj

    @property
    def feedback_stat(self):
        if not self._feedback_stat_pv_obj:
            self._feedback_stat_pv_obj = PV(self.feedback_stat_pv)
        return self._feedback_stat_pv_obj.get()

    @property
    def in_manual(self) -> bool:
        return self.feedback_stat == utils.PIEZO_MANUAL_VALUE

    def set_to_feedback(self):
        self.feedback_control_pv_obj.put(utils.PIEZO_FEEDBACK_VALUE)

    def set_to_manual(self):
        self.feedback_control_pv_obj.put(utils.PIEZO_MANUAL_VALUE)

    def enable(self):
        self.bias_voltage = 25
        while not self.is_enabled:
            self.cavity.check_abort()
            print(f"{self} not enabled, trying to enable")
            self.enable_pv_obj.put(utils.PIEZO_DISABLE_VALUE)
            sleep(2)
            self.enable_pv_obj.put(utils.PIEZO_ENABLE_VALUE)
            sleep(2)

    def enable_feedback(self):
        self.enable()
        while self.in_manual:
            self.cavity.check_abort()
            print(f"{self} feedback not enabled, trying to enable feedback")
            self.set_to_manual()
            sleep(2)
            self.set_to_feedback()
            sleep(2)

    def disable_feedback(self):
        self.enable()
        while not self.in_manual:
            self.cavity.check_abort()
            print(f"{self} feedback enabled, trying to disable feedback")
            self.set_to_feedback()
            sleep(2)
            self.set_to_manual()
            sleep(2)


class Cavity(utils.SCLinacObject):
    """
    Python representation of LCLS II cavities. This class provides utility
    functions for commonly used tasks including powering on/off, changing RF mode,
    setting amplitude, characterizing, and tuning to resonance

    """

    def __init__(
        self,
        cavity_num,
        rack_object,
    ):
        # type: (int, Rack) -> None
        """
        @param cavity_num: int cavity number i.e. 1 - 8
        @param rack_object: the rack object the cavities belong to
        """

        self.number: int = cavity_num
        self.rack: Rack = rack_object
        self.cryomodule: Cryomodule = self.rack.cryomodule
        self.linac: Linac = self.cryomodule.linac

        if self.cryomodule.is_harmonic_linearizer:
            self.length = 0.346
            self.frequency = 3.9e9
            self.loaded_q_lower_limit = utils.LOADED_Q_LOWER_LIMIT_HL
            self.loaded_q_upper_limit = utils.LOADED_Q_UPPER_LIMIT_HL
        else:
            self.length = 1.038
            self.frequency = 1.3e9
            self.loaded_q_lower_limit = utils.LOADED_Q_LOWER_LIMIT
            self.loaded_q_upper_limit = utils.LOADED_Q_UPPER_LIMIT

        self._pv_prefix = "ACCL:{LINAC}:{CRYOMODULE}{CAVITY}0:".format(
            LINAC=self.linac.name, CRYOMODULE=self.cryomodule.name, CAVITY=self.number
        )

        self.ctePrefix = "CTE:CM{cm}:1{cav}".format(
            cm=self.cryomodule.name, cav=self.number
        )

        self.chirp_prefix = self._pv_prefix + "CHIRP:"
        self.abort_flag: bool = False

        # These need to be created after all the base cavity properties are defined
        self.ssa: SSA = self.rack.ssa_class(cavity=self)
        self.stepper_tuner: StepperTuner = self.rack.stepper_class(cavity=self)
        self.piezo: Piezo = self.rack.piezo_class(cavity=self)

        self._calc_probe_q_pv_obj: Optional[PV] = None
        self.calc_probe_q_pv: str = self.pv_addr("QPROBE_CALC1.PROC")

        self._push_ssa_slope_pv_obj: Optional[PV] = None
        self.push_ssa_slope_pv: str = self.pv_addr("PUSH_SSA_SLOPE.PROC")

        self.save_ssa_slope_pv: str = self.pv_addr("SAVE_SSA_SLOPE.PROC")
        self._save_ssa_slope_pv_obj: Optional[PV] = None

        self.interlock_reset_pv: str = self.pv_addr("INTLK_RESET_ALL")
        self._interlock_reset_pv_obj: Optional[PV] = None

        self.drive_level_pv: str = self.pv_addr("SEL_ASET")
        self._drive_level_pv_obj: Optional[PV] = None

        self.characterization_start_pv: str = self.pv_addr("PROBECALSTRT")
        self._characterization_start_pv_obj: Optional[PV] = None

        self.characterization_status_pv: str = self.pv_addr("PROBECALSTS")
        self._characterization_status_pv_obj: Optional[PV] = None

        self.current_q_loaded_pv: str = self.pv_addr("QLOADED")

        self.measured_loaded_q_pv: str = self.pv_addr("QLOADED_NEW")
        self._measured_loaded_q_pv_obj: Optional[PV] = None

        self.push_loaded_q_pv: str = self.pv_addr("PUSH_QLOADED.PROC")
        self._push_loaded_q_pv_obj: Optional[PV] = None

        self.save_q_loaded_pv: str = self.pv_addr("SAVE_QLOADED.PROC")

        self.current_cavity_scale_pv: str = self.pv_addr("CAV:SCALER_SEL.B")

        self.measured_scale_factor_pv: str = self.pv_addr("CAV:CAL_SCALEB_NEW")
        self._measured_scale_factor_pv_obj: Optional[PV] = None

        self.push_scale_factor_pv: str = self.pv_addr("PUSH_CAV_SCALE.PROC")
        self._push_scale_factor_pv_obj: Optional[PV] = None

        self.save_cavity_scale_pv: str = self.pv_addr("SAVE_CAV_SCALE.PROC")

        self.ades_pv: str = self.pv_addr("ADES")
        self._ades_pv_obj: Optional[PV] = None

        self.acon_pv: str = self.pv_addr("ACON")
        self._acon_pv_obj: Optional[PV] = None

        self.aact_pv: str = self.pv_addr("AACTMEAN")
        self._aact_pv_obj: Optional[PV] = None

        self.ades_max_pv: str = self.pv_addr("ADES_MAX")
        self._ades_max_pv_obj: Optional[PV] = None

        self.rf_mode_ctrl_pv: str = self.pv_addr("RFMODECTRL")
        self._rf_mode_ctrl_pv_obj: Optional[PV] = None

        self.rf_mode_pv: str = self.pv_addr("RFMODE")
        self._rf_mode_pv_obj: Optional[PV] = None

        self.rf_state_pv: str = self.pv_addr("RFSTATE")
        self._rf_state_pv_obj: Optional[PV] = None

        self.rf_control_pv: str = self.pv_addr("RFCTRL")
        self._rf_control_pv_obj: Optional[PV] = None

        self.pulse_go_pv: str = self.pv_addr("PULSE_DIFF_SUM")
        self._pulse_go_pv_obj: Optional[PV] = None

        self.pulse_status_pv: str = self.pv_addr("PULSE_STATUS")
        self._pulse_status_pv_obj: Optional[PV] = None

        self.pulse_on_time_pv: str = self.pv_addr("PULSE_ONTIME")
        self._pulse_on_time_pv_obj: Optional[PV] = None

        self.rev_waveform_pv: str = self.pv_addr("REV:AWF")
        self.fwd_waveform_pv: str = self.pv_addr("FWD:AWF")
        self.cav_waveform_pv: str = self.pv_addr("CAV:AWF")

        self.stepper_temp_pv: str = self.pv_addr("STEPTEMP")

        self.detune_best_pv: str = self.pv_addr("DFBEST")
        self._detune_best_pv_obj: Optional[PV] = None

        self.detune_chirp_pv: str = self.pv_addr("CHIRP:DF")
        self._detune_chirp_pv_obj: Optional[PV] = None

        self.rf_permit_pv: str = self.pv_addr("RFPERMIT")
        self._rf_permit_pv_obj: Optional[PV] = None

        self.quench_latch_pv: str = self.pv_addr("QUENCH_LTCH")
        self._quench_latch_pv_obj: Optional[PV] = None

        self.quench_bypass_pv: str = self.pv_addr("QUENCH_BYP")

        self.cw_data_decimation_pv: str = self.pv_addr("ACQ_DECIM_SEL.A")
        self._cw_data_decim_pv_obj: Optional[PV] = None

        self.pulsed_data_decimation_pv: str = self.pv_addr("ACQ_DECIM_SEL.C")
        self._pulsed_data_decim_pv_obj: Optional[PV] = None

        self.tune_config_pv: str = self.pv_addr("TUNE_CONFIG")
        self._tune_config_pv_obj: Optional[PV] = None

        self.chirp_freq_start_pv: str = self.chirp_prefix + "FREQ_START"
        self._chirp_freq_start_pv_obj: Optional[PV] = None

        self.freq_stop_pv: str = self.chirp_prefix + "FREQ_STOP"
        self._freq_stop_pv_obj: Optional[PV] = None

        self.hw_mode_pv: str = self.pv_addr("HWMODE")
        self._hw_mode_pv_obj: Optional[PV] = None

        self.char_timestamp_pv: str = self.pv_addr("PROBECALTS")
        self._char_timestamp_pv_obj: Optional[PV] = None

    def __str__(self):
        return f"{self.linac.name} CM{self.cryomodule.name} Cavity {self.number}"

    @property
    def pv_prefix(self):
        return self._pv_prefix

    @property
    def microsteps_per_hz(self):
        return 1 / self.stepper_tuner.hz_per_microstep

    def start_characterization(self):
        if not self._characterization_start_pv_obj:
            self._characterization_start_pv_obj = PV(self.characterization_start_pv)
        self._characterization_start_pv_obj.put(1)

    @property
    def cw_data_decimation_pv_obj(self) -> PV:
        if not self._cw_data_decim_pv_obj:
            self._cw_data_decim_pv_obj = PV(self.cw_data_decimation_pv)
        return self._cw_data_decim_pv_obj

    @property
    def cw_data_decimation(self):
        return self.cw_data_decimation_pv_obj.get()

    @cw_data_decimation.setter
    def cw_data_decimation(self, value: float):
        self.cw_data_decimation_pv_obj.put(value)

    @property
    def pulsed_data_decimation_pv_obj(self) -> PV:
        if not self._pulsed_data_decim_pv_obj:
            self._pulsed_data_decim_pv_obj = PV(self.pulsed_data_decimation_pv)
        return self._pulsed_data_decim_pv_obj

    @property
    def pulsed_data_decimation(self):
        return self.pulsed_data_decimation_pv_obj.get()

    @pulsed_data_decimation.setter
    def pulsed_data_decimation(self, value):
        self.pulsed_data_decimation_pv_obj.put(value)

    @property
    def rf_control_pv_obj(self) -> PV:
        if not self._rf_control_pv_obj:
            self._rf_control_pv_obj = PV(self.rf_control_pv)
        return self._rf_control_pv_obj

    @property
    def rf_control(self):
        return self.rf_control_pv_obj.get()

    @rf_control.setter
    def rf_control(self, value):
        self.rf_control_pv_obj.put(value)

    @property
    def rf_mode(self):
        if not self._rf_mode_pv_obj:
            self._rf_mode_pv_obj = PV(self.rf_mode_pv)
        return self._rf_mode_pv_obj.get()

    @property
    def rf_mode_ctrl_pv_obj(self) -> PV:
        if not self._rf_mode_ctrl_pv_obj:
            self._rf_mode_ctrl_pv_obj = PV(self.rf_mode_ctrl_pv)
        return self._rf_mode_ctrl_pv_obj

    def set_chirp_mode(self):
        self.rf_mode_ctrl_pv_obj.put(utils.RF_MODE_CHIRP)

    def set_sel_mode(self):
        self.rf_mode_ctrl_pv_obj.put(utils.RF_MODE_SEL)

    def set_sela_mode(self):
        self.rf_mode_ctrl_pv_obj.put(utils.RF_MODE_SELA)

    def set_selap_mode(self):
        self.rf_mode_ctrl_pv_obj.put(utils.RF_MODE_SELAP, use_caput=False)

    @property
    def drive_level_pv_obj(self):
        if not self._drive_level_pv_obj:
            self._drive_level_pv_obj = PV(self.drive_level_pv)
        return self._drive_level_pv_obj

    @property
    def drive_level(self):
        return self.drive_level_pv_obj.get()

    @drive_level.setter
    def drive_level(self, value):
        self.drive_level_pv_obj.put(value)

    def push_ssa_slope(self):
        if not self._push_ssa_slope_pv_obj:
            self._push_ssa_slope_pv_obj = PV(self._pv_prefix + "PUSH_SSA_SLOPE.PROC")
        self._push_ssa_slope_pv_obj.put(1)

    def save_ssa_slope(self):
        if not self._save_ssa_slope_pv_obj:
            self._save_ssa_slope_pv_obj = PV(self.save_ssa_slope_pv)
        self._save_ssa_slope_pv_obj.put(1)

    @property
    def measured_loaded_q(self) -> float:
        if not self._measured_loaded_q_pv_obj:
            self._measured_loaded_q_pv_obj = PV(self.measured_loaded_q_pv)
        return self._measured_loaded_q_pv_obj.get()

    @property
    def measured_loaded_q_in_tolerance(self) -> bool:
        return (
            self.loaded_q_lower_limit
            < self.measured_loaded_q
            < self.loaded_q_upper_limit
        )

    def push_loaded_q(self):
        if not self._push_loaded_q_pv_obj:
            self._push_loaded_q_pv_obj = PV(self.push_loaded_q_pv)
        self._push_loaded_q_pv_obj.put(1)

    @property
    def measured_scale_factor(self) -> float:
        if not self._measured_scale_factor_pv_obj:
            self._measured_scale_factor_pv_obj = PV(self.measured_scale_factor_pv)
        return self._measured_scale_factor_pv_obj.get()

    @property
    def measured_scale_factor_in_tolerance(self) -> bool:
        if self.cryomodule.is_harmonic_linearizer:
            return (
                utils.CAVITY_SCALE_LOWER_LIMIT_HL
                < self.measured_scale_factor
                < utils.CAVITY_SCALE_UPPER_LIMIT_HL
            )
        else:
            return (
                utils.CAVITY_SCALE_LOWER_LIMIT
                < self.measured_scale_factor
                < utils.CAVITY_SCALE_UPPER_LIMIT
            )

    def push_scale_factor(self):
        if not self._push_scale_factor_pv_obj:
            self._push_scale_factor_pv_obj = PV(self.push_scale_factor_pv)
        self._push_scale_factor_pv_obj.put(1)

    @property
    def characterization_status(self):
        if not self._characterization_status_pv_obj:
            self._characterization_status_pv_obj = PV(self.characterization_status_pv)
        return self._characterization_status_pv_obj.get()

    @property
    def characterization_running(self) -> bool:
        return self.characterization_status == utils.CHARACTERIZATION_RUNNING_VALUE

    @property
    def characterization_crashed(self) -> bool:
        return self.characterization_status == utils.CHARACTERIZATION_CRASHED_VALUE

    @property
    def pulse_on_time(self):
        if not self._pulse_on_time_pv_obj:
            self._pulse_on_time_pv_obj = PV(self._pv_prefix + "PULSE_ONTIME")
        return self._pulse_on_time_pv_obj.get()

    @pulse_on_time.setter
    def pulse_on_time(self, value: int):
        if not self._pulse_on_time_pv_obj:
            self._pulse_on_time_pv_obj = PV(self.pulse_on_time_pv)
        self._pulse_on_time_pv_obj.put(value)

    @property
    def pulse_status(self):
        if not self._pulse_status_pv_obj:
            self._pulse_status_pv_obj = PV(self.pulse_status_pv)
        return self._pulse_status_pv_obj.get()

    @property
    def rf_permit(self):
        if not self._rf_permit_pv_obj:
            self._rf_permit_pv_obj = PV(self.rf_permit_pv)
        return self._rf_permit_pv_obj.get()

    @property
    def rf_inhibited(self) -> bool:
        return self.rf_permit == 0

    @property
    def ades(self):
        if not self._ades_pv_obj:
            self._ades_pv_obj = PV(self.ades_pv)
        return self._ades_pv_obj.get(use_caget=False)

    @ades.setter
    def ades(self, value: float):
        if not self._ades_pv_obj:
            self._ades_pv_obj = PV(self._pv_prefix + "ADES")
        self._ades_pv_obj.put(value)

    @property
    def acon(self):
        if not self._acon_pv_obj:
            self._acon_pv_obj = PV(self.acon_pv)
        return self._acon_pv_obj.get(use_caget=False)

    @acon.setter
    def acon(self, value: float):
        if not self._acon_pv_obj:
            self._acon_pv_obj = PV(self.acon_pv)
        self._acon_pv_obj.put(value)

    @property
    def aact(self):
        if not self._aact_pv_obj:
            self._aact_pv_obj = PV(self.aact_pv)
        return self._aact_pv_obj.get()

    @property
    def ades_max(self):
        if not self._ades_max_pv_obj:
            self._ades_max_pv_obj = PV(self.ades_max_pv)
        return self._ades_max_pv_obj.get()

    @property
    def edm_macro_string(self):
        rfs_map = {
            1: "1A",
            2: "1A",
            3: "2A",
            4: "2A",
            5: "1B",
            6: "1B",
            7: "2B",
            8: "2B",
        }

        rfs = rfs_map[self.number]

        r = self.rack.rack_name

        # need to remove trailing colon and zeroes to match needed format
        cm = self.cryomodule.pv_prefix[:-3]

        # "id" shadows built-in id, renaming
        macro_id = self.cryomodule.name

        ch = 2 if self.number in [2, 4] else 1

        macro_string = ",".join(
            [
                "C={c}".format(c=self.number),
                "RFS={rfs}".format(rfs=rfs),
                "R={r}".format(r=r),
                "CM={cm}".format(cm=cm),
                "ID={id}".format(id=macro_id),
                "CH={ch}".format(ch=ch),
            ]
        )
        return macro_string

    @property
    def hw_mode(self):
        if not self._hw_mode_pv_obj:
            self._hw_mode_pv_obj = PV(self.hw_mode_pv)
        return self._hw_mode_pv_obj.get()

    @property
    def is_online(self) -> bool:
        return self.hw_mode == utils.HW_MODE_ONLINE_VALUE

    @property
    def is_offline(self) -> bool:
        return self.hw_mode == utils.HW_MODE_OFFLINE_VALUE

    @property
    def is_quenched(self) -> bool:
        if not self._quench_latch_pv_obj:
            self._quench_latch_pv_obj = PV(self.quench_latch_pv)
        return self._quench_latch_pv_obj.get() == 1

    @property
    def tune_config_pv_obj(self) -> PV:
        if not self._tune_config_pv_obj:
            self._tune_config_pv_obj = PV(self.tune_config_pv)
        return self._tune_config_pv_obj

    @property
    def chirp_freq_start_pv_obj(self) -> PV:
        if not self._chirp_freq_start_pv_obj:
            self._chirp_freq_start_pv_obj = PV(self.chirp_freq_start_pv)
        return self._chirp_freq_start_pv_obj

    @property
    def chirp_freq_start(self):
        return self.chirp_freq_start_pv_obj.get()

    @chirp_freq_start.setter
    def chirp_freq_start(self, value):
        self.chirp_freq_start_pv_obj.put(value)

    @property
    def freq_stop_pv_obj(self) -> PV:
        if not self._freq_stop_pv_obj:
            self._freq_stop_pv_obj = PV(self.freq_stop_pv)
        return self._freq_stop_pv_obj

    @property
    def chirp_freq_stop(self):
        return self.freq_stop_pv_obj.get()

    @chirp_freq_stop.setter
    def chirp_freq_stop(self, value):
        self.freq_stop_pv_obj.put(value)

    @property
    def calc_probe_q_pv_obj(self) -> PV:
        if not self._calc_probe_q_pv_obj:
            self._calc_probe_q_pv_obj = PV(self.calc_probe_q_pv)
        return self._calc_probe_q_pv_obj

    def calculate_probe_q(self):
        self.calc_probe_q_pv_obj.put(1)

    def set_chirp_range(self, offset: int):
        offset = abs(offset)
        print(f"Setting chirp range for {self} to +/- {offset} Hz")
        self.chirp_freq_start = -offset
        self.chirp_freq_stop = offset
        print(f"Chirp range set for {self}")

    @property
    def rf_state_pv_obj(self) -> PV:
        if not self._rf_state_pv_obj:
            self._rf_state_pv_obj = PV(self.rf_state_pv)
        return self._rf_state_pv_obj

    @property
    def rf_state(self):
        """This property is read only"""
        return self.rf_state_pv_obj.get()

    @property
    def is_on(self):
        return self.rf_state == 1

    def move_to_resonance(self, reset_signed_steps=False, use_sela=False):
        def delta_detune():
            return self.detune

        self.setup_tuning(use_sela=use_sela)
        print(f"Tuning {self} to resonance in " + ("SELA" if use_sela else "chirp"))
        self._auto_tune(
            delta_hz_func=delta_detune,
            tolerance=(500 if self.cryomodule.is_harmonic_linearizer else 50),
            reset_signed_steps=reset_signed_steps,
        )

        if use_sela:

            def delta_piezo():
                delta_volts = self.piezo.voltage - utils.PIEZO_CENTER_VOLTAGE
                delta_hz = delta_volts * utils.PIEZO_HZ_PER_VOLT
                print(f"{self} piezo detune: {delta_hz}")
                return (
                    delta_hz
                    if not self.cryomodule.is_harmonic_linearizer
                    else -delta_hz
                )

            print(f"Centering {self} piezo")
            self._auto_tune(
                delta_hz_func=delta_piezo,
                tolerance=100,
                reset_signed_steps=False,
            )

        self.tune_config_pv_obj.put(utils.TUNE_CONFIG_RESONANCE_VALUE)

    @property
    def detune_best_pv_obj(self) -> PV:
        if not self._detune_best_pv_obj:
            self._detune_best_pv_obj = PV(self.detune_best_pv)
        return self._detune_best_pv_obj

    @property
    def detune_chirp_pv_obj(self) -> PV:
        if not self._detune_chirp_pv_obj:
            self._detune_chirp_pv_obj = PV(self.detune_chirp_pv)
        return self._detune_chirp_pv_obj

    @property
    def detune_best(self):
        return self.detune_best_pv_obj.get()

    @property
    def detune_chirp(self):
        return self.detune_chirp_pv_obj.get()

    @property
    def detune(self):
        if self.rf_mode == utils.RF_MODE_CHIRP:
            return self.detune_chirp
        else:
            return self.detune_best

    @property
    def detune_invalid(self) -> bool:
        if self.rf_mode == utils.RF_MODE_CHIRP:
            return self.detune_chirp_pv_obj.severity == EPICS_INVALID_VAL
        else:
            return self.detune_best_pv_obj.severity == EPICS_INVALID_VAL

    def _auto_tune(
        self,
        delta_hz_func: Callable,
        tolerance: int = 50,
        reset_signed_steps: bool = False,
    ):
        if self.detune_invalid:
            raise utils.DetuneError(f"Detune for {self} is invalid")

        delta_hz = delta_hz_func()
        expected_steps: int = abs(int(delta_hz * self.microsteps_per_hz))

        stepper_tol_factor = utils.stepper_tol_factor(expected_steps)

        steps_moved: int = 0

        if reset_signed_steps:
            self.stepper_tuner.reset_signed_steps()

        self.tune_config_pv_obj.put(utils.TUNE_CONFIG_OTHER_VALUE)

        while abs(delta_hz) > tolerance:
            self.check_abort()
            est_steps = int(0.9 * delta_hz * self.microsteps_per_hz)

            print(f"Moving stepper for {self} {est_steps} steps")

            self.stepper_tuner.move(
                est_steps,
                max_steps=int(abs(est_steps) * 1.1),
                speed=utils.MAX_STEPPER_SPEED,
            )

            steps_moved += abs(est_steps)

            if steps_moved > expected_steps * stepper_tol_factor:
                raise utils.DetuneError(f"{self} motor moved more steps than expected")

            # this should catch if the chirp range is wrong or if the cavity is off
            self.check_detune()

            delta_hz = delta_hz_func()

    def check_detune(self):
        if self.detune_invalid:
            if self.rf_mode == utils.RF_MODE_CHIRP:
                self.find_chirp_range(self.chirp_freq_start * 1.1)
            else:
                raise utils.DetuneError(
                    f"Cannot tune {self} in SELA with invalid detune"
                )

    def check_and_set_on_time(self):
        """
        In pulsed mode the cavity has a duty cycle determined by the on time and
        off time. We want the on time to be 70 ms or else the various cavity
        parameters calculated from the waveform (e.g. the RF gradient) won't be
        accurate.
        :return:
        """
        print("Checking RF Pulse On Time...")
        if self.pulse_on_time != utils.NOMINAL_PULSED_ONTIME:
            print(
                "Setting RF Pulse On Time to {ontime} ms".format(
                    ontime=utils.NOMINAL_PULSED_ONTIME
                )
            )
            self.pulse_on_time = utils.NOMINAL_PULSED_ONTIME
            self.push_go_button()

    @property
    def pulse_go_pv_obj(self) -> PV:
        if not self._pulse_go_pv_obj:
            self._pulse_go_pv_obj = PV(self._pv_prefix + "PULSE_DIFF_SUM")
        return self._pulse_go_pv_obj

    def push_go_button(self):
        """
        Many of the changes made to a cavity don't actually take effect until the
        go button is pressed
        :return:
        """
        self._pulse_go_pv_obj.put(1)
        while self.pulse_status < 2:
            print("waiting for pulse state", datetime.now())
            sleep(1)
        if self.pulse_status > 2:
            raise utils.PulseError("Unable to pulse cavity")

    def turn_on(self):
        print(f"Turning {self} on")
        if self.is_online:
            self.ssa.turn_on()
            self.reset_interlocks()
            self.rf_control = 1

            while not self.is_on:
                self.check_abort()
                print(f"waiting for {self} to turn on", datetime.now())
                sleep(1)

            print(f"{self} on")
        else:
            raise utils.CavityHWModeError(f"{self} not online")

    def turn_off(self):
        print(f"turning {self} off")
        self.rf_control = 0
        while self.is_on:
            self.check_abort()
            print(f"waiting for {self} to turn off")
            sleep(1)
        print(f"{self} off")

    def setup_selap(self, des_amp: float = 5):
        self.setup_rf(des_amp)
        self.set_selap_mode()
        print(f"{self} set up in SELAP")

    def setup_sela(self, des_amp: float = 5):
        self.setup_rf(des_amp)
        self.set_sela_mode()
        print(f"{self} set up in SELA")

    def check_abort(self):
        if self.abort_flag:
            self.abort_flag = False
            self.turn_off()
            raise utils.CavityAbortError(f"Abort requested for {self}")

    def setup_rf(self, des_amp):
        if des_amp > self.ades_max:
            print(
                f"Requested amplitude for {self} too high - ramping up to AMAX instead"
            )
            des_amp = self.ades_max
        print(f"setting up {self}")
        self.turn_off()
        self.ssa.calibrate(self.ssa.drive_max)
        self.move_to_resonance()

        self.characterize()
        self.calculate_probe_q()

        self.check_abort()

        self.reset_data_decimation()

        self.check_abort()

        self.ades = min(5, des_amp)
        self.set_sel_mode()
        self.piezo.enable_feedback()
        self.set_sela_mode()

        self.check_abort()

        if des_amp <= 10:
            self.walk_amp(des_amp, 0.5)

        else:
            self.walk_amp(10, 0.5)
            self.walk_amp(des_amp, 0.1)

    def reset_data_decimation(self):
        print(f"Setting data decimation for {self}")
        self.cw_data_decimation = 255
        self.pulsed_data_decimation = 255

    def setup_tuning(self, chirp_range=50000, use_sela=False):
        self.piezo.enable()

        if not use_sela:
            self.piezo.disable_feedback()

            print(f"setting {self} piezo DC voltage offset to 0V")
            self.piezo.dc_setpoint = 0

            print(f"setting {self} drive level to {utils.SAFE_PULSED_DRIVE_LEVEL}")
            self.drive_level = utils.SAFE_PULSED_DRIVE_LEVEL

            print(f"setting {self} RF to chirp")
            self.set_chirp_mode()

            print(f"turning {self} RF on and waiting 5s for detune to catch up")
            self.turn_on()
            sleep(5)
            self.find_chirp_range(chirp_range)

        else:
            self.piezo.enable_feedback()
            self.set_sela_mode()
            self.turn_on()

    def find_chirp_range(self, chirp_range=50000):
        self.check_abort()
        self.set_chirp_range(chirp_range)
        sleep(1)
        if self.detune_invalid:
            if chirp_range < 400000:
                self.find_chirp_range(int(chirp_range * 1.1))
            else:
                raise utils.DetuneError(
                    f"{self}: No valid detune found within" f"+/-400000Hz chirp range"
                )

    def reset_interlocks(self, wait: int = 3, attempt: int = 0):
        # TODO see if it makes more sense to implement this non-recursively
        print(f"Resetting interlocks for {self} and waiting {wait}s")

        if not self._interlock_reset_pv_obj:
            self._interlock_reset_pv_obj = PV(self.interlock_reset_pv)

        self._interlock_reset_pv_obj.put(1)
        sleep(wait)

        print(f"Checking {self} RF permit")
        if self.rf_inhibited:
            if attempt >= utils.INTERLOCK_RESET_ATTEMPTS:
                raise utils.CavityFaultError(
                    f"{self} still faulted after"
                    f" {utils.INTERLOCK_RESET_ATTEMPTS} "
                    f"reset attempts"
                )
            else:
                print(f"{self} reset {attempt} unsuccessful; retrying")
                self.reset_interlocks(wait=wait + 2, attempt=attempt + 1)
        else:
            print(f"{self} interlocks reset")

    @property
    def characterization_timestamp(self) -> datetime:
        if not self._char_timestamp_pv_obj:
            self._char_timestamp_pv_obj = PV(self.char_timestamp_pv)
        date_string = self._char_timestamp_pv_obj.get(use_caget=False)
        time_readback = datetime.strptime(date_string, "%Y-%m-%d-%H:%M:%S")
        print(f"{self} characterization time is {time_readback}")
        return time_readback

    def characterize(self):
        """
        Calibrates the cavity's RF probe so that the amplitude readback will be
        accurate. Also measures the loaded Q (quality factor) of the cavity power
        coupler
        :return:
        """

        self.reset_interlocks()

        print(f"setting {self} drive to {utils.SAFE_PULSED_DRIVE_LEVEL}")
        self.drive_level = utils.SAFE_PULSED_DRIVE_LEVEL

        if (datetime.now() - self.characterization_timestamp).total_seconds() < 60:
            if self.characterization_status == 1:
                print(
                    f"{self} successful characterization within the last minute,"
                    f" not starting a new one"
                )
                self.finish_characterization()
                return

        print(f"Starting {self} cavity characterization at {datetime.now()}")
        self.start_characterization()
        sleep(2)

        while self.characterization_running:
            self.check_abort()
            print(
                f"waiting for {self} characterization" f" to stop running",
                datetime.now(),
            )
            sleep(1)

        if self.characterization_status == utils.CALIBRATION_COMPLETE_VALUE:
            if (datetime.now() - self.characterization_timestamp).total_seconds() > 300:
                raise utils.CavityQLoadedCalibrationError(
                    f"No valid {self} characterization within the last 5 min"
                )
            self.finish_characterization()

        if self.characterization_crashed:
            raise utils.CavityQLoadedCalibrationError(
                f"{self} characterization crashed"
            )

    def finish_characterization(self):
        print(f"pushing {self} characterization results")
        if self.measured_loaded_q_in_tolerance:
            self.push_loaded_q()
        else:
            raise utils.CavityQLoadedCalibrationError(
                f"{self} loaded Q out of tolerance"
            )
        if self.measured_scale_factor_in_tolerance:
            self.push_scale_factor()
        else:
            raise utils.CavityScaleFactorCalibrationError(
                f"{self} scale factor out of tolerance"
            )

        self.reset_data_decimation()
        print(f"restoring {self} piezo feedback setpoint to 0")
        self.piezo.feedback_setpoint = 0

        print(f"{self} characterization successful")

    def walk_amp(self, des_amp, step_size):
        print(f"walking {self} to {des_amp} from {self.ades}")

        while self.ades <= (des_amp - step_size):
            self.check_abort()
            if self.is_quenched:
                raise utils.QuenchError(f"{self} quench detected, aborting RF ramp")
            self.ades = self.ades + step_size
            # to avoid tripping sensitive interlock
            sleep(0.1)

        if self.ades != des_amp:
            self.ades = des_amp

        print(f"{self} at {des_amp} MV")


class Magnet(utils.SCLinacObject):
    """
    Python representation of LCLS II magnets. This class provides wrappers for
    common magnet controls including powering on/off and changing strength

    """

    def __init__(self, magnet_type, cryomodule):
        # type: (str, Cryomodule) -> None
        """
        @param magnet_type: One of QUAD, XCOR, or YCOR
        @param cryomodule: the cryomodule object in which this magnet is contained
        """

        self._pv_prefix = f"{magnet_type}:{cryomodule.linac.name}:{cryomodule.name}85:"

        self.name = magnet_type
        self.cryomodule: Cryomodule = cryomodule

        self.bdes_pv: str = self.pv_addr("BDES")
        self._bdes_pv_obj: Optional[PV] = None

        self.control_pv: str = self.pv_addr("CTRL")
        self._control_pv_obj: Optional[PV] = None

        self.interlock_pv: str = self.pv_addr("INTLKSUMY")
        self.ps_status_pv: str = self.pv_addr("STATE")
        self.bact_pv: str = self.pv_addr("BACT")
        self.iact_pv: str = self.pv_addr("IACT")

        # changing IDES immediately perturbs
        self.ides_pv: str = self.pv_addr("IDES")

    @property
    def pv_prefix(self):
        return self._pv_prefix

    @property
    def control_pv_obj(self) -> PV:
        if not self._control_pv_obj:
            self._control_pv_obj = PV(self.control_pv)
        return self._control_pv_obj

    @property
    def bdes(self):
        if not self._bdes_pv_obj:
            self._bdes_pv_obj = PV(self.bdes_pv)
        return self._bdes_pv_obj.get()

    @bdes.setter
    def bdes(self, value):
        self._bdes_pv_obj.put(value)
        self.control_pv_obj.put(utils.MAGNET_TRIM_VALUE)

    def reset(self):
        self.control_pv_obj.put(utils.MAGNET_RESET_VALUE)

    def turn_on(self):
        self.control_pv_obj.put(utils.MAGNET_ON_VALUE)

    def turn_off(self):
        self.control_pv_obj.put(utils.MAGNET_OFF_VALUE)

    def degauss(self):
        self.control_pv_obj.put(utils.MAGNET_DEGAUSS_VALUE)

    def trim(self):
        self.control_pv_obj.put(utils.MAGNET_TRIM_VALUE)


class Rack(utils.SCLinacObject):
    """
    Python representation of LCLS II RF Racks. This class functions mostly as a
    container for cavities.
    Rack A has cavities 1 through 4, Rack B has cavities 5 through 8.
    """

    def __init__(
        self,
        rack_name,
        cryomodule_object,
    ):
        # type: (str, Cryomodule) -> None
        """
        Parameters
        ----------
        rack_name: str name of rack (always either "A" or "B")
        cryomodule_object: the cryomodule object this rack belongs to
        """

        self.cryomodule: Cryomodule = cryomodule_object
        self.rack_name = rack_name

        self.cavity_class: Type[Cavity] = self.cryomodule.cavity_class
        self.ssa_class = self.cryomodule.ssa_class
        self.stepper_class = self.cryomodule.stepper_class
        self.piezo_class = self.cryomodule.piezo_class

        self.cavities: Dict[int, Cavity] = {}
        self._pv_prefix = self.cryomodule.pv_addr(
            "RACK{RACK}:".format(RACK=self.rack_name)
        )

        if rack_name == "A":
            # rack A always has cavities 1 - 4
            for cavityNum in range(1, 5):
                self.cavities[cavityNum] = self.cavity_class(
                    cavity_num=cavityNum, rack_object=self
                )

        elif rack_name == "B":
            # rack B always has cavities 5 - 8
            for cavityNum in range(5, 9):
                self.cavities[cavityNum] = self.cavity_class(
                    cavity_num=cavityNum, rack_object=self
                )

        else:
            raise Exception(f"Bad rack name {rack_name}")

    @property
    def pv_prefix(self):
        return self._pv_prefix


class Cryomodule(utils.SCLinacObject):
    """
    Python representation of an LCLS II cryomodule. This class functions mostly
    as a container for racks and cryo-level PVs

    """

    def __init__(
        self,
        cryo_name,
        linac_object,
    ):
        # type: (str, Linac) -> None # noqa: E501
        """
        @param cryo_name: str name of Cryomodule i.e. "02", "03", "H1", "H2"
        @param linac_object: the linac object this cryomodule belongs to i.e.
                             CM02 is in linac L1B
        """

        self.name: str = cryo_name
        self.linac: Linac = linac_object

        self.magnet_class: Type[Magnet] = self.linac.magnet_class
        self.rack_class: Type[Rack] = self.linac.rack_class
        self.cavity_class: Type[Cavity] = self.linac.cavity_class
        self.ssa_class: Type[SSA] = self.linac.ssa_class
        self.stepper_class: Type[StepperTuner] = self.linac.stepper_class
        self.piezo_class: Type[Piezo] = self.linac.piezo_class

        if not self.is_harmonic_linearizer:
            self.quad: Magnet = self.magnet_class(magnet_type="QUAD", cryomodule=self)
            self.xcor: Magnet = self.magnet_class(magnet_type="XCOR", cryomodule=self)
            self.ycor: Magnet = self.magnet_class(magnet_type="YCOR", cryomodule=self)

        self._pv_prefix = f"ACCL:{self.linac.name}:{self.name}00:"

        self.cte_prefix = f"CTE:CM{self.name}:"
        self.cvt_prefix = f"CVT:CM{self.name}:"
        self.cpv_prefix = f"CPV:CM{self.name}:"

        if not self.is_harmonic_linearizer:
            self.jt_prefix = f"CLIC:CM{self.name}:3001:PVJT:"
        else:
            name_map: Dict[str, str] = {"H1": "HL01", "H2": "HL02"}
            self.jt_prefix = f"CLIC:{name_map[self.name]}:3001:PVJT:"

        self.ds_level_pv: str = f"CLL:CM{self.name}:2301:DS:LVL"
        self.us_level_pv: str = f"CLL:CM{self.name}:2601:US:LVL"
        self.ds_pressure_pv: str = f"CPT:CM{self.name}:2302:DS:PRESS"
        self.jt_valve_readback_pv: str = self.jt_prefix + "ORBV"
        self.heater_readback_pv: str = f"CPIC:CM{self.name}:0000:EHCV:ORBV"

        self.rack_a: Rack = self.rack_class(rack_name="A", cryomodule_object=self)
        self.rack_b: Rack = self.rack_class(rack_name="B", cryomodule_object=self)

        self.cavities: Dict[int, Cavity] = {}
        self.cavities.update(self.rack_a.cavities)
        self.cavities.update(self.rack_b.cavities)

        if self.is_harmonic_linearizer:
            self.coupler_vacuum_pvs: List[str] = [
                self.linac.vacuum_prefix + "{cm}09:COMBO_P".format(cm=self.name),
                self.linac.vacuum_prefix + "{cm}19:COMBO_P".format(cm=self.name),
            ]
        else:
            self.coupler_vacuum_pvs: List[str] = [
                self.linac.vacuum_prefix + "{cm}14:COMBO_P".format(cm=self.name)
            ]

        self.vacuum_pvs: List[str] = (
            self.coupler_vacuum_pvs
            + self.linac.beamline_vacuum_pvs
            + self.linac.insulating_vacuum_pvs
        )

    @property
    def is_harmonic_linearizer(self):
        return self.name in ["H1", "H2"]

    @property
    def pv_prefix(self):
        return self._pv_prefix


class Linac:
    """
    Python representation of LCLS II linac sections. This class functions mostly
    as a container for cryomodules and linac-level vacuum PVs

    """

    def __init__(
        self,
        linac_section,
        beamline_vacuum_infixes,
        insulating_vacuum_cryomodules,
        machine,
    ):
        # type: (int, List[str], List[str], Machine) -> None
        """
        @param linac_section: int of Linac index i.e. "L0B" -> 0
        @param beamline_vacuum_infixes: str list of vacuum infixes for that
                                        section as found in
                                        utils.BEAMLINE_VACUUM_INFIXES
        @param insulating_vacuum_cryomodules: str list of cryomodules with
                                              insulated vacuum readback in that
                                              section as found in
                                              utils.INSULATING_VACUUM_CRYOMODULES
        @param machine: Machine object that this linac belongs to
        """

        self.cryomodule_class: Type[Cryomodule] = machine.cryomodule_class
        self.cavity_class = machine.cavity_class
        self.rack_class = machine.rack_class
        self.magnet_class = machine.magnet_class
        self.ssa_class = machine.ssa_class
        self.stepper_class = machine.stepper_class
        self.piezo_class = machine.piezo_class

        self.name = f"L{linac_section}B"
        self.cryomodules: Dict[str, Cryomodule] = {}
        self.vacuum_prefix = "VGXX:{linac}:".format(linac=self.name)

        self.beamline_vacuum_pvs: List[str] = [
            self.vacuum_prefix + "{infix}:COMBO_P".format(infix=infix)
            for infix in beamline_vacuum_infixes
        ]
        self.insulating_vacuum_pvs: List[str] = [
            self.vacuum_prefix + "{cm}96:COMBO_P".format(cm=cm)
            for cm in insulating_vacuum_cryomodules
        ]

        for cm_name in utils.LINAC_CM_MAP[linac_section]:
            self.cryomodules[cm_name] = self.cryomodule_class(
                cryo_name=cm_name, linac_object=self
            )

    def add_cryomodules(
        self,
        cryomodule_string_list: List[str],
    ):
        for cryomoduleString in cryomodule_string_list:
            self.add_cryomodule(
                cryomodule_name=cryomoduleString,
            )

    def add_cryomodule(self, cryomodule_name: str):
        self.cryomodules[cryomodule_name] = self.cryomodule_class(
            cryo_name=cryomodule_name, linac_object=self
        )


class Machine:
    """
    Python representation of the entire LCLS II accelerator. This class functions
    as a generator for lower level accelerator objects, as well as a container
    for generated cryomodule objects

    """

    def __init__(
        self,
        linac_class: Type[Linac] = Linac,
        cryomodule_class: Type[Cryomodule] = Cryomodule,
        cavity_class: Type[Cavity] = Cavity,
        magnet_class: Type[Magnet] = Magnet,
        rack_class: Type[Rack] = Rack,
        stepper_class: Type[StepperTuner] = StepperTuner,
        ssa_class: Type[SSA] = SSA,
        piezo_class: Type[Piezo] = Piezo,
    ):
        """
        All inputs are optional, but allow for object customization for more
        specific use cases. Only functionality used by at least two applications
        is put in default classes

        """
        self.linac_class = linac_class
        self.cryomodule_class = cryomodule_class
        self.cavity_class = cavity_class
        self.magnet_class = magnet_class
        self.rack_class = rack_class
        self.stepper_class = stepper_class
        self.ssa_class = ssa_class
        self.piezo_class = piezo_class

        self.linacs: List[Linac] = []

        for section in range(4):
            self.linacs.append(
                linac_class(
                    linac_section=section,
                    beamline_vacuum_infixes=utils.BEAMLINE_VACUUM_INFIXES[section],
                    insulating_vacuum_cryomodules=utils.INSULATING_VACUUM_CRYOMODULES[
                        section
                    ],
                    machine=self,
                )
            )

        self.cryomodules: Dict[str, Cryomodule] = {}
        for linac in self.linacs:
            for cm_name, cm_obj in linac.cryomodules.items():
                self.cryomodules[cm_name] = cm_obj


MACHINE = Machine()
