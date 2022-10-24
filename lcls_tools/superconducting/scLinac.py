################################################################################
# Utility classes for superconducting linac
# NOTE: For some reason, using python 3 style type annotations causes circular
#       import issues, so leaving as python 2 style for now
################################################################################
from datetime import datetime
from time import sleep
from typing import Dict, List, Type

from epics import PV, caget, caput
from numpy import sign

import lcls_tools.superconducting.scLinacUtils as utils
from lcls_tools.common.pyepics_tools.pyepicsUtils import EPICS_INVALID_VAL

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
        
        self.statusPV: str = (self.pvPrefix + "StatusMsg")
        self.turnOnPV: PV = PV(self.pvPrefix + "PowerOn")
        self.turnOffPV: PV = PV(self.pvPrefix + "PowerOff")
        self.resetPV: str = self.pvPrefix + "FaultReset"
        
        self.calibrationStartPV: PV = PV(self.pvPrefix + "CALSTRT")
        self.calibrationStatusPV: PV = PV(self.pvPrefix + "CALSTS")
        self.calResultStatusPV: PV = PV(self.pvPrefix + "CALSTAT")
        
        self.currentSlopePV: PV = PV(self.pvPrefix + "SLOPE")
        self.measuredSlopePV: PV = PV(self.pvPrefix + "SLOPE_NEW")
        
        self.maxdrive_setpoint_pv: str = self.pvPrefix + "DRV_MAX_REQ"
        self.saved_maxdrive_pv: str = self.pvPrefix + "DRV_MAX_SAVE"
    
    @property
    def drivemax(self):
        saved_val = caget(self.saved_maxdrive_pv)
        return (1 if self.cavity.cryomodule.isHarmonicLinearizer
                else (saved_val if saved_val else 0.8))
    
    def calibrate(self, drivemax):
        print(f"Trying {self.cavity} SSA calibration with drivemax {drivemax}")
        if drivemax < 0.5:
            raise utils.SSACalibrationError(f"Requested {self.cavity} SSA drive max too low")
        
        while caput(self.maxdrive_setpoint_pv, drivemax, wait=True) != 1:
            print("Setting max drive")
        
        try:
            if self.cavity.abort_flag:
                raise utils.CavityAbortError(f"Abort requested for {self.cavity}")
            self.runCalibration()
        
        except utils.SSACalibrationError as e:
            print(f"{self.cavity} SSA Calibration failed, retrying")
            self.calibrate(drivemax - 0.02)
    
    def turnOn(self):
        self.setPowerState(True)
    
    def turnOff(self):
        self.setPowerState(False)
    
    def reset(self):
        print(f"Resetting {self.cavity} SSA...")
        caput(self.resetPV, 1, wait=True)
        while caget(self.statusPV) == utils.SSA_STATUS_RESETTING_FAULTS_VALUE:
            sleep(1)
        if caget(self.statusPV) in [utils.SSA_STATUS_FAULTED_VALUE,
                                    utils.SSA_STATUS_FAULT_RESET_FAILED_VALUE]:
            raise utils.SSAFaultError(f"Unable to reset {self.cavity} SSA")
    
    def setPowerState(self, turnOn: bool):
        print(f"Setting {self.cavity} SSA power...")
        
        if turnOn:
            if caget(self.statusPV) != utils.SSA_STATUS_ON_VALUE:
                while caput(self.turnOnPV.pvname, 1, wait=True) != 1:
                    self.cavity.check_abort()
                    print(f"Trying to power on {self.cavity} SSA")
                while caget(self.statusPV) != utils.SSA_STATUS_ON_VALUE:
                    self.cavity.check_abort()
                    print(f"waiting for {self.cavity} SSA to turn on")
                    sleep(1)
        else:
            if caget(self.statusPV) == utils.SSA_STATUS_ON_VALUE:
                while caput(self.turnOffPV.pvname, 1, wait=True) != 1:
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
        utils.runCalibration(startPV=self.calibrationStartPV,
                             statusPV=self.calibrationStatusPV,
                             exception=utils.SSACalibrationError,
                             resultStatusPV=self.calResultStatusPV)
        
        print(f"Pushing SSA calibration results for {self.cavity}")
        utils.pushAndSaveCalibrationChange(measuredPV=self.measuredSlopePV,
                                           currentPV=self.currentSlopePV,
                                           lowerLimit=utils.SSA_SLOPE_LOWER_LIMIT,
                                           upperLimit=utils.SSA_SLOPE_UPPER_LIMIT,
                                           pushPV=self.cavity.pushSSASlopePV,
                                           savePV=self.cavity.saveSSASlopePV,
                                           exception=utils.SSACalibrationError)


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
            self._reset_signed_pv.connect()
        return self._reset_signed_pv
    
    @property
    def limit_switch_a_pv(self) -> PV:
        if not self._limit_switch_a_pv:
            self._limit_switch_a_pv = PV(self.pvPrefix + "STAT_LIMA")
            self._limit_switch_a_pv.connect()
        return self._limit_switch_a_pv
    
    @property
    def limit_switch_b_pv(self) -> PV:
        if not self._limit_switch_b_pv:
            self._limit_switch_b_pv = PV(self.pvPrefix + "STAT_LIMB")
            self._limit_switch_b_pv.connect()
        return self._limit_switch_b_pv
    
    def restoreDefaults(self):
        caput(self.max_steps_pv.pvname, utils.DEFAULT_STEPPER_MAX_STEPS, wait=True)
        caput(self.speed_pv.pvname, utils.DEFAULT_STEPPER_SPEED, wait=True)
    
    def move(self, numSteps: int, maxSteps: int = utils.DEFAULT_STEPPER_MAX_STEPS,
             speed: int = utils.DEFAULT_STEPPER_SPEED, changeLimits: bool = True):
        """
        :param numSteps: positive for increasing cavity length, negative for decreasing
        :param maxSteps: the maximum number of steps allowed at once
        :param speed: the speed of the motor in steps/second
        :param changeLimits: whether or not to change the speed and steps
        :return:
        """
        
        if (self.limit_switch_a_pv.value == utils.STEPPER_ON_LIMIT_SWITCH_VALUE
                or self.limit_switch_b_pv.value == utils.STEPPER_ON_LIMIT_SWITCH_VALUE):
            raise utils.StepperError("Stepper motor on limit switch")
        
        if changeLimits:
            # on the off chance that someone tries to write a negative maximum
            caput(self.max_steps_pv.pvname, abs(maxSteps), wait=True)
            
            # make sure that we don't exceed the speed limit as defined by the tuner experts
            caput(self.speed_pv.pvname,
                  speed if speed < utils.MAX_STEPPER_SPEED
                  else utils.MAX_STEPPER_SPEED, wait=True)
        
        if abs(numSteps) <= maxSteps:
            caput(self.step_des_pv.pvname, abs(numSteps), wait=True)
            self.issueMoveCommand(numSteps)
            self.restoreDefaults()
        else:
            caput(self.step_des_pv.pvname, maxSteps, wait=True)
            self.issueMoveCommand(numSteps)
            
            self.move(numSteps - (sign(numSteps) * maxSteps), maxSteps, speed,
                      False)
    
    def issueMoveCommand(self, numSteps):
        
        # this is necessary because the tuners for the HLs move the other direction
        if self.cavity.cryomodule.isHarmonicLinearizer:
            numSteps *= -1
        
        if sign(numSteps) == 1:
            caput(self.move_pos_pv.pvname, 1, wait=True)
        else:
            caput(self.move_neg_pv.pvname, 1, wait=True)
        
        print("Waiting 5s for the motor to start moving")
        sleep(5)
        
        while self.motor_moving_pv.value == 1:
            if self.abort_flag:
                self.abort_pv.put(1)
                raise utils.StepperAbortError(
                        f"Abort requested for {self.cavity.cryomodule.name} cavity {self.cavity.number} stepper tuner")
            
            print("Motor moving", datetime.now())
            sleep(1)
            if (abs(self.cavity.detune_best_PV.value) > 150000
                    and self.cavity.freq_stop_pv.value != 400000):
                self.cavity.set_chirp_range(400000)
        
        if self.motor_done_pv.value != 1:
            raise utils.StepperError(f"Motor for not in expected state for {self}")
        
        print("Motor done")


