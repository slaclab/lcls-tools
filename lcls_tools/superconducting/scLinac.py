################################################################################
# Utility classes for superconducting linac
# NOTE: For some reason, using python 3 style type annotations causes circular
#       import issues, so leaving as python 2 style for now
################################################################################
from datetime import datetime
from time import sleep
from typing import Dict, List, Type

from epics import caget, caput
from numpy import isclose, sign

import lcls_tools.superconducting.scLinacUtils as utils
from lcls_tools.common.pyepics_tools.pyepicsUtils import EPICS_INVALID_VAL, PV

HL_SSA_MAP = {1: 1, 2: 2, 3: 3, 4: 4, 5: 1, 6: 2, 7: 3, 8: 4}


class SSA:
    def __init__(self, cavity):
        # type: (Cavity) -> None
        self.cavity: Cavity = cavity
        
        self.pvPrefix = self.cavity.pvPrefix + "SSA:"
        
        if self.cavity.cryomodule.isHarmonicLinearizer:
            cavity_num = HL_SSA_MAP[self.cavity.number]
            hl_prefix = "ACCL:{LINAC}:{CRYOMODULE}{CAVITY}0:SSA:".format(LINAC=self.cavity.linac.name,
                                                                         CRYOMODULE=self.cavity.cryomodule.name,
                                                                         CAVITY=cavity_num)
            self.fwd_power_lower_limit = 500
            
            self.ps_volt_setpoint1_pv: str = hl_prefix + "PSVoltSetpt1"
            self._ps_volt_setpoint1_pv_obj: PV = None
            
            self.ps_volt_setpoint2_pv: str = hl_prefix + "PSVoltSetpt2"
            self._ps_volt_setpoint2_pv_obj: PV = None
            
            self.statusPV: str = (hl_prefix + "StatusMsg")
            self.turnOnPV: PV = PV(hl_prefix + "PowerOn")
            self.turnOffPV: PV = PV(hl_prefix + "PowerOff")
            self.resetPV: str = hl_prefix + "FaultReset"
        
        else:
            self.statusPV: str = (self.pvPrefix + "StatusMsg")
            self.turnOnPV: PV = PV(self.pvPrefix + "PowerOn")
            self.turnOffPV: PV = PV(self.pvPrefix + "PowerOff")
            self.resetPV: str = self.pvPrefix + "FaultReset"
            self.fwd_power_lower_limit = 3000
        
        self.calibrationStartPV: PV = PV(self.pvPrefix + "CALSTRT")
        self.calibrationStatusPV: PV = PV(self.pvPrefix + "CALSTS")
        self.calResultStatusPV: PV = PV(self.pvPrefix + "CALSTAT")
        
        self.currentSlopePV: PV = PV(self.pvPrefix + "SLOPE")
        self.measuredSlopePV: PV = PV(self.pvPrefix + "SLOPE_NEW")
        
        self.maxdrive_setpoint_pv: str = self.pvPrefix + "DRV_MAX_REQ"
        self._maxdrive_setpoint_pv_obj: PV = None
        self.saved_maxdrive_pv: str = self.pvPrefix + "DRV_MAX_SAVE"
        self._saved_maxdrive_pv_obj: PV = None
        self._max_fwd_pwr_pv: PV = None
    
    @property
    def max_fwd_pwr(self):
        if not self._max_fwd_pwr_pv:
            self._max_fwd_pwr_pv = PV(self.pvPrefix + "CALPWR")
        return self._max_fwd_pwr_pv.get()
    
    @property
    def drivemax(self):
        if not self._saved_maxdrive_pv_obj:
            self._saved_maxdrive_pv_obj = PV(self.saved_maxdrive_pv)
        saved_val = self._saved_maxdrive_pv_obj.get()
        return (saved_val if saved_val
                else (1 if self.cavity.cryomodule.isHarmonicLinearizer else 0.8))
    
    @property
    def maxdrive_setpoint_pv_obj(self):
        if not self._maxdrive_setpoint_pv_obj:
            self._maxdrive_setpoint_pv_obj = PV(self.maxdrive_setpoint_pv)
        return self._maxdrive_setpoint_pv_obj
    
    def calibrate(self, drivemax, attempt=0):
        print(f"Running {self.cavity} SSA calibration with drivemax {drivemax}")
        
        self.maxdrive_setpoint_pv_obj.put(drivemax)
        
        self.cavity.check_abort()
        
        try:
            self.runCalibration()
        
        except (utils.SSACalibrationToleranceError, utils.SSACalibrationError) as e:
            if attempt < 3:
                self.calibrate(drivemax, attempt + 1)
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
    
    def turnOn(self):
        self.setPowerState(True)
        
        if self.cavity.cryomodule.isHarmonicLinearizer:
            self.ps_volt_setpoint2_pv_obj.put(utils.HL_SSA_PS_SETPOINT)
            self.ps_volt_setpoint1_pv_obj.put(utils.HL_SSA_PS_SETPOINT)
    
    def turnOff(self):
        self.setPowerState(False)
    
    def reset(self):
        print(f"Resetting {self.cavity} SSA...")
        caput(self.resetPV, 1)
        while caget(self.statusPV) == utils.SSA_STATUS_RESETTING_FAULTS_VALUE:
            sleep(1)
        if caget(self.statusPV) in [utils.SSA_STATUS_FAULTED_VALUE,
                                    utils.SSA_STATUS_FAULT_RESET_FAILED_VALUE]:
            raise utils.SSAFaultError(f"Unable to reset {self.cavity} SSA")
    
    def setPowerState(self, turnOn: bool):
        print(f"Setting {self.cavity} SSA power...")
        
        if turnOn:
            if caget(self.statusPV) != utils.SSA_STATUS_ON_VALUE:
                while caput(self.turnOnPV.pvname, 1) != 1:
                    self.cavity.check_abort()
                    print(f"Trying to power on {self.cavity} SSA")
                while caget(self.statusPV) != utils.SSA_STATUS_ON_VALUE:
                    self.cavity.check_abort()
                    print(f"waiting for {self.cavity} SSA to turn on")
                    sleep(1)
        else:
            if caget(self.statusPV) == utils.SSA_STATUS_ON_VALUE:
                while caput(self.turnOffPV.pvname, 1) != 1:
                    self.cavity.check_abort()
                    print(f"Trying to power off {self.cavity} SSA")
                while caget(self.statusPV) == utils.SSA_STATUS_ON_VALUE:
                    self.cavity.check_abort()
                    print(f"waiting for {self.cavity} SSA to turn off")
                    sleep(1)
        
        print(f"{self.cavity} SSA power set")
    
    def runCalibration(self):
        """
        Runs the SSA through its range and finds the slope that describes
        the relationship between SSA drive signal and output power
        :return:
        """
        self.reset()
        self.setPowerState(True)
        
        self.cavity.reset_interlocks()
        
        print(f"Running SSA Calibration for {self.cavity}")
        self.calibrationStartPV.put(1)
        
        while self.calibrationStatusPV.get() == 2:
            print(f"waiting for {self.calibrationStatusPV.pvname} to stop running",
                  datetime.now())
            sleep(1)
        
        if self.calibrationStatusPV.get() == 0:
            raise utils.SSACalibrationError("{pv} crashed"
                                            .format(pv=self.calibrationStatusPV.pvname))
        
        if self.calResultStatusPV.get() != utils.SSA_RESULT_GOOD_STATUS_VALUE:
            raise utils.SSACalibrationError(f"{self.calResultStatusPV.pvname} not in good state")
        
        if self.max_fwd_pwr < self.fwd_power_lower_limit:
            raise utils.SSACalibrationToleranceError(f"{self.cavity} SSA forward power too low")
        
        if (self.measuredSlopePV.get() < utils.SSA_SLOPE_LOWER_LIMIT
                or self.measuredSlopePV.get() > utils.SSA_SLOPE_UPPER_LIMIT):
            raise utils.SSACalibrationToleranceError(f"{self.cavity} SSA measured slope out of tolerance")
        
        while self.measuredSlopePV.get() != self.currentSlopePV.get():
            print(f"{self.cavity} SSA current slope differs from measured slope, pushing")
            self.cavity.pushSSASlopePV.put(1)
            sleep(0.5)


