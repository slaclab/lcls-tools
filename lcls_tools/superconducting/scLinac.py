################################################################################
# Utility classes for superconducting linac
# NOTE: For some reason, using python 3 style type annotations causes circular
#       import issues, so leaving as python 2 style for now
################################################################################
from datetime import datetime
from time import sleep
from typing import Dict, List, Type

from numpy import sign

import lcls_tools.superconducting.scLinacUtils as utils
from lcls_tools.common.pyepics_tools.pyepicsUtils import EPICS_INVALID_VAL, PV

HL_SSA_MAP = {1: 1, 2: 2, 3: 3, 4: 4, 5: 1, 6: 2, 7: 3, 8: 4}


class SSA:
    def __init__(self, cavity):
        # type: (Cavity) -> None
        self.cavity: Cavity = cavity
        if self.cavity.cryomodule.isHarmonicLinearizer:
            cavity_num = HL_SSA_MAP[self.cavity.number]
            self.pvPrefix = "ACCL:{LINAC}:{CRYOMODULE}{CAVITY}0:SSA:".format(LINAC=self.cavity.linac.name,
                                                                             CRYOMODULE=self.cavity.cryomodule.name,
                                                                             CAVITY=cavity_num)
        else:
            self.pvPrefix = self.cavity.pvPrefix + "SSA:"
        
        self._status_pv: PV = None
        self._turn_on_pv: PV = None
        self._turn_off_pv: PV = None
        self._reset_pv: PV = None
        
        self._calibration_start_pv: PV = None
        self._calibration_status_pv: PV = None
        self._cal_result_status_pv: PV = None
        
        self.currentSlopePV: PV = PV(self.pvPrefix + "SLOPE")
        self._measured_slope_pv: PV = None
        
        self._maxdrive_setpoint_pv: PV = None
        self._saved_maxdrive_pv: PV = None
        self._max_fwd_pwr_pv: PV = None
    
    def __str__(self):
        return f"{self.cavity} SSA"
    
    @property
    def status_message(self):
        if not self._status_pv:
            self._status_pv = PV(self.pvPrefix + "StatusMsg")
        return self._status_pv.get()
    
    @property
    def is_on(self):
        return self.status_message == utils.SSA_STATUS_ON_VALUE
    
    @property
    def max_fwd_pwr(self):
        if not self._max_fwd_pwr_pv:
            self._max_fwd_pwr_pv = PV(self.pvPrefix + "CALPWR")
        return self._max_fwd_pwr_pv.get()
    
    @property
    def drivemax(self):
        if not self._saved_maxdrive_pv:
            self._saved_maxdrive_pv = PV(self.pvPrefix + "DRV_MAX_SAVE")
        saved_val = self._saved_maxdrive_pv.get()
        return (1 if self.cavity.cryomodule.isHarmonicLinearizer
                else (saved_val if saved_val else 0.8))
    
    @drivemax.setter
    def drivemax(self, value: float):
        if not self._maxdrive_setpoint_pv:
            self._maxdrive_setpoint_pv = PV(self.pvPrefix + "DRV_MAX_REQ")
        self._maxdrive_setpoint_pv.put(value)
    
    def calibrate(self, drivemax):
        print(f"Trying {self} calibration with drivemax {drivemax}")
        if drivemax < 0.5:
            raise utils.SSACalibrationError(f"Requested {self} drive max too low")
        
        print(f"Setting {self} max drive")
        self.drivemax = drivemax
        
        try:
            self.cavity.check_abort()
            self.runCalibration()
        
        except utils.SSACalibrationError as e:
            print(f"{self} Calibration failed with '{e}', retrying")
            self.calibrate(drivemax - 0.02)
        
        except utils.SSACalibrationToleranceError as e:
            print(f"{self} Calibration failed with '{e}', retrying")
            self.calibrate(drivemax)
    
    def turn_on(self):
        if not self.is_on:
            print(f"Turning {self} on")
            
            if not self._turn_on_pv:
                self._turn_on_pv = PV(self.pvPrefix + "PowerOn")
            self._turn_on_pv.put(1)
            
            while not self.is_on:
                self.cavity.check_abort()
                print(f"waiting for {self} to turn on")
                sleep(1)
        
        print(f"{self} on")
    
    def turn_off(self):
        if self.is_on:
            print(f"Turning {self} off")
            if not self._turn_off_pv:
                self._turn_off_pv = PV(self.pvPrefix + "PowerOff")
            self._turn_off_pv.put(1)
            
            while self.is_on:
                self.cavity.check_abort()
                print(f"waiting for {self} to turn off")
                sleep(1)
        
        print(f"{self} off")
    
    def reset(self):
        print(f"Resetting {self}...")
        if not self._reset_pv:
            self._reset_pv = PV(self.pvPrefix + "FaultReset")
        self._reset_pv.put(1)
        
        while self.status_message == utils.SSA_STATUS_RESETTING_FAULTS_VALUE:
            sleep(1)
        
        if self.status_message in [utils.SSA_STATUS_FAULTED_VALUE,
                                   utils.SSA_STATUS_FAULT_RESET_FAILED_VALUE]:
            raise utils.SSAFaultError(f"Unable to reset {self}")
        
        print(f"{self} reset")
    
    def start_calibration(self):
        if not self._calibration_start_pv:
            self._calibration_start_pv = PV(self.pvPrefix + "CALSTRT")
        self._calibration_start_pv.put(1)
    
    @property
    def calibration_status(self):
        if not self._calibration_status_pv:
            self._calibration_status_pv = PV(self.pvPrefix + "CALSTS")
        return self._calibration_status_pv.get()
    
    @property
    def calibration_running(self) -> bool:
        return self.calibration_status == utils.SSA_CALIBRATION_RUNNING_VALUE
    
    @property
    def calibration_crashed(self) -> bool:
        return self.calibration_status == utils.SSA_CALIBRATION_CRASHED_VALUE
    
    @property
    def calibration_result_good(self) -> bool:
        if not self._cal_result_status_pv:
            self._cal_result_status_pv = PV(self.pvPrefix + "CALSTAT")
        return self._cal_result_status_pv.get() == utils.SSA_RESULT_GOOD_STATUS_VALUE
    
    def runCalibration(self, save_slope: bool = False):
        """
        Runs the SSA through its range and finds the slope that describes
        the relationship between SSA drive signal and output power
        :return:
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
        
        if self.max_fwd_pwr < utils.SSA_FWD_PWR_LOWER_LIMIT:
            raise utils.SSACalibrationToleranceError(f"{self.cavity} SSA forward power too low")
        
        if not self.measured_slope_in_tolerance:
            raise utils.SSACalibrationToleranceError(f"{self.cavity} SSA Slope out of tolerance")
        
        print(f"Pushing SSA calibration results for {self.cavity}")
        self.cavity.push_ssa_slope()
        
        if save_slope:
            self.cavity.save_ssa_slope()
    
    @property
    def measured_slope(self):
        if not self._measured_slope_pv:
            self._measured_slope_pv = PV(self.pvPrefix + "SLOPE_NEW")
        return self._measured_slope_pv.get()
    
    @property
    def measured_slope_in_tolerance(self) -> bool:
        return (utils.SSA_SLOPE_LOWER_LIMIT
                > self.measured_slope
                > utils.SSA_SLOPE_UPPER_LIMIT)


class StepperTuner:
    def __init__(self, cavity):
        # type (Cavity) -> None
        
        self.cavity: Cavity = cavity
        self.pvPrefix: str = self.cavity.pvPrefix + "STEP:"
        
        self._move_pos_pv: PV = None
        self._move_neg_pv: PV = None
        self._abort_pv: PV = None
        self._step_des_pv: PV = None
        self._max_steps_pv: PV = None
        self._speed_pv: PV = None
        self.step_tot_pv: PV = PV(self.pvPrefix + "REG_TOTABS")
        self.step_signed_pv: PV = PV(self.pvPrefix + "REG_TOTSGN")
        self.reset_tot_pv: PV = PV(self.pvPrefix + "TOTABS_RESET")
        self._reset_signed_pv: PV = None
        self.steps_cold_landing_pv: PV = PV(self.pvPrefix + "NSTEPS_COLD")
        self.push_signed_cold_pv: PV = PV(self.pvPrefix + "PUSH_NSTEPS_COLD.PROC")
        self.push_signed_park_pv: PV = PV(self.pvPrefix + "PUSH_NSTEPS_PARK.PROC")
        self._motor_moving_pv: PV = None
        self.motor_done_pv: PV = PV(self.pvPrefix + "STAT_DONE")
        self._limit_switch_a_pv: PV = None
        self._limit_switch_b_pv: PV = None
        
        self.abort_flag: bool = False
    
    def __str__(self):
        return f"{self.cavity} Stepper Tuner"
    
    def check_abort(self):
        if self.abort_flag:
            self.abort()
            self.abort_flag = False
            raise utils.StepperAbortError(f"Abort requested for {self}")
    
    def abort(self):
        if not self._abort_pv:
            self._abort_pv = PV(self.pvPrefix + "ABORT_REQ")
        self._abort_pv.put(1)
    
    def move_positive(self):
        if not self._move_pos_pv:
            self._move_pos_pv = PV(self.pvPrefix + "MOV_REQ_POS")
        self._move_pos_pv.put(1)
    
    def move_negative(self):
        if not self._move_neg_pv:
            self._move_neg_pv = PV(self.pvPrefix + "MOV_REQ_NEG")
        self._move_neg_pv.put(1)
    
    @property
    def step_des_pv(self):
        if not self._step_des_pv:
            self._step_des_pv = PV(self.pvPrefix + "NSTEPS")
        return self._step_des_pv
    
    @property
    def step_des(self):
        return self.step_des_pv.get()
    
    @step_des.setter
    def step_des(self, value: int):
        self.step_des_pv.put(value)
    
    @property
    def motor_moving(self) -> bool:
        if not self._motor_moving_pv:
            self._motor_moving_pv = PV(self.pvPrefix + "STAT_MOV")
        return self._motor_moving_pv.get() == 1
    
    def reset_signed_steps(self):
        if not self._reset_signed_pv:
            self._reset_signed_pv = PV(self.pvPrefix + "TOTSGN_RESET")
        self._reset_signed_pv.put(0)
    
    @property
    def on_limit_switch(self) -> bool:
        if not self._limit_switch_a_pv:
            self._limit_switch_a_pv = PV(self.pvPrefix + "STAT_LIMA")
        if not self._limit_switch_b_pv:
            self._limit_switch_b_pv = PV(self.pvPrefix + "STAT_LIMB")
        
        return (self._limit_switch_a_pv.get()
                == utils.STEPPER_ON_LIMIT_SWITCH_VALUE or
                self._limit_switch_b_pv.get()
                == utils.STEPPER_ON_LIMIT_SWITCH_VALUE)
    
    @property
    def max_steps_pv(self) -> PV:
        if not self._max_steps_pv:
            self._max_steps_pv = PV(self.pvPrefix + "NSTEPS.DRVH")
        return self._max_steps_pv
    
    @property
    def max_steps(self):
        return self.max_steps_pv.get()
    
    @max_steps.setter
    def max_steps(self, value: int):
        self.max_steps_pv.put(value)
    
    @property
    def speed_pv(self):
        if not self._speed_pv:
            self._speed_pv = PV(self.pvPrefix + "VELO")
        return self._speed_pv
    
    @property
    def speed(self):
        return self.speed_pv.get()
    
    @speed.setter
    def speed(self, value: int):
        self.speed_pv.put(value)
    
    def restoreDefaults(self):
        self.max_steps = utils.DEFAULT_STEPPER_MAX_STEPS
        self.speed = utils.DEFAULT_STEPPER_SPEED
    
    def move(self, numSteps: int, maxSteps: int = utils.DEFAULT_STEPPER_MAX_STEPS,
             speed: int = utils.DEFAULT_STEPPER_SPEED, changeLimits: bool = True):
        """
        :param numSteps: positive for increasing cavity length, negative for decreasing
        :param maxSteps: the maximum number of steps allowed at once
        :param speed: the speed of the motor in steps/second
        :param changeLimits: whether or not to change the speed and steps
        :return:
        """
        
        if changeLimits:
            # on the off chance that someone tries to write a negative maximum
            self.max_steps = abs(maxSteps)
            
            # make sure that we don't exceed the speed limit as defined by the tuner experts
            self.speed = (speed if speed < utils.MAX_STEPPER_SPEED
                          else utils.MAX_STEPPER_SPEED)
        
        if abs(numSteps) <= maxSteps:
            self.step_des = abs(numSteps)
            self.issueMoveCommand(numSteps)
            self.restoreDefaults()
        else:
            self.step_des = maxSteps
            self.issueMoveCommand(numSteps)
            self.move(numSteps - (sign(numSteps) * maxSteps), maxSteps, speed,
                      False)
    
    def issueMoveCommand(self, numSteps):
        
        # this is necessary because the tuners for the HLs move the other direction
        if self.cavity.cryomodule.isHarmonicLinearizer:
            numSteps *= -1
        
        if sign(numSteps) == 1:
            self.move_positive()
        else:
            self.move_negative()
        
        print("Waiting 5s for the motor to start moving")
        sleep(5)
        
        while self.motor_moving:
            self.check_abort()
            print(f"{self} motor still moving, waiting 5s", datetime.now())
            sleep(5)
        
        print(f"{self} motor done moving")
        
        # the motor can be done moving for good OR bad reasons
        if self.on_limit_switch:
            raise utils.StepperError(f"{self.cavity} stepper motor on limit switch")


class Piezo:
    def __init__(self, cavity):
        # type (Cavity) -> None
        self.cavity: Cavity = cavity
        self.pvPrefix: str = self.cavity.pvPrefix + "PZT:"
        self._enable_PV: PV = None
        self._enable_stat_pv: PV = None
        self._feedback_mode_PV: PV = None
        self._feedback_stat_pv: PV = None
        self._feedback_setpoint_pv: PV = None
        self._dc_setpoint_pv: PV = None
        self._bias_voltage_pv: PV = None
    
    @property
    def bias_voltage_pv(self):
        if not self._bias_voltage_pv:
            self._bias_voltage_pv = PV(self.pvPrefix + "BIAS")
        return self._bias_voltage_pv
    
    @property
    def bias_voltage(self):
        return self.bias_voltage_pv.get()
    
    @bias_voltage.setter
    def bias_voltage(self, value):
        self.bias_voltage_pv.put(value)
    
    @property
    def dc_setpoint_pv(self) -> PV:
        if not self._dc_setpoint_pv:
            self._dc_setpoint_pv = PV(self.pvPrefix + "DAC_SP")
        return self._dc_setpoint_pv
    
    @property
    def dc_setpoint(self):
        return self.dc_setpoint_pv.get()
    
    @dc_setpoint.setter
    def dc_setpoint(self, value: float):
        self.dc_setpoint_pv.put(value)
    
    @property
    def feedback_setpoint_pv(self) -> PV:
        if not self._feedback_setpoint_pv:
            self._feedback_setpoint_pv = PV(self.pvPrefix + "INTEG_SP")
        return self._feedback_setpoint_pv
    
    @property
    def enable_pv(self) -> PV:
        if not self._enable_PV:
            self._enable_PV = PV(self.pvPrefix + "ENABLE")
        return self._enable_PV
    
    @property
    def is_enabled(self) -> bool:
        if not self._enable_stat_pv:
            self._enable_stat_pv = PV(self.pvPrefix + "ENABLESTAT")
        return self._enable_stat_pv.get() == utils.PIEZO_ENABLE_VALUE
    
    @property
    def feedback_mode_pv(self) -> PV:
        if not self._feedback_mode_PV:
            self._feedback_mode_PV = PV(self.pvPrefix + "MODECTRL")
        return self._feedback_mode_PV
    
    @property
    def feedback_stat(self):
        if not self._feedback_stat_pv:
            self._feedback_stat_pv = PV(self.pvPrefix + "MODESTAT")
        return self._feedback_stat_pv.get()
    
    @property
    def in_manual(self) -> bool:
        return self.feedback_stat == utils.PIEZO_MANUAL_VALUE
    
    def set_to_feedback(self):
        self.feedback_mode_pv.put(utils.PIEZO_FEEDBACK_VALUE)
    
    def set_to_manual(self):
        self.feedback_mode_pv.put(utils.PIEZO_MANUAL_VALUE)
    
    def enable_feedback(self):
        self.enable_pv.put(utils.PIEZO_DISABLE_VALUE)
        self.dc_setpoint = 25
        self.set_to_manual()
        self.enable_pv.put(utils.PIEZO_ENABLE_VALUE)


class Cavity:
    def __init__(self, cavityNum, rackObject, ssaClass=SSA,
                 stepperClass=StepperTuner, piezoClass=Piezo):
        # type: (int, Rack, Type[SSA], Type[StepperTuner], Type[Piezo]) -> None
        """
        Parameters
        ----------
        cavityNum: int cavity number i.e. 1 - 8
        rackObject: the rack object the cavities belong to
        """
        
        self._calc_probe_q_pv = None
        self.number = cavityNum
        self.rack: Rack = rackObject
        self.cryomodule: Cryomodule = self.rack.cryomodule
        self.linac = self.cryomodule.linac
        
        if self.cryomodule.isHarmonicLinearizer:
            self.length = 0.346
            self.frequency = 3.9e9
            self.loaded_q_lower_limit = utils.LOADED_Q_LOWER_LIMIT_HL
            self.loaded_q_upper_limit = utils.LOADED_Q_UPPER_LIMIT_HL
            self.steps_per_hz = utils.ESTIMATED_MICROSTEPS_PER_HZ_HL
        else:
            self.length = 1.038
            self.frequency = 1.3e9
            self.loaded_q_lower_limit = utils.LOADED_Q_LOWER_LIMIT
            self.loaded_q_upper_limit = utils.LOADED_Q_UPPER_LIMIT
            self.steps_per_hz = utils.ESTIMATED_MICROSTEPS_PER_HZ
        
        self.pvPrefix = "ACCL:{LINAC}:{CRYOMODULE}{CAVITY}0:".format(LINAC=self.linac.name,
                                                                     CRYOMODULE=self.cryomodule.name,
                                                                     CAVITY=self.number)
        
        self.ctePrefix = "CTE:CM{cm}:1{cav}".format(cm=self.cryomodule.name,
                                                    cav=self.number)
        
        self.ssa = ssaClass(self)
        self.steppertuner = stepperClass(self)
        self.piezo = piezoClass(self)
        
        self._push_ssa_slope_pv: PV = None
        self._save_ssa_slope_pv: PV = None
        self._interlock_reset_pv: PV = None
        
        self._drive_level_pv: PV = None
        
        self._characterization_start_pv: PV = None
        self._characterization_status_pv: PV = None
        
        self.currentQLoadedPV: PV = PV(self.pvPrefix + "QLOADED")
        self._measured_loaded_q_pv: PV = None
        self._push_loaded_q_pv: PV = None
        self.saveQLoadedPV: PV = PV(self.pvPrefix + "SAVE_QLOADED.PROC")
        
        self.currentCavityScalePV: PV = PV(self.pvPrefix + "CAV:SCALER_SEL.B")
        self._measured_scale_factor_pv: PV = None
        self._push_scale_factor_pv: PV = None
        self.saveCavityScalePV: PV = PV(self.pvPrefix + "SAVE_CAV_SCALE.PROC")
        
        self._ades_pv: PV = None
        self._aact_pv: PV = None
        self._ades_max_pv: PV = None
        
        self._rf_mode_ctrl_pv: PV = None
        self.rfModePV: PV = PV(self.pvPrefix + "RFMODE")
        
        self._rf_state_pv: PV = None
        self._rf_control_pv: PV = None
        
        self.pulseGoButtonPV: PV = PV(self.pvPrefix + "PULSE_DIFF_SUM")
        self._pulse_status_pv: PV = None
        self._pulse_on_time_pv: PV = None
        
        self.revWaveformPV: PV = PV(self.pvPrefix + "REV:AWF")
        self.fwdWaveformPV: PV = PV(self.pvPrefix + "FWD:AWF")
        self.cavWaveformPV: PV = PV(self.pvPrefix + "CAV:AWF")
        
        self.stepper_temp_pv: str = self.pvPrefix + "STEPTEMP"
        self._detune_best_pv: PV = None
        self.detune_rfs_PV: PV = PV(self.pvPrefix + "DF")
        
        self._rf_permit_pv: PV = None
        
        self._quench_latch_pv: PV = None
        self.quench_bypass_pv: str = self.pvPrefix + "QUENCH_BYP"
        
        self._cw_data_decim_pv: PV = None
        self._pulsed_data_decim_pv: PV = None
        
        self._tune_config_pv: PV = None
        self.chirp_prefix = self.pvPrefix + "CHIRP:"
        
        self._freq_start_pv: str = None
        self._freq_stop_pv: str = None
        
        self.abort_flag: bool = False
        
        self._hw_mode_pv: PV = None
    
    def __str__(self):
        return f"{self.linac.name} CM{self.cryomodule.name} Cavity {self.number}"
    
    @property
    def characterization_start_pv(self):
        if not self._characterization_start_pv:
            self._characterization_start_pv = PV(self.pvPrefix + "PROBECALSTRT")
        return self._characterization_start_pv
    
    def start_characterization(self):
        self.characterization_start_pv.put(1)
    
    @property
    def interlock_reset_pv(self):
        if not self._interlock_reset_pv:
            self._interlock_reset_pv = PV(self.pvPrefix + "INTLK_RESET_ALL")
        return self._interlock_reset_pv
    
    @property
    def cw_data_decimation_pv(self) -> PV:
        if not self._cw_data_decim_pv:
            self._cw_data_decim_pv = PV(self.pvPrefix + "ACQ_DECIM_SEL.A")
        return self._cw_data_decim_pv
    
    @property
    def cw_data_decimation(self):
        return self.cw_data_decimation_pv.get()
    
    @cw_data_decimation.setter
    def cw_data_decimation(self, value: float):
        self.cw_data_decimation_pv.put(value)
    
    @property
    def pulsed_data_decimation_pv(self):
        if not self._pulsed_data_decim_pv:
            self._pulsed_data_decim_pv = PV(self.pvPrefix + "ACQ_DECIM_SEL.C")
        return self._pulsed_data_decim_pv
    
    @property
    def pulsed_data_decimation(self):
        return self.pulsed_data_decimation_pv.get()
    
    @pulsed_data_decimation.setter
    def pulsed_data_decimation(self, value):
        self.pulsed_data_decimation_pv.put(value)
    
    @property
    def rf_control_pv(self):
        if not self._rf_control_pv:
            self._rf_control_pv = PV(self.pvPrefix + "RFCTRL")
        return self._rf_control_pv
    
    @property
    def rf_control(self):
        return self.rf_control_pv.get()
    
    @rf_control.setter
    def rf_control(self, value):
        self.rf_control_pv.put(value)
    
    @property
    def rf_mode_ctrl_pv(self) -> PV:
        if not self._rf_mode_ctrl_pv:
            self._rf_mode_ctrl_pv = PV(self.pvPrefix + "RFMODECTRL")
        return self._rf_mode_ctrl_pv
    
    def set_chirp_mode(self):
        self.rf_mode_ctrl_pv.put(utils.RF_MODE_CHIRP)
    
    def set_sel_mode(self):
        self.rf_mode_ctrl_pv.put(utils.RF_MODE_SEL)
    
    def set_sela_mode(self):
        self.rf_mode_ctrl_pv.put(utils.RF_MODE_SELA)
    
    def set_selap_mode(self):
        self.rf_mode_ctrl_pv.put(utils.RF_MODE_SELAP)
    
    @property
    def drive_level_pv(self):
        if not self._drive_level_pv:
            self._drive_level_pv = PV(self.pvPrefix + "SEL_ASET")
        return self._drive_level_pv
    
    @property
    def drive_level(self):
        return self._drive_level_pv.get()
    
    @drive_level.setter
    def drive_level(self, value):
        self.drive_level_pv.put(value)
    
    def push_ssa_slope(self):
        if not self._push_ssa_slope_pv:
            self._push_ssa_slope_pv = PV(self.pvPrefix + "PUSH_SSA_SLOPE.PROC")
        self._push_ssa_slope_pv.put(1)
    
    def save_ssa_slope(self):
        if not self._save_ssa_slope_pv:
            self._save_ssa_slope_pv = PV(self.pvPrefix + "SAVE_SSA_SLOPE.PROC")
        self._save_ssa_slope_pv.put(1)
    
    @property
    def measured_loaded_q(self) -> float:
        if not self._measured_loaded_q_pv:
            self._measured_loaded_q_pv = PV(self.pvPrefix + "QLOADED_NEW")
        return self._measured_loaded_q_pv.get()
    
    @property
    def measured_loaded_q_in_tolerance(self) -> bool:
        return (self.loaded_q_lower_limit
                < self.measured_loaded_q
                < self.loaded_q_upper_limit)
    
    def push_loaded_q(self):
        if not self._push_loaded_q_pv:
            self._push_loaded_q_pv = PV(self.pvPrefix + "PUSH_QLOADED.PROC")
        self._push_loaded_q_pv.put(1)
    
    @property
    def measured_scale_factor(self) -> float:
        if not self._measured_scale_factor_pv:
            self._measured_scale_factor_pv = PV(self.pvPrefix + "CAV:CAL_SCALEB_NEW")
        return self._measured_scale_factor_pv.get()
    
    @property
    def measured_scale_factor_in_tolerance(self) -> bool:
        return (utils.CAVITY_SCALE_LOWER_LIMIT
                < self.measured_scale_factor
                < utils.CAVITY_SCALE_UPPER_LIMIT)
    
    def push_scale_factor(self):
        if not self._push_scale_factor_pv:
            self._push_scale_factor_pv = PV(self.pvPrefix + "PUSH_CAV_SCALE.PROC")
        self._push_scale_factor_pv.put(1)
    
    @property
    def characterization_status(self):
        if not self._characterization_status_pv:
            self._characterization_status_pv = PV(self.pvPrefix + "PROBECALSTS")
        return self._characterization_status_pv.get()
    
    @property
    def characterization_running(self) -> bool:
        return self.characterization_status == utils.CALIBRATION_RUNNING_VALUE
    
    @property
    def characterization_crashed(self) -> bool:
        return self.characterization_status == utils.CALIBRATION_CRASHED_VALUE
    
    @property
    def pulse_on_time(self):
        if not self._pulse_on_time_pv:
            self._pulse_on_time_pv = PV(self.pvPrefix + "PULSE_ONTIME")
        return self._pulse_on_time_pv.get()
    
    @pulse_on_time.setter
    def pulse_on_time(self, value: int):
        if not self._pulse_on_time_pv:
            self._pulse_on_time_pv = PV(self.pvPrefix + "PULSE_ONTIME")
        self._pulse_on_time_pv.put(value)
    
    @property
    def pulse_status(self):
        if not self._pulse_status_pv:
            self._pulse_status_pv = PV(self.pvPrefix + "PULSE_STATUS")
        return self._pulse_status_pv.get()
    
    @property
    def rf_permit(self):
        if not self._rf_permit_pv:
            self._rf_permit_pv = self.pvPrefix + "RFPERMIT"
        return self._rf_permit_pv.get()
    
    @property
    def rf_inhibited(self) -> bool:
        return self.rf_permit == 0
    
    @property
    def ades(self):
        if not self._ades_pv:
            self._ades_pv = PV(self.pvPrefix + "ADES")
        return self._ades_pv.get()
    
    @ades.setter
    def ades(self, value: float):
        if not self._ades_pv:
            self._ades_pv = PV(self.pvPrefix + "ADES")
        self._ades_pv.put(value)
    
    @property
    def aact(self):
        if not self._aact_pv:
            self._aact_pv = PV(self.pvPrefix + "AACTMEAN")
        return self._aact_pv.get()
    
    @property
    def ades_max(self):
        if not self._ades_max_pv:
            self._ades_max_pv = PV(self.pvPrefix + "ADES_MAX")
        return self._ades_max_pv.get()
    
    @property
    def edm_macro_string(self):
        rfs_map = {1: "1A", 2: "1A", 3: "2A", 4: "2A", 5: "1B", 6: "1B", 7: "2B", 8: "2B"}
        
        rfs = rfs_map[self.number]
        
        r = self.rack.rackName
        cm = self.cryomodule.pvPrefix[:-3]  # need to remove trailing colon and zeroes to match needed format
        id = self.cryomodule.name
        
        ch = 2 if self.number in [2, 4] else 1
        
        macro_string = ",".join(["C={c}".format(c=self.number),
                                 "RFS={rfs}".format(rfs=rfs),
                                 "R={r}".format(r=r), "CM={cm}".format(cm=cm),
                                 "ID={id}".format(id=id),
                                 "CH={ch}".format(ch=ch)])
        return macro_string
    
    @property
    def hw_mode(self):
        if not self._hw_mode_pv:
            self._hw_mode_pv = PV(self.pvPrefix + "HWMODE")
        return self._hw_mode_pv.get()
    
    @property
    def is_online(self) -> bool:
        return self.hw_mode == utils.HW_MODE_ONLINE_VALUE
    
    @property
    def is_quenched(self) -> bool:
        if not self._quench_latch_pv:
            self._quench_latch_pv = PV(self.pvPrefix + "QUENCH_LTCH")
        return self._quench_latch_pv.get() == 1
    
    @property
    def tune_config_pv(self) -> PV:
        if not self._tune_config_pv:
            self._tune_config_pv = PV(self.pvPrefix + "TUNE_CONFIG")
        return self._tune_config_pv
    
    @property
    def freq_start_pv(self) -> PV:
        if not self._freq_start_pv:
            self._freq_start_pv = PV(self.chirp_prefix + "FREQ_START")
        return self._freq_start_pv
    
    @property
    def freq_stop_pv(self) -> PV:
        if not self._freq_stop_pv:
            self._freq_stop_pv = PV(self.chirp_prefix + "FREQ_STOP")
        return self._freq_stop_pv
    
    @property
    def calc_probe_q_pv(self):
        if not self._calc_probe_q_pv:
            self._calc_probe_q_pv = PV(self.pvPrefix + "QPROBE_CALC1.PROC")
        return self._calc_probe_q_pv
    
    def set_chirp_range(self, offset: int):
        offset = abs(offset)
        print(f"Setting chirp range for {self} to +/- {offset} Hz")
        self.freq_start_pv.put(-offset)
        self.freq_stop_pv.put(offset)
        print(f"Chirp range set for {self}")
    
    @property
    def rf_state(self):
        return self.rf_state_pv.get()
    
    @property
    def is_on(self):
        return self.rf_state == 1
    
    @property
    def rf_state_pv(self) -> PV:
        if not self._rf_state_pv:
            self._rf_state_pv = PV(self.pvPrefix + "RFSTATE")
        return self._rf_state_pv
    
    def move_to_resonance(self, reset_signed_steps=False):
        self.auto_tune(des_detune=0,
                       config_val=utils.TUNE_CONFIG_RESONANCE_VALUE,
                       reset_signed_steps=reset_signed_steps)
    
    @property
    def detune_best(self):
        if not self._detune_best_pv:
            self._detune_best_pv = PV(self.pvPrefix + "DFBEST")
        return self._detune_best_pv.get()
    
    def auto_tune(self, des_detune, config_val, tolerance=50,
                  chirp_range=200000, reset_signed_steps=False):
        self.setup_tuning(chirp_range)
        
        if self._detune_best_pv.severity == 3:
            raise utils.DetuneError(f"Detune for {self} is invalid")
        
        delta = self.detune_best - des_detune
        
        self.tune_config_pv.put(utils.TUNE_CONFIG_OTHER_VALUE)
        
        expected_steps: int = abs(int(delta * self.steps_per_hz))
        steps_moved: int = 0
        
        if reset_signed_steps:
            self.steppertuner.reset_signed_steps()
        
        while abs(delta) > tolerance:
            est_steps = int(0.9 * delta * self.steps_per_hz)
            
            print(f"Moving stepper for {self} {est_steps} steps")
            
            self.steppertuner.move(est_steps,
                                   maxSteps=est_steps * 1.1,
                                   speed=utils.MAX_STEPPER_SPEED)
            steps_moved += abs(est_steps)
            
            if steps_moved > expected_steps * 1.1:
                raise utils.DetuneError(f"{self} motor moved more steps than expected")
            
            # this should catch if the chirp range is wrong or if the cavity is off
            if self._detune_best_pv.severity == EPICS_INVALID_VAL:
                self.find_chirp_range()
            
            delta = self.detune_best - des_detune
        
        self.tune_config_pv.put(config_val)
    
    def checkAndSetOnTime(self):
        """
        In pulsed mode the cavity has a duty cycle determined by the on time and
        off time. We want the on time to be 70 ms or else the various cavity
        parameters calculated from the waveform (e.g. the RF gradient) won't be
        accurate.
        :return:
        """
        print("Checking RF Pulse On Time...")
        if self.pulse_on_time != utils.NOMINAL_PULSED_ONTIME:
            print("Setting RF Pulse On Time to {ontime} ms".format(ontime=utils.NOMINAL_PULSED_ONTIME))
            self.pulse_on_time = utils.NOMINAL_PULSED_ONTIME
            self.pushGoButton()
    
    def pushGoButton(self):
        """
        Many of the changes made to a cavity don't actually take effect until the
        go button is pressed
        :return:
        """
        self.pulseGoButtonPV.put(1)
        while self.pulse_status < 2:
            print("waiting for pulse state", datetime.now())
            sleep(1)
        if self.pulse_status > 2:
            raise utils.PulseError("Unable to pulse cavity")
    
    def turnOn(self):
        print(f"Turning {self} on")
        if self.is_online:
            self.ssa.turn_on()
            self.rf_control = 1
            
            while not self.is_on:
                self.check_abort()
                print(f"waiting for {self} to turn on", datetime.now())
                sleep(1)
            
            print(f"{self} on")
        else:
            raise utils.CavityHWModeError(f"{self} not online")
    
    def turnOff(self):
        print(f"turning {self} off")
        self.rf_control = 0
        while self.is_on:
            self.check_abort()
            print(f"waiting for {self} to turn off")
            sleep(1)
        print(f"{self} off")
    
    def setup_selap(self, desAmp: float = 5):
        self.setup_rf(desAmp)
        self.set_selap_mode()
        print(f"{self} set up in SELAP")
    
    def setup_sela(self, desAmp: float = 5):
        self.setup_rf(desAmp)
        self.set_sela_mode()
        print(f"{self} set up in SELA")
    
    def check_abort(self):
        if self.abort_flag:
            self.abort_flag = False
            self.turnOff()
            raise utils.CavityAbortError(f"Abort requested for {self}")
    
    def setup_rf(self, desAmp):
        if desAmp > self.ades_max:
            print(f"Requested amplitude for {self} too high - ramping up to AMAX instead")
            desAmp = self.ades_max
        print(f"setting up {self}")
        self.turnOff()
        self.ssa.calibrate(self.ssa.drivemax)
        self.move_to_resonance()
        
        self.characterize()
        self.calc_probe_q_pv.put(1)
        
        self.check_abort()
        
        self.reset_data_decimation()
        
        self.check_abort()
        
        self.ades = min(5, desAmp)
        self.set_sel_mode()
        self.piezo.set_to_feedback()
        self.set_sela_mode()
        
        self.check_abort()
        
        if desAmp <= 10:
            self.walk_amp(desAmp, 0.5)
        
        else:
            self.walk_amp(10, 0.5)
            self.walk_amp(desAmp, 0.1)
    
    def reset_data_decimation(self):
        print(f"Setting data decimation for {self}")
        self.cw_data_decimation = 255
        self.pulsed_data_decimation = 255
    
    def setup_tuning(self, chirp_range=200000):
        print(f"enabling {self} piezo")
        while not self.piezo.is_enabled:
            print(f"{self} piezo not enabled, retrying")
            self.piezo.enable_pv.put(utils.PIEZO_DISABLE_VALUE)
            sleep(1)
            self.piezo.enable_pv.put(utils.PIEZO_ENABLE_VALUE)
            sleep(1)
        
        print(f"setting {self} piezo to manual")
        while not self.piezo.in_manual:
            print(f"{self} piezo not in manual, retrying")
            self.piezo.set_to_feedback()
            sleep(1)
            self.piezo.set_to_manual()
            sleep(1)
        
        print(f"setting {self} piezo DC voltage offset to 0V")
        self.piezo.dc_setpoint = 0
        
        print(f"setting {self} piezo bias voltage to 25V")
        self.piezo.bias_voltage = 25
        
        print(f"setting {self} drive level to {utils.SAFE_PULSED_DRIVE_LEVEL}")
        self.drive_level = utils.SAFE_PULSED_DRIVE_LEVEL
        
        print(f"setting {self} RF to chirp")
        self.set_chirp_mode()
        
        print(f"turning {self} RF on and waiting 5s for detune to catch up")
        self.ssa.turn_on()
        
        self.reset_interlocks()
        
        self.turnOn()
        sleep(5)
        
        self.find_chirp_range(chirp_range)
    
    def find_chirp_range(self, chirp_range=200000):
        self.set_chirp_range(chirp_range)
        sleep(1)
        if self._detune_best_pv.severity == EPICS_INVALID_VAL:
            if chirp_range < 500000:
                self.find_chirp_range(int(chirp_range * 1.25))
            else:
                raise utils.DetuneError(f"{self}: No valid detune found within"
                                        f"+/-500000Hz chirp range")
    
    def reset_interlocks(self, wait: int = 3, attempt: int = 0):
        # TODO see if it makes sense to implement this non-recursively
        print(f"Resetting interlocks for {self} and waiting {wait}s")
        self.interlock_reset_pv.put(1)
        sleep(wait)
        
        if self.rf_inhibited:
            if attempt > 2:
                raise utils.CavityFaultError(f"{self} still faulted after 3 reset attempts")
            else:
                print(f"{self} reset unsuccessful; retrying")
                self.reset_interlocks(wait=wait + 2, attempt=attempt + 1)
        else:
            print(f"{self} interlocks reset")
    
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
        
        print(f"starting {self} cavity characterization")
        self.start_characterization()
        print(f"waiting 2s for {self} cavity characterization script to run")
        sleep(2)
        
        while self.characterization_running:
            print(f"waiting for {self} characterization"
                  f" to stop running", datetime.now())
            sleep(1)
        
        sleep(2)
        
        if self.characterization_crashed:
            raise utils.CavityQLoadedCalibrationError(f"{self} characterization crashed")
        
        print(f"pushing {self} characterization results")
        
        if self.measured_loaded_q_in_tolerance:
            self.push_loaded_q()
        else:
            raise utils.CavityQLoadedCalibrationError(f"{self} loaded Q out of tolerance")
        
        if self.measured_scale_factor_in_tolerance:
            self.push_scale_factor()
        else:
            raise utils.CavityScaleFactorCalibrationError(f"{self} scale factor out of tolerance")
        
        self.reset_data_decimation()
        
        print(f"restoring {self} piezo feedback setpoint to 0")
        self.piezo.feedback_setpoint_pv.put(0)
        
        print(f"{self} characterization successful")
    
    def walk_amp(self, des_amp, step_size):
        print(f"walking {self} to {des_amp}")
        
        while self.ades <= (des_amp - step_size):
            self.check_abort()
            if self.is_quenched:
                raise utils.QuenchError(f"{self} quench detected, aborting rampup")
            self.ades = self.ades + step_size
            # to avoid tripping sensitive interlock
            sleep(0.1)
        
        if self.ades != des_amp:
            self.ades = des_amp
        
        print(f"{self} at {des_amp}")


class Magnet:
    def __init__(self, magnettype, cryomodule):
        # type: (str, Cryomodule) -> None
        self.pvprefix = "{magnettype}:{linac}:{cm}85:".format(magnettype=magnettype,
                                                              linac=cryomodule.linac.name,
                                                              cm=cryomodule.name)
        self.name = magnettype
        self.cryomodule: Cryomodule = cryomodule
        self._bdes_pv: PV = None
        self._control_pv: PV = None
        self.interlockPV: PV = PV(self.pvprefix + 'INTLKSUMY')
        self.ps_statusPV: PV = PV(self.pvprefix + 'STATE')
        self.bactPV: PV = PV(self.pvprefix + 'BACT')
        self.iactPV: PV = PV(self.pvprefix + 'IACT')
        # changing IDES immediately perturbs
        self.idesPV: PV = PV(self.pvprefix + 'IDES')
    
    @property
    def bdes(self):
        if not self._bdes_pv:
            self._bdes_pv = PV(self.pvprefix + 'BDES')
        return self._bdes_pv.get()
    
    @property
    def control_pv(self) -> PV:
        if not self._control_pv:
            self._control_pv = PV(self.pvprefix + 'CTRL')
        return self._control_pv
    
    @bdes.setter
    def bdes(self, value):
        self._bdes_pv.put(value)
        self.control_pv.put(utils.MAGNET_TRIM_VALUE)
    
    def reset(self):
        self.control_pv.put(utils.MAGNET_RESET_VALUE)
    
    def turnOn(self):
        self.control_pv.put(utils.MAGNET_ON_VALUE)
    
    def turnOff(self):
        self.control_pv.put(utils.MAGNET_OFF_VALUE)
    
    def degauss(self):
        self.control_pv.put(utils.MAGNET_DEGAUSS_VALUE)
    
    def trim(self):
        self.control_pv.put(utils.MAGNET_TRIM_VALUE)


class Rack:
    def __init__(self, rackName, cryoObject, cavityClass=Cavity, ssaClass=SSA,
                 stepperClass=StepperTuner, piezoClass=Piezo):
        # type: (str, Cryomodule, Type[Cavity], Type[SSA], Type[StepperTuner], Type[Piezo]) -> None
        """
        Parameters
        ----------
        rackName: str name of rack (always either "A" or "B")
        cryoObject: the cryomodule object this rack belongs to
        cavityClass: cavity object
        """
        
        self.cryomodule = cryoObject
        self.rackName = rackName
        self.cavities: Dict[int, Cavity] = {}
        self.pvPrefix = self.cryomodule.pvPrefix + "RACK{RACK}:".format(RACK=self.rackName)
        
        if rackName == "A":
            # rack A always has cavities 1 - 4
            for cavityNum in range(1, 5):
                self.cavities[cavityNum] = cavityClass(cavityNum=cavityNum,
                                                       rackObject=self,
                                                       ssaClass=ssaClass,
                                                       stepperClass=stepperClass,
                                                       piezoClass=piezoClass)
        
        elif rackName == "B":
            # rack B always has cavities 5 - 8
            for cavityNum in range(5, 9):
                self.cavities[cavityNum] = cavityClass(cavityNum=cavityNum,
                                                       rackObject=self,
                                                       ssaClass=ssaClass,
                                                       stepperClass=stepperClass,
                                                       piezoClass=piezoClass)
        
        else:
            raise Exception(f"Bad rack name {rackName}")


class Cryomodule:
    
    def __init__(self, cryoName, linacObject, cavityClass=Cavity,
                 magnetClass=Magnet, rackClass=Rack, isHarmonicLinearizer=False,
                 ssaClass=SSA, stepperClass=StepperTuner, piezoClass=Piezo):
        # type: (str, Linac, Type[Cavity], Type[Magnet], Type[Rack], bool, Type[SSA], Type[StepperTuner], Type[Piezo]) -> None
        """
        Parameters
        ----------
        cryoName: str name of Cryomodule i.e. "02", "03", "H1", "H2"
        linacObject: the linac object this cryomodule belongs to i.e. CM02 is in linac L1B
        cavityClass: cavity object
        """
        
        self.name: str = cryoName
        self.linac: Linac = linacObject
        self.isHarmonicLinearizer = isHarmonicLinearizer
        
        if not isHarmonicLinearizer:
            self.quad: Magnet = magnetClass("QUAD", self)
            self.xcor: Magnet = magnetClass("XCOR", self)
            self.ycor: Magnet = magnetClass("YCOR", self)
        
        self.pvPrefix = "ACCL:{LINAC}:{CRYOMODULE}00:".format(LINAC=self.linac.name,
                                                              CRYOMODULE=self.name)
        self.ctePrefix = "CTE:CM{cm}:".format(cm=self.name)
        self.cvtPrefix = "CVT:CM{cm}:".format(cm=self.name)
        self.cpvPrefix = "CPV:CM{cm}:".format(cm=self.name)
        self.jtPrefix = "CLIC:CM{cm}:3001:PVJT:".format(cm=self.name)
        
        self.dsLevelPV: str = "CLL:CM{cm}:2301:DS:LVL".format(cm=self.name)
        self.usLevelPV: str = "CLL:CM{cm}:2601:US:LVL".format(cm=self.name)
        self.dsPressurePV: str = "CPT:CM{cm}:2302:DS:PRESS".format(cm=self.name)
        self.jtValveReadbackPV: str = self.jtPrefix + "ORBV"
        self.heater_readback_pv: str = f"CPIC:CM{self.name}:0000:EHCV:ORBV"
        
        self.racks = {"A": rackClass(rackName="A", cryoObject=self,
                                     cavityClass=cavityClass,
                                     ssaClass=ssaClass,
                                     stepperClass=stepperClass,
                                     piezoClass=piezoClass),
                      "B": rackClass(rackName="B", cryoObject=self,
                                     cavityClass=cavityClass,
                                     ssaClass=ssaClass,
                                     stepperClass=stepperClass,
                                     piezoClass=piezoClass)}
        
        self.cavities: Dict[int, cavityClass] = {}
        self.cavities.update(self.racks["A"].cavities)
        self.cavities.update(self.racks["B"].cavities)
        
        if isHarmonicLinearizer:
            # two cavities share one SSA, this is the mapping
            cavity_ssa_pairs = [(1, 5), (2, 6), (3, 7), (4, 8)]
            
            for (leader, follower) in cavity_ssa_pairs:
                self.cavities[follower].ssa = self.cavities[leader].ssa
            self.couplerVacuumPVs: List[PV] = [PV(self.linac.vacuumPrefix + '{cm}09:COMBO_P'.format(cm=self.name)),
                                               PV(self.linac.vacuumPrefix + '{cm}19:COMBO_P'.format(cm=self.name))]
        else:
            self.couplerVacuumPVs: List[PV] = [PV(self.linac.vacuumPrefix + '{cm}14:COMBO_P'.format(cm=self.name))]
        
        self.vacuumPVs: List[str] = [pv.pvname for pv in (self.couplerVacuumPVs
                                                          + self.linac.beamlineVacuumPVs
                                                          + self.linac.insulatingVacuumPVs)]


class Linac:
    def __init__(self, linacName, beamlineVacuumInfixes, insulatingVacuumCryomodules):
        # type: (str, List[str], List[str]) -> None
        """
        Parameters
        ----------
        linacName: str name of Linac i.e. "L0B", "L1B", "L2B", "L3B"
        """
        
        self.name = linacName
        self.cryomodules: Dict[str, Cryomodule] = {}
        self.vacuumPrefix = 'VGXX:{linac}:'.format(linac=self.name)
        
        self.beamlineVacuumPVs = [PV(self.vacuumPrefix
                                     + '{infix}:COMBO_P'.format(infix=infix))
                                  for infix in beamlineVacuumInfixes]
        self.insulatingVacuumPVs = [PV(self.vacuumPrefix
                                       + '{cm}96:COMBO_P'.format(cm=cm))
                                    for cm in insulatingVacuumCryomodules]
    
    def addCryomodules(self, cryomoduleStringList: List[str], cryomoduleClass: Type[Cryomodule] = Cryomodule,
                       cavityClass: Type[Cavity] = Cavity, rackClass: Type[Rack] = Rack,
                       magnetClass: Type[Magnet] = Magnet, isHarmonicLinearizer: bool = False,
                       ssaClass: Type[SSA] = SSA, stepperClass: Type[StepperTuner] = StepperTuner):
        for cryomoduleString in cryomoduleStringList:
            self.addCryomodule(cryomoduleName=cryomoduleString,
                               cryomoduleClass=cryomoduleClass,
                               cavityClass=cavityClass, rackClass=rackClass,
                               magnetClass=magnetClass,
                               isHarmonicLinearizer=isHarmonicLinearizer,
                               ssaClass=ssaClass,
                               stepperClass=stepperClass)
    
    def addCryomodule(self, cryomoduleName: str, cryomoduleClass: Type[Cryomodule] = Cryomodule,
                      cavityClass: Type[Cavity] = Cavity, rackClass: Type[Rack] = Rack,
                      magnetClass: Type[Magnet] = Magnet,
                      isHarmonicLinearizer: bool = False, ssaClass: Type[SSA] = SSA,
                      stepperClass: Type[StepperTuner] = StepperTuner):
        self.cryomodules[cryomoduleName] = cryomoduleClass(cryoName=cryomoduleName,
                                                           linacObject=self,
                                                           cavityClass=cavityClass,
                                                           rackClass=rackClass,
                                                           magnetClass=magnetClass,
                                                           isHarmonicLinearizer=isHarmonicLinearizer,
                                                           ssaClass=ssaClass,
                                                           stepperClass=stepperClass)


# Global list of superconducting linac objects
L0B = ["01"]
L1B = ["02", "03"]
L1BHL = ["H1", "H2"]
L2B = ["04", "05", "06", "07", "08", "09", "10", "11", "12", "13", "14", "15"]
L3B = ["16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27",
       "28", "29", "30", "31", "32", "33", "34", "35"]

LINAC_TUPLES = [("L0B", L0B), ("L1B", L1B), ("L2B", L2B), ("L3B", L3B)]

BEAMLINEVACUUM_INFIXES = [['0198'], ['0202', 'H292'], ['0402', '1592'], ['1602', '2594', '2598', '3592']]
INSULATINGVACUUM_CRYOMODULES = [['01'], ['02', 'H1'], ['04', '06', '08', '10', '12', '14'],
                                ['16', '18', '20', '22', '24', '27', '29', '31', '33', '34']]

linacs = {"L0B": Linac("L0B", beamlineVacuumInfixes=BEAMLINEVACUUM_INFIXES[0],
                       insulatingVacuumCryomodules=INSULATINGVACUUM_CRYOMODULES[0]),
          "L1B": Linac("L1B", beamlineVacuumInfixes=BEAMLINEVACUUM_INFIXES[1],
                       insulatingVacuumCryomodules=INSULATINGVACUUM_CRYOMODULES[1]),
          "L2B": Linac("L2B", beamlineVacuumInfixes=BEAMLINEVACUUM_INFIXES[2],
                       insulatingVacuumCryomodules=INSULATINGVACUUM_CRYOMODULES[2]),
          "L3B": Linac("L3B", beamlineVacuumInfixes=BEAMLINEVACUUM_INFIXES[3],
                       insulatingVacuumCryomodules=INSULATINGVACUUM_CRYOMODULES[3])}

ALL_CRYOMODULES = L0B + L1B + L1BHL + L2B + L3B
ALL_CRYOMODULES_NO_HL = L0B + L1B + L2B + L3B


class CryoDict(dict):
    def __init__(self, cryomoduleClass: Type[Cryomodule] = Cryomodule,
                 cavityClass: Type[Cavity] = Cavity,
                 magnetClass: Type[Magnet] = Magnet, rackClass: Type[Rack] = Rack,
                 stepperClass: Type[StepperTuner] = StepperTuner,
                 ssaClass: Type[SSA] = SSA, piezoClass: Type[Piezo] = Piezo):
        super().__init__()
        
        self.cryomoduleClass = cryomoduleClass
        self.cavityClass = cavityClass
        self.magnetClass = magnetClass
        self.rackClass = rackClass
        self.stepperClass = stepperClass
        self.ssaClass = ssaClass
        self.piezoClass = piezoClass
    
    def __missing__(self, key):
        if key in L0B:
            linac = linacs['L0B']
        elif key in L1B:
            linac = linacs['L1B']
        elif key in L1BHL:
            linac = linacs['L1B']
        elif key in L2B:
            linac = linacs['L2B']
        elif key in L3B:
            linac = linacs['L3B']
        else:
            raise KeyError(f"Cryomodule {key} not found in any linac region.")
        cryomodule = self.cryomoduleClass(cryoName=key,
                                          linacObject=linac,
                                          cavityClass=self.cavityClass,
                                          magnetClass=self.magnetClass,
                                          rackClass=self.rackClass,
                                          stepperClass=self.stepperClass,
                                          isHarmonicLinearizer=(key in L1BHL),
                                          ssaClass=self.ssaClass,
                                          piezoClass=self.piezoClass)
        self[key] = cryomodule
        return cryomodule


CRYOMODULE_OBJECTS = CryoDict()
