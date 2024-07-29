from datetime import datetime
from time import sleep
from typing import Optional, TYPE_CHECKING

from numpy import sign

from lcls_tools.common.controls.pyepics.utils import PV
from lcls_tools.superconducting import sc_linac_utils as utils

if TYPE_CHECKING:
    from lcls_tools.superconducting.sc_cavity import Cavity


class StepperTuner(utils.SCLinacObject):
    """
    Python representation of LCLS II stepper tuners. This class provides wrappers
    for common stepper controls including sending move commands, checking movement
    status, and retrieving stored movement parameters
    """

    def __init__(self, cavity: "Cavity"):
        """
        @param cavity: the cavity object tuned by this stepper
        """

        self.cavity: "Cavity" = cavity
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