class StepperTuner:
    def __init__(self, cavity):
        # type (Cavity) -> None
        
        self.cavity: Cavity = cavity
        self.pvPrefix: str = self.cavity.pvPrefix + "STEP:"
        
        self.move_pos_pv: PV = PV(self.pvPrefix + "MOV_REQ_POS")
        self.move_neg_pv: PV = PV(self.pvPrefix + "MOV_REQ_NEG")
        self.abort_pv: PV = PV(self.pvPrefix + "ABORT_REQ")
        self.step_des_pv: PV = PV(self.pvPrefix + "NSTEPS")
        self.max_steps_pv: PV = PV(self.pvPrefix + "NSTEPS.DRVH")
        self.speed_pv: PV = PV(self.pvPrefix + "VELO")
        self.step_tot_pv: PV = PV(self.pvPrefix + "REG_TOTABS")
        self.step_signed_pv: PV = PV(self.pvPrefix + "REG_TOTSGN")
        self.reset_tot_pv: PV = PV(self.pvPrefix + "TOTABS_RESET")
        self._reset_signed_pv: PV = None
        self.steps_cold_landing_pv: PV = PV(self.pvPrefix + "NSTEPS_COLD")
        self.push_signed_cold_pv: PV = PV(self.pvPrefix + "PUSH_NSTEPS_COLD.PROC")
        self.push_signed_park_pv: PV = PV(self.pvPrefix + "PUSH_NSTEPS_PARK.PROC")
        self.motor_moving_pv: PV = PV(self.pvPrefix + "STAT_MOV")
        self.motor_done_pv: PV = PV(self.pvPrefix + "STAT_DONE")
        self._limit_switch_a_pv: PV = None
        self._limit_switch_b_pv: PV = None
        
        self.abort_flag: bool = False
    
    @property
    def reset_signed_pv(self):
        if not self._reset_signed_pv:
            self._reset_signed_pv = PV(self.pvPrefix + "TOTSGN_RESET")
        return self._reset_signed_pv
    
    @property
    def limit_switch_a_pv(self) -> PV:
        if not self._limit_switch_a_pv:
            self._limit_switch_a_pv = PV(self.pvPrefix + "STAT_LIMA")
        return self._limit_switch_a_pv
    
    @property
    def limit_switch_b_pv(self) -> PV:
        if not self._limit_switch_b_pv:
            self._limit_switch_b_pv = PV(self.pvPrefix + "STAT_LIMB")
        return self._limit_switch_b_pv
    
    def restoreDefaults(self):
        caput(self.max_steps_pv.pvname, utils.DEFAULT_STEPPER_MAX_STEPS)
        caput(self.speed_pv.pvname, utils.DEFAULT_STEPPER_SPEED)
    
    def move(self, numSteps: int, maxSteps: int = utils.DEFAULT_STEPPER_MAX_STEPS,
             speed: int = utils.DEFAULT_STEPPER_SPEED, changeLimits: bool = True):
        """
        :param numSteps: positive for increasing cavity length, negative for decreasing
        :param maxSteps: the maximum number of steps allowed at once
        :param speed: the speed of the motor in steps/second
        :param changeLimits: whether or not to change the speed and steps
        :return:
        """
        
        self.check_abort()
        
        if changeLimits:
            # on the off chance that someone tries to write a negative maximum
            caput(self.max_steps_pv.pvname, abs(maxSteps))
            
            # make sure that we don't exceed the speed limit as defined by the tuner experts
            caput(self.speed_pv.pvname,
                  speed if speed < utils.MAX_STEPPER_SPEED
                  else utils.MAX_STEPPER_SPEED)
        
        if abs(numSteps) <= maxSteps:
            print(f"{self.cavity} {numSteps} steps <= {maxSteps} max")
            self.step_des_pv.put(abs(numSteps))
            self.issueMoveCommand(numSteps)
            self.restoreDefaults()
        else:
            print(f"{self.cavity} {numSteps} steps > {maxSteps} max")
            self.step_des_pv.put(maxSteps)
            self.issueMoveCommand(numSteps)
            print(f"{self.cavity} moving {numSteps - (sign(numSteps) * maxSteps)}")
            self.move(numSteps - (sign(numSteps) * maxSteps), maxSteps, speed,
                      False)
    
    def issueMoveCommand(self, numSteps):
        
        # this is necessary because the tuners for the HLs move the other direction
        if self.cavity.cryomodule.isHarmonicLinearizer:
            numSteps *= -1
        
        if sign(numSteps) == 1:
            self.move_pos_pv.put(1)
        else:
            self.move_neg_pv.put(1)
        
        print(f"Waiting 5s for {self.cavity} motor to start moving")
        sleep(5)
        
        while self.motor_moving_pv.get() == 1:
            self.check_abort()
            print(f"{self.cavity} motor still moving, waiting 5s", datetime.now())
            sleep(5)
        
        print(f"{self.cavity} motor done moving")
        
        # the motor can be done moving for good OR bad reasons
        if (caget(self.limit_switch_a_pv.pvname) == utils.STEPPER_ON_LIMIT_SWITCH_VALUE
                or caget(self.limit_switch_b_pv.pvname) == utils.STEPPER_ON_LIMIT_SWITCH_VALUE):
            raise utils.StepperError(f"{self.cavity} stepper motor on limit switch")
    
    def check_abort(self):
        if self.abort_flag:
            self.abort_pv.put(1)
            raise utils.StepperAbortError(
                    f"Abort requested for {self.cavity.cryomodule.name} cavity {self.cavity.number} stepper tuner")


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
        self.dc_setpoint_PV: PV = PV(self.pvPrefix + "DAC_SP")
        self.bias_voltage_PV: PV = PV(self.pvPrefix + "BIAS")
    
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
    def enable_stat_pv(self) -> PV:
        if not self._enable_stat_pv:
            self._enable_stat_pv = PV(self.pvPrefix + "ENABLESTAT")
        return self._enable_stat_pv
    
    @property
    def feedback_mode_PV(self) -> PV:
        if not self._feedback_mode_PV:
            self._feedback_mode_PV = PV(self.pvPrefix + "MODECTRL")
        return self._feedback_mode_PV
    
    @property
    def feedback_stat_pv(self) -> PV:
        if not self._feedback_stat_pv:
            self._feedback_stat_pv = PV(self.pvPrefix + "MODESTAT")
        return self._feedback_stat_pv
    
    def enable_feedback(self):
        self.enable_pv.put(utils.PIEZO_DISABLE_VALUE)
        self.dc_setpoint_PV.put(25)
        self.feedback_mode_PV.put(utils.PIEZO_MANUAL_VALUE)
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
        
        self.pushSSASlopePV: PV = PV(self.pvPrefix + "PUSH_SSA_SLOPE.PROC")
        self.saveSSASlopePV: PV = PV(self.pvPrefix + "SAVE_SSA_SLOPE.PROC")
        self.interlockResetPV: PV = PV(self.pvPrefix + "INTLK_RESET_ALL")
        
        self.drivelevelPV: PV = PV(self.pvPrefix + "SEL_ASET")
        
        self.cavityCharacterizationStartPV: PV = PV(self.pvPrefix + "PROBECALSTRT")
        self.cavityCharacterizationStatusPV: PV = PV(self.pvPrefix + "PROBECALSTS")
        
        self.currentQLoadedPV: PV = PV(self.pvPrefix + "QLOADED")
        self.measuredQLoadedPV: PV = PV(self.pvPrefix + "QLOADED_NEW")
        self.pushQLoadedPV: PV = PV(self.pvPrefix + "PUSH_QLOADED.PROC")
        self.saveQLoadedPV: PV = PV(self.pvPrefix + "SAVE_QLOADED.PROC")
        
        self.currentCavityScalePV: PV = PV(self.pvPrefix + "CAV:SCALER_SEL.B")
        self.measuredCavityScalePV: PV = PV(self.pvPrefix + "CAV:CAL_SCALEB_NEW")
        self.pushCavityScalePV: PV = PV(self.pvPrefix + "PUSH_CAV_SCALE.PROC")
        self.saveCavityScalePV: PV = PV(self.pvPrefix + "SAVE_CAV_SCALE.PROC")
        
        self.selAmplitudeDesPV: PV = PV(self.pvPrefix + "ADES")
        self.selAmplitudeActPV: PV = PV(self.pvPrefix + "AACTMEAN")
        self.ades_max_PV: PV = PV(self.pvPrefix + "ADES_MAX")
        
        self.rfModeCtrlPV: PV = PV(self.pvPrefix + "RFMODECTRL")
        self.rfModePV: PV = PV(self.pvPrefix + "RFMODE")
        
        self._rfStatePV: PV = None
        self.rfControlPV: PV = PV(self.pvPrefix + "RFCTRL")
        
        self.pulseGoButtonPV: PV = PV(self.pvPrefix + "PULSE_DIFF_SUM")
        self.pulseStatusPV = PV(self.pvPrefix + "PULSE_STATUS")
        self.pulseOnTimePV: PV = PV(self.pvPrefix + "PULSE_ONTIME")
        
        self.revWaveformPV: PV = PV(self.pvPrefix + "REV:AWF")
        self.fwdWaveformPV: PV = PV(self.pvPrefix + "FWD:AWF")
        self.cavWaveformPV: PV = PV(self.pvPrefix + "CAV:AWF")
        
        self.stepper_temp_pv: str = self.pvPrefix + "STEPTEMP"
        self.detune_best_PV: PV = PV(self.pvPrefix + "DFBEST")
        self.detune_rfs_PV: PV = PV(self.pvPrefix + "DF")
        
        self.rf_permit_pv: str = self.pvPrefix + "RFPERMIT"
        
        self._quench_latch_pv: PV = None
        self.quench_bypass_pv: str = self.pvPrefix + "QUENCH_BYP"
        
        self.cw_data_decim_pv: str = self.pvPrefix + "ACQ_DECIM_SEL.A"
        self.pulsed_data_decim_pv: str = self.pvPrefix + "ACQ_DECIM_SEL.C"
        
        self._tune_config_pv: PV = None
        self.chirp_prefix = self.pvPrefix + "CHIRP:"
        
        self._freq_start_pv: str = None
        self._freq_stop_pv: str = None
        
        self.abort_flag: bool = False
        
        self._hw_mode_pv: PV = None
        
        self.char_timestamp_pv: str = self.pvPrefix + "PROBECALTS"
        self._char_timestamp_pv_obj: PV = None
    
    def __str__(self):
        return f"{self.linac.name} CM{self.cryomodule.name} Cavity {self.number}"
    
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
    def hw_mode_pv(self) -> PV:
        if not self._hw_mode_pv:
            self._hw_mode_pv = PV(self.pvPrefix + "HWMODE")
        return self._hw_mode_pv
    
    @property
    def quench_latch_pv(self) -> PV:
        if not self._quench_latch_pv:
            self._quench_latch_pv = PV(self.pvPrefix + "QUENCH_LTCH")
        return self._quench_latch_pv
    
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
    def rfStatePV(self) -> PV:
        if not self._rfStatePV:
            self._rfStatePV = PV(self.pvPrefix + "RFSTATE")
        return self._rfStatePV
    
    def move_to_resonance(self):
        self.auto_tune(des_detune=0,
                       config_val=utils.TUNE_CONFIG_RESONANCE_VALUE,
                       tolerance=(200 if self.cryomodule.isHarmonicLinearizer else 50))
    
    def auto_tune(self, des_detune, config_val, tolerance=50, chirp_range=50000):
        self.setup_tuning(chirp_range)
        
        if self.detune_best_PV.severity == 3:
            raise utils.DetuneError(f"Detune for {self} is invalid")
        
        delta = self.detune_best_PV.get() - des_detune
        
        self.tune_config_pv.put(utils.TUNE_CONFIG_OTHER_VALUE)
        
        expected_steps: int = abs(int(delta * self.steps_per_hz))
        steps_moved: int = 0
        
        while abs(delta) > tolerance:
            self.check_abort()
            est_steps = int(0.9 * delta * self.steps_per_hz)
            
            print(f"Moving stepper for {self} {est_steps} steps")
            
            self.steppertuner.move(est_steps,
                                   maxSteps=abs(est_steps) * 1.1,
                                   speed=utils.MAX_STEPPER_SPEED)
            steps_moved += abs(est_steps)
            
            if steps_moved > expected_steps * 1.5:
                raise utils.DetuneError(f"{self} motor moved more steps than expected")
            
            # this should catch if the chirp range is wrong or if the cavity is off
            if self.detune_best_PV.severity == EPICS_INVALID_VAL:
                self.find_chirp_range()
            
            delta = self.detune_best_PV.get() - des_detune
        
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
        if self.pulseOnTimePV.get() != utils.NOMINAL_PULSED_ONTIME:
            print("Setting RF Pulse On Time to {ontime} ms".format(ontime=utils.NOMINAL_PULSED_ONTIME))
            self.pulseOnTimePV.put(utils.NOMINAL_PULSED_ONTIME)
            self.pushGoButton()
    
    def pushGoButton(self):
        """
        Many of the changes made to a cavity don't actually take effect until the
        go button is pressed
        :return:
        """
        self.pulseGoButtonPV.put(1)
        while self.pulseStatusPV.get() < 2:
            print("waiting for pulse state", datetime.now())
            sleep(1)
        if self.pulseStatusPV.get() > 2:
            raise utils.PulseError("Unable to pulse cavity")
    
    def turnOn(self):
        if self.hw_mode_pv.get() == utils.HW_MODE_ONLINE_VALUE:
            self.ssa.turnOn()
            self.setPowerState(True)
        else:
            raise utils.CavityHWModeError(f"{self} not online")
    
    def turnOff(self):
        self.setPowerState(False)
    
    def setPowerState(self, turnOn: bool, wait_time=1):
        """
        Turn the cavity on or off
        :param wait_time:
        :param turnOn:
        :return:
        """
        desiredState = (1 if turnOn else 0)
        
        print(f"\nSetting RF State for {self}")
        caput(self.rfControlPV.pvname, desiredState)
        
        while caget(self.rfStatePV.pvname) != desiredState:
            self.check_abort()
            print(f"Waiting {wait_time} seconds for {self} RF state to change")
            sleep(wait_time)
        
        print(f"RF state set for {self}")
    
    def setup_SELAP(self, desAmp: float = 5):
        self.setup_rf(desAmp)
        
        caput(self.rfModeCtrlPV.pvname, utils.RF_MODE_SELAP)
        print(f"{self} set up in SELAP")
    
    def setup_SELA(self, desAmp: float = 5):
        self.setup_rf(desAmp)
        
        caput(self.rfModeCtrlPV.pvname, utils.RF_MODE_SELA)
        print(f"{self} set up in SELA")
    
    def check_abort(self):
        if self.abort_flag:
            self.abort_flag = False
            self.turnOff()
            raise utils.CavityAbortError(f"Abort requested for {self}")
    
    def setup_rf(self, desAmp):
        if desAmp > caget(self.ades_max_PV.pvname):
            print(f"Requested amplitude for {self} too high - ramping up to AMAX instead")
            desAmp = caget(self.ades_max_PV.pvname)
        print(f"setting up {self}")
        self.turnOff()
        self.ssa.calibrate(self.ssa.drivemax)
        self.move_to_resonance()
        
        self.characterize()
        self.calc_probe_q_pv.put(1)
        
        self.check_abort()
        
        self.reset_data_decimation()
        
        self.check_abort()
        
        caput(self.selAmplitudeDesPV.pvname, min(5, desAmp))
        caput(self.rfModeCtrlPV.pvname, utils.RF_MODE_SEL)
        caput(self.piezo.feedback_mode_PV.pvname, utils.PIEZO_FEEDBACK_VALUE)
        caput(self.rfModeCtrlPV.pvname, utils.RF_MODE_SELA)
        
        self.check_abort()
        
        if desAmp <= 10:
            self.walk_amp(desAmp, 0.5)
        
        else:
            self.walk_amp(10, 0.5)
            self.walk_amp(desAmp, 0.1)
    
    def reset_data_decimation(self):
        print(f"Setting data decimation PVs for {self}")
        caput(self.cw_data_decim_pv, 255)
        caput(self.pulsed_data_decim_pv, 255)
    
    def setup_tuning(self, chirp_range=200000):
        print(f"enabling {self} piezo")
        while self.piezo.enable_stat_pv.get() != utils.PIEZO_ENABLE_VALUE:
            print(f"{self} piezo not enabled, retrying")
            self.piezo.enable_pv.put(utils.PIEZO_DISABLE_VALUE)
            sleep(2)
            self.piezo.enable_pv.put(utils.PIEZO_ENABLE_VALUE)
            sleep(2)
        
        print(f"setting {self} piezo to manual")
        while self.piezo.feedback_stat_pv.get() != utils.PIEZO_MANUAL_VALUE:
            print(f"{self} piezo not in manual, retrying")
            self.piezo.feedback_mode_PV.put(utils.PIEZO_FEEDBACK_VALUE)
            sleep(2)
            self.piezo.feedback_mode_PV.put(utils.PIEZO_MANUAL_VALUE)
            sleep(2)
        
        print(f"setting {self} piezo DC voltage offset to 0V")
        self.piezo.dc_setpoint_PV.put(0)
        
        print(f"setting {self} piezo bias voltage to 25V")
        self.piezo.bias_voltage_PV.put(25)
        
        print(f"setting {self} drive level to {utils.SAFE_PULSED_DRIVE_LEVEL}")
        self.drivelevelPV.put(utils.SAFE_PULSED_DRIVE_LEVEL)
        
        print(f"setting {self} RF to chirp")
        self.rfModeCtrlPV.put(utils.RF_MODE_CHIRP)
        
        print(f"turning {self} RF on and waiting 5s for detune to catch up")
        self.ssa.turnOn()
        
        self.reset_interlocks()
        
        self.turnOn()
        sleep(5)
        
        self.find_chirp_range(chirp_range)
    
    def find_chirp_range(self, chirp_range=50000):
        self.set_chirp_range(chirp_range)
        sleep(1)
        if self.detune_best_PV.severity == EPICS_INVALID_VAL:
            if chirp_range < 500000:
                self.find_chirp_range(int(chirp_range * 1.25))
            else:
                raise utils.DetuneError(f"{self}: No valid detune found within"
                                        f"+/-500000Hz chirp range")
    
    def reset_interlocks(self, retry=True, wait=True):
        print(f"Resetting interlocks for {self} and waiting 3s")
        self.interlockResetPV.put(1)
        if wait:
            sleep(3)
        
        if retry:
            count = 0
            wait = 5
            while caget(self.rf_permit_pv) == 0 and count < 3:
                print(f"{self} reset unsuccessful, retrying and waiting {wait} seconds")
                self.interlockResetPV.put(1)
                sleep(wait)
                count += 1
                wait += 2
            if caget(self.rf_permit_pv) == 0:
                raise utils.CavityFaultError(f"{self} still faulted after 3 reset attempts")
    
    @property
    def characterization_timestamp(self) -> datetime:
        if not self._char_timestamp_pv_obj:
            self._char_timestamp_pv_obj = PV(self.char_timestamp_pv)
        date_string = self._char_timestamp_pv_obj.get(use_caget=False)
        time_readback = datetime.strptime(date_string, '%Y-%m-%d-%H:%M:%S')
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
        self.drivelevelPV.put(utils.SAFE_PULSED_DRIVE_LEVEL)
        
        if (datetime.now() - self.characterization_timestamp).total_seconds() < 60:
            if self.cavityCharacterizationStatusPV.get() == 1:
                print(f"{self} successful characterization within the last minute,"
                      f" not starting a new one")
                self.finish_characterization()
                return
        
        print(f"Starting {self} cavity characterization at {datetime.now()}")
        self.cavityCharacterizationStartPV.put(1, retry=False)
        sleep(2)
        
        while (self.cavityCharacterizationStatusPV.get()
               == utils.CALIBRATION_RUNNING_VALUE):
            print(f"waiting for {self.cavityCharacterizationStatusPV.pvname}"
                  f" to stop running", datetime.now())
            sleep(1)
            
        if self.cavityCharacterizationStatusPV.get() == utils.CALIBRATION_COMPLETE_VALUE:
            if (datetime.now() - self.characterization_timestamp).total_seconds() > 60:
                raise utils.CavityQLoadedCalibrationError(f"{self} characterization did not start")
            self.finish_characterization()
        
        else:
            raise utils.CavityQLoadedCalibrationError(f"{self} characterization crashed")
    
    def finish_characterization(self):
        print(f"pushing {self} characterization results")
        if (self.loaded_q_lower_limit < self.measuredQLoadedPV.get()
                < self.loaded_q_upper_limit):
            self.pushQLoadedPV.put(1)
        else:
            raise utils.CavityQLoadedCalibrationError(f"{self} loaded Q out of tolerance")
        if (utils.CAVITY_SCALE_LOWER_LIMIT < self.measuredCavityScalePV.get()
                < utils.CAVITY_SCALE_UPPER_LIMIT):
            self.pushCavityScalePV.put(1)
        else:
            raise utils.CavityScaleFactorCalibrationError(f"{self} scale factor out of tolerance")
        
        self.reset_data_decimation()
        print(f"restoring {self} piezo feedback setpoint to 0")
        self.piezo.feedback_setpoint_pv.put(0)
        print(f"{self} characterization successful")
    
    def walk_amp(self, des_amp, step_size):
        print(f"walking {self} to {des_amp} from {self.selAmplitudeDesPV.get()}")
        
        while self.selAmplitudeDesPV.get() <= (des_amp - step_size):
            self.check_abort()
            self.selAmplitudeDesPV.put(self.selAmplitudeDesPV.get() + step_size)
            # to avoid tripping sensitive interlock
            sleep(0.1)
        
        while not isclose(self.selAmplitudeDesPV.get(), des_amp):
            print(f"{self} ADES not at {des_amp}, retrying")
            self.selAmplitudeDesPV.put(des_amp, use_caput=True)
            sleep(0.5)
        
        print(f"{self} at {des_amp} MV")


