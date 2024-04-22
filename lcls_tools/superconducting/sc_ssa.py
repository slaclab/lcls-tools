from datetime import datetime
from time import sleep
from typing import Optional

from lcls_tools.common.controls.pyepics.utils import PV
from lcls_tools.superconducting import sc_linac_utils as utils
from lcls_tools.superconducting.sc_cavity import Cavity


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