class Piezo:
    def __init__(self, cavity):
        # type (Cavity) -> None
        self.cavity: Cavity = cavity
        self.pvPrefix: str = self.cavity.pvPrefix + "PZT:"
        self.enable_PV: PV = PV(self.pvPrefix + "ENABLE")
        self.feedback_mode_PV: PV = PV(self.pvPrefix + "MODECTRL")
        self.dc_setpoint_PV: PV = PV(self.pvPrefix + "DAC_SP")
        self.bias_voltage_PV: PV = PV(self.pvPrefix + "BIAS")
    
    def enable_feedback(self):
        self.enable_PV.put(utils.PIEZO_DISABLE_VALUE)
        self.dc_setpoint_PV.put(25)
        self.feedback_mode_PV.put(utils.PIEZO_MANUAL_VALUE)
        self.enable_PV.put(utils.PIEZO_ENABLE_VALUE)


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
        
        self.number = cavityNum
        self.rack: Rack = rackObject
        self.cryomodule: Cryomodule = self.rack.cryomodule
        self.linac = self.cryomodule.linac
        
        if self.cryomodule.isHarmonicLinearizer:
            self.length = 0.346
            self.frequency = 3.9e9
            self.loaded_q_lower_limit = utils.LOADED_Q_LOWER_LIMIT_HL
            self.loaded_q_upper_limit = utils.LOADED_Q_UPPER_LIMIT_HL
        else:
            self.length = 1.038
            self.frequency = 1.3e9
            self.loaded_q_lower_limit = utils.LOADED_Q_LOWER_LIMIT
            self.loaded_q_upper_limit = utils.LOADED_Q_UPPER_LIMIT
        
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
        
        self.cavityCalibrationStartPV: PV = PV(self.pvPrefix + "PROBECALSTRT")
        self.cavityCalibrationStatusPV: PV = PV(self.pvPrefix + "PROBECALSTS")
        
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
            self._freq_start_pv.connect()
        return self._freq_start_pv
    
    @property
    def freq_stop_pv(self) -> PV:
        if not self._freq_stop_pv:
            self._freq_stop_pv = PV(self.chirp_prefix + "FREQ_STOP")
            self._freq_stop_pv.connect()
        return self._freq_stop_pv
    
    def set_chirp_range(self, offset: int):
        offset = abs(offset)
        print(f"Setting chirp range for {self} to +/- {offset} Hz")
        self.freq_start_pv.put(-offset, wait=True)
        self.freq_stop_pv.put(offset, wait=True)
        print(f"Chirp range set for {self}")
    
    @property
    def rfStatePV(self) -> PV:
        if not self._rfStatePV:
            self._rfStatePV = PV(self.pvPrefix + "RFSTATE")
        return self._rfStatePV
    
    def move_to_resonance(self):
        self.auto_tune(des_detune=0,
                       config_val=utils.TUNE_CONFIG_RESONANCE_VALUE)
    
    def auto_tune(self, des_detune, config_val):
        self.setup_tuning()
        
        cm_name = self.cryomodule.name
        cav_num = self.number
        
        delta = self.detune_best_PV.value - des_detune
        steps_per_hz = (utils.ESTIMATED_MICROSTEPS_PER_HZ_HL
                        if self.cryomodule.isHarmonicLinearizer
                        else utils.ESTIMATED_MICROSTEPS_PER_HZ)
        
        if self.detune_best_PV.severity == 3:
            raise utils.DetuneError(f"Detune for {self} is invalid")
        
        while abs(delta) > 50:
            if self.quench_latch_pv.value == 1:
                raise utils.QuenchError(f"{self} quenched, aborting autotune")
            est_steps = int(0.9 * delta * steps_per_hz)
            
            print(f"Moving stepper for {self} {est_steps} steps")
            
            self.tune_config_pv.put(utils.TUNE_CONFIG_OTHER_VALUE)
            
            self.steppertuner.move(est_steps,
                                   maxSteps=10000000,
                                   speed=utils.MAX_STEPPER_SPEED)
            try:
                delta = caget(self.detune_best_PV.pvname) - des_detune
            except TypeError as e:
                raise utils.StepperError(str(e))
        
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
        if self.pulseOnTimePV.value != utils.NOMINAL_PULSED_ONTIME:
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
        while self.pulseStatusPV.value < 2:
            print("waiting for pulse state", datetime.now())
            sleep(1)
        if self.pulseStatusPV.value > 2:
            raise utils.PulseError("Unable to pulse cavity")
    
    def turnOn(self):
        self.setPowerState(True)
    
    def turnOff(self):
        self.setPowerState(False)
    
    def setPowerState(self, turnOn: bool):
        """
        Turn the cavity on or off
        :param turnOn:
        :return:
        """
        desiredState = (1 if turnOn else 0)
        
        print(f"\nSetting RF State for {self}")
        caput(self.rfControlPV.pvname, desiredState, wait=True)
        
        wait = 1
        
        while self.rfStatePV.value != desiredState:
            self.check_abort()
            print(f"Waiting {wait} seconds for {self} RF state to change")
            sleep(wait)
            wait += 2
        
        print(f"RF state set for {self}")
    
    def setup_SELAP(self, desAmp: float = 5):
        self.setup_rf(desAmp)
        
        caput(self.rfModeCtrlPV.pvname, utils.RF_MODE_SELAP, wait=True)
        print(f"{self} set up in SELAP")
    
    def setup_SELA(self, desAmp: float = 5):
        self.setup_rf(desAmp)
        
        caput(self.rfModeCtrlPV.pvname, utils.RF_MODE_SELA, wait=True)
        print(f"{self} set up in SELA")
    
    def check_abort(self):
        if self.abort_flag:
            self.abort_flag = False
            self.turnOff()
            self.ssa.turnOff()
            raise utils.CavityAbortError(f"Abort requested for {self}")
    
    def setup_rf(self, desAmp):
        if desAmp > caget(self.ades_max_PV.pvname):
            print(f"Requested amplitude for {self} too high - ramping up to AMAX instead")
            desAmp = caget(self.ades_max_PV.pvname)
        print(f"setting up {self}")
        self.turnOff()
        self.ssa.calibrate(self.ssa.drivemax)
        self.move_to_resonance()
        
        caput(self.quench_bypass_pv, 1, wait=True)
        self.runCalibration()
        caput(self.quench_bypass_pv, 0, wait=True)
        
        self.check_abort()
        
        print(f"Setting data decimation PVs for {self}")
        caput(self.cw_data_decim_pv, 255, wait=True)
        caput(self.pulsed_data_decim_pv, 255, wait=True)
        
        self.check_abort()
        
        caput(self.selAmplitudeDesPV.pvname, min(5, desAmp), wait=True)
        caput(self.rfModeCtrlPV.pvname, utils.RF_MODE_SEL, wait=True)
        caput(self.piezo.feedback_mode_PV.pvname, utils.PIEZO_FEEDBACK_VALUE, wait=True)
        caput(self.rfModeCtrlPV.pvname, utils.RF_MODE_SELA, wait=True)
        
        self.check_abort()
        
        if desAmp <= 10:
            self.walk_amp(desAmp, 0.5)
        
        else:
            self.walk_amp(10, 0.5)
            self.walk_amp(desAmp, 0.1)
    
    def setup_tuning(self):
        # self.turnOff()
        print(f"enabling {self} piezo")
        self.piezo.enable_PV.put(utils.PIEZO_ENABLE_VALUE)
        
        print(f"setting {self} piezo to manual")
        self.piezo.feedback_mode_PV.put(utils.PIEZO_MANUAL_VALUE)
        
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
        
        if self.detune_best_PV.severity == EPICS_INVALID_VAL:
            raise utils.DetuneError(f"{self} Detune PV invalid. Either expand the chirp"
                                    " range or use the rack large frequency scan"
                                    " to find the detune.")
    
    def reset_interlocks(self, retry=True, wait=True):
        print(f"Resetting interlocks for {self} and waiting 3s")
        self.interlockResetPV.put(1, wait=True)
        if wait:
            sleep(3)
        
        if retry:
            count = 0
            wait = 5
            while caget(self.rf_permit_pv) == 0 and count < 3 and self.quench_latch_pv.value != 0:
                print(f"{self} reset unsuccessful, retrying and waiting {wait} seconds")
                self.interlockResetPV.put(1, wait=True)
                sleep(wait)
                count += 1
                wait += 2
            if caget(self.rf_permit_pv) == 0:
                raise utils.CavityFaultError(f"{self} still faulted after 3 reset attempts")
    
    def runCalibration(self):
        """
        Calibrates the cavity's RF probe so that the amplitude readback will be
        accurate. Also measures the loaded Q (quality factor) of the cavity power
        coupler
        :return:
        """
        
        self.reset_interlocks()
        
        print(f"setting {self} drive to {utils.SAFE_PULSED_DRIVE_LEVEL}")
        self.drivelevelPV.put(utils.SAFE_PULSED_DRIVE_LEVEL)
        
        print(f"running {self} calibration")
        utils.runCalibration(startPV=self.cavityCalibrationStartPV,
                             statusPV=self.cavityCalibrationStatusPV,
                             exception=utils.CavityQLoadedCalibrationError)
        
        print(f"pushing {self} calibration results")
        utils.pushAndSaveCalibrationChange(measuredPV=self.measuredQLoadedPV,
                                           currentPV=self.currentQLoadedPV,
                                           lowerLimit=self.loaded_q_lower_limit,
                                           upperLimit=self.loaded_q_upper_limit,
                                           pushPV=self.pushQLoadedPV,
                                           savePV=self.saveQLoadedPV,
                                           exception=utils.CavityQLoadedCalibrationError)
        
        utils.pushAndSaveCalibrationChange(measuredPV=self.measuredCavityScalePV,
                                           currentPV=self.currentCavityScalePV,
                                           lowerLimit=utils.CAVITY_SCALE_LOWER_LIMIT,
                                           upperLimit=utils.CAVITY_SCALE_UPPER_LIMIT,
                                           pushPV=self.pushCavityScalePV,
                                           savePV=self.saveCavityScalePV,
                                           exception=utils.CavityScaleFactorCalibrationError)
        
        print(f"{self} calibration successful")
    
    def walk_amp(self, des_amp, step_size):
        print(f"walking {self} to {des_amp}")
        
        while caget(self.selAmplitudeDesPV.pvname) <= (des_amp - step_size):
            self.check_abort()
            if (self.quench_latch_pv.value) == 1:
                raise utils.QuenchError(f"{self} quench detected, aborting rampup")
            caput(self.selAmplitudeDesPV.pvname,
                  self.selAmplitudeDesPV.value + step_size, wait=True)
            # to avoid tripping sensitive interlock
            sleep(0.1)
        
        if caget(self.selAmplitudeDesPV.pvname) != des_amp:
            caput(self.selAmplitudeDesPV.pvname, des_amp)
        
        print(f"{self} at {des_amp}")


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
        return self.bdesPV.value
    
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