class Magnet:
    def __init__(self, magnettype, cryomodule):
        # type: (str, Cryomodule) -> None
        self.pvprefix = "{magnettype}:{linac}:{cm}85:".format(magnettype=magnettype,
                                                              linac=cryomodule.linac.name,
                                                              cm=cryomodule.name)
        self.name = magnettype
        self.cryomodule: Cryomodule = cryomodule
        self.bdesPV: PV = PV(self.pvprefix + 'BDES')
        self.controlPV: PV = PV(self.pvprefix + 'CTRL')
        self.interlockPV: PV = PV(self.pvprefix + 'INTLKSUMY')
        self.ps_statusPV: PV = PV(self.pvprefix + 'STATE')
        self.bactPV: PV = PV(self.pvprefix + 'BACT')
        self.iactPV: PV = PV(self.pvprefix + 'IACT')
        # changing IDES immediately perturbs
        self.idesPV: PV = PV(self.pvprefix + 'IDES')
    
    @property
    def bdes(self):
        return self.bdesPV.get()
    
    @bdes.setter
    def bdes(self, value):
        self.bdesPV.put(value)
        self.controlPV.put(utils.MAGNET_TRIM_VALUE)
    
    def reset(self):
        self.controlPV.put(utils.MAGNET_RESET_VALUE)
    
    def turnOn(self):
        self.controlPV.put(utils.MAGNET_ON_VALUE)
    
    def turnOff(self):
        self.controlPV.put(utils.MAGNET_OFF_VALUE)
    
    def degauss(self):
        self.controlPV.put(utils.MAGNET_DEGAUSS_VALUE)
    
    def trim(self):
        self.controlPV.put(utils.MAGNET_TRIM_VALUE)


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
