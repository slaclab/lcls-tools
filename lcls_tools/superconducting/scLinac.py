################################################################################
# Utility classes for superconducting linac
# NOTE: For some reason, using python 3 style type annotations causes circular
#       import issues, so leaving as python 2 style for now
################################################################################
from datetime import datetime
from time import sleep
from typing import Dict, List, Type

from epics import caget, caput
from numpy import sign

import lcls_tools.superconducting.scLinacUtils as utils
from lcls_tools.common.pyepics_tools.pyepicsUtils import PV


class SSA:
    def __init__(self, cavity):
        # type: (Cavity) -> None
        self.cavity: Cavity = cavity
        self.pvPrefix = self.cavity.pvPrefix + "SSA:"
        
        self.statusPV: PV = PV(self.pvPrefix + "StatusMsg")
        self.turnOnPV: PV = PV(self.pvPrefix + "PowerOn")
        self.turnOffPV: PV = PV(self.pvPrefix + "PowerOff")
        
        self.calibrationStartPV: PV = PV(self.pvPrefix + "CALSTRT")
        self.calibrationStatusPV: PV = PV(self.pvPrefix + "CALSTS")
        self.calResultStatusPV: PV = PV(self.pvPrefix + "CALSTAT")
        
        self.currentSlopePV: PV = PV(self.pvPrefix + "SLOPE")
        self.measuredSlopePV: PV = PV(self.pvPrefix + "SLOPE_NEW")
    
    def turnOn(self):
        self.setPowerState(True)
    
    def turnOff(self):
        self.setPowerState(False)
    
    def setPowerState(self, turnOn: bool):
        print("\nSetting SSA power...")
        
        if turnOn:
            if self.statusPV.value != utils.SSA_STATUS_ON_VALUE:
                while caput(self.turnOnPV.pvname, 1, wait=True) != 1:
                    print("Trying to power on SSA")
                while caget(self.statusPV.pvname) != utils.SSA_STATUS_ON_VALUE:
                    print("waiting for SSA to turn on")
                    sleep(1)
        else:
            if self.statusPV.value == utils.SSA_STATUS_ON_VALUE:
                while caput(self.turnOffPV.pvname, 1, wait=True) != 1:
                    print("Trying to power off SSA")
                while caget(self.statusPV.pvname) == utils.SSA_STATUS_ON_VALUE:
                    print("waiting for SSA to turn off")
                    sleep(1)
        
        print("SSA power set\n")
    
    def runCalibration(self):
        """
        Runs the SSA through its range and finds the slope that describes
        the relationship between SSA drive signal and output power
        :return:
        """
        self.setPowerState(True)
        
        self.cavity.reset_interlocks()
        
        print(f"Running SSA Calibration for CM{self.cavity.cryomodule.name}"
              f" cavity {self.cavity.number}")
        utils.runCalibration(startPV=self.calibrationStartPV,
                             statusPV=self.calibrationStatusPV,
                             exception=utils.SSACalibrationError,
                             resultStatusPV=self.calResultStatusPV)
        
        print(f"Pushing SSA calibration results for CM{self.cavity.cryomodule.name}"
              f" cavity {self.cavity.number}")
        utils.pushAndSaveCalibrationChange(measuredPV=self.measuredSlopePV,
                                           currentPV=self.currentSlopePV,
                                           lowerLimit=utils.SSA_SLOPE_LOWER_LIMIT,
                                           upperLimit=utils.SSA_SLOPE_UPPER_LIMIT,
                                           pushPV=self.cavity.pushSSASlopePV,
                                           savePV=self.cavity.saveSSASlopePV,
                                           exception=utils.SSACalibrationError)


class Heater:
    def __init__(self, cavity):
        # type: (Cavity) -> None
        self.cavity = cavity
        self.pvPrefix = "CHTR:CM{cm}:1{cav}55:HV:".format(cm=self.cavity.cryomodule.name,
                                                          cav=self.cavity.number)
        self.powerDesPV = PV(self.pvPrefix + "POWER_SETPT")
        self.powerActPV = PV(self.pvPrefix + "POWER")


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
        self.reset_signed_pv: PV = PV(self.pvPrefix + "TOTSGN_RESET")
        self.steps_cold_landing_pv: PV = PV(self.pvPrefix + "NSTEPS_COLD")
        self.push_signed_cold_pv: PV = PV(self.pvPrefix + "PUSH_NSTEPS_COLD.PROC")
        self.push_signed_park_pv: PV = PV(self.pvPrefix + "PUSH_NSTEPS_PARK.PROC")
        self.motor_moving_pv: PV = PV(self.pvPrefix + "STAT_MOV")
        self.motor_done_pv: PV = PV(self.pvPrefix + "STAT_DONE")
    
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
        
        while caget(self.motor_moving_pv.pvname) == 1:
            print("Motor moving", datetime.now())
            sleep(1)
        
        if caget(self.motor_done_pv.pvname) != 1:
            raise utils.StepperError("Motor not in expected state")
        
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
        else:
            self.length = 1.038
            self.frequency = 1.3e9
        
        self.pvPrefix = "ACCL:{LINAC}:{CRYOMODULE}{CAVITY}0:".format(LINAC=self.linac.name,
                                                                     CRYOMODULE=self.cryomodule.name,
                                                                     CAVITY=self.number)
        
        self.ctePrefix = "CTE:CM{cm}:1{cav}".format(cm=self.cryomodule.name,
                                                    cav=self.number)
        
        self.ssa = ssaClass(self)
        self.heater = Heater(self)
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
        
        self.rfModeCtrlPV: PV = PV(self.pvPrefix + "RFMODECTRL")
        self.rfModePV: PV = PV(self.pvPrefix + "RFMODE")
        
        self.rfStatePV: PV = PV(self.pvPrefix + "RFSTATE")
        self.rfControlPV: PV = PV(self.pvPrefix + "RFCTRL")
        
        self.pulseGoButtonPV: PV = PV(self.pvPrefix + "PULSE_DIFF_SUM")
        self.pulseStatusPV = PV(self.pvPrefix + "PULSE_STATUS")
        self.pulseOnTimePV: PV = PV(self.pvPrefix + "PULSE_ONTIME")
        
        self.revWaveformPV: PV = PV(self.pvPrefix + "REV:AWF")
        self.fwdWaveformPV: PV = PV(self.pvPrefix + "FWD:AWF")
        self.cavWaveformPV: PV = PV(self.pvPrefix + "CAV:AWF")
        
        self.stepper_temp_PV: PV = PV(self.pvPrefix + "STEPTEMP")
        self.detune_best_PV: PV = PV(self.pvPrefix + "DFBEST")
        self.detune_rfs_PV: PV = PV(self.pvPrefix + "DF")
        
        self.ades_max_PV: PV = PV(self.pvPrefix + "ADES_MAX")
        self.rf_permit_pv: str = self.pvPrefix + "RFPERMIT"
    
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
        self.pulseGoButtonPV.put(1, waitForPut=False)
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
        
        print("\nSetting RF State...")
        caput(self.rfControlPV.pvname, desiredState, wait=True)
        while caget(self.pvPrefix + "RFSTATE") != desiredState:
            print("Waiting for RF state to change")
            sleep(1)
        
        print("RF state set\n")
    
    def reset_interlocks(self):
        if caget(self.rf_permit_pv) != 1:
            print(f"Resetting interlocks for CM{self.cryomodule.name}"
                  f" cavity {self.number}")
            caput(self.interlockResetPV.pvname, 1, wait=True)
    
    def runCalibration(self, loadedQLowerlimit=utils.LOADED_Q_LOWER_LIMIT,
                       loadedQUpperlimit=utils.LOADED_Q_UPPER_LIMIT):
        """
        Calibrates the cavity's RF probe so that the amplitude readback will be
        accurate. Also measures the loaded Q (quality factor) of the cavity power
        coupler
        :return:
        """
        
        self.reset_interlocks()
        
        print("setting drive to {drive}".format(drive=utils.SAFE_PULSED_DRIVE_LEVEL))
        self.drivelevelPV.put(utils.SAFE_PULSED_DRIVE_LEVEL)
        
        print("running calibration")
        utils.runCalibration(startPV=self.cavityCalibrationStartPV,
                             statusPV=self.cavityCalibrationStatusPV,
                             exception=utils.CavityQLoadedCalibrationError)
        
        print("pushing results")
        utils.pushAndSaveCalibrationChange(measuredPV=self.measuredQLoadedPV,
                                           currentPV=self.currentQLoadedPV,
                                           lowerLimit=loadedQLowerlimit,
                                           upperLimit=loadedQUpperlimit,
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
        
        print("calibration successful")


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
        self.controlPV.put(utils.MAGNET_TRIM_VALUE, waitForPut=False)
    
    def reset(self):
        self.controlPV.put(utils.MAGNET_RESET_VALUE, waitForPut=False)
    
    def turnOn(self):
        self.controlPV.put(utils.MAGNET_ON_VALUE, waitForPut=False)
    
    def turnOff(self):
        self.controlPV.put(utils.MAGNET_OFF_VALUE, waitForPut=False)
    
    def degauss(self):
        self.controlPV.put(utils.MAGNET_DEGAUSS_VALUE, waitForPut=False)
    
    def trim(self):
        self.controlPV.put(utils.MAGNET_TRIM_VALUE, waitForPut=False)


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
            raise Exception("Bad rack name")


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
        
        self.dsLevelPV: PV = PV("CLL:CM{cm}:2301:DS:LVL".format(cm=self.name))
        self.usLevelPV: PV = PV("CLL:CM{cm}:2601:US:LVL".format(cm=self.name))
        self.dsPressurePV: PV = PV("CPT:CM{cm}:2302:DS:PRESS".format(cm=self.name))
        self.jtValveRdbkPV: PV = PV(self.jtPrefix + "ORBV")
        
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


def make_lcls_cryomodules(cryomoduleClass: Type[Cryomodule] = Cryomodule,
                          magnetClass: Type[Magnet] = Magnet,
                          rackClass: Type[Rack] = Rack,
                          cavityClass: Type[Cavity] = Cavity,
                          ssaClass: Type[SSA] = SSA,
                          stepperClass: Type[StepperTuner] = StepperTuner) -> Dict[str, Cryomodule]:
    cryomoduleObjects: Dict[str, Cryomodule] = {}
    linacObjects: List[Linac] = []
    
    for idx, (name, cryomoduleList) in enumerate(LINAC_TUPLES):
        linac = Linac(name, beamlineVacuumInfixes=BEAMLINEVACUUM_INFIXES[idx],
                      insulatingVacuumCryomodules=INSULATINGVACUUM_CRYOMODULES[idx])
        linac.addCryomodules(cryomoduleStringList=cryomoduleList,
                             cryomoduleClass=cryomoduleClass,
                             cavityClass=cavityClass,
                             rackClass=rackClass,
                             magnetClass=magnetClass,
                             ssaClass=ssaClass,
                             stepperClass=stepperClass)
        linacObjects.append(linac)
        cryomoduleObjects.update(linac.cryomodules)
    
    linacObjects[1].addCryomodules(cryomoduleStringList=L1BHL,
                                   cryomoduleClass=cryomoduleClass,
                                   isHarmonicLinearizer=True,
                                   cavityClass=cavityClass,
                                   rackClass=rackClass,
                                   magnetClass=magnetClass,
                                   ssaClass=ssaClass,
                                   stepperClass=stepperClass)
    cryomoduleObjects.update(linacObjects[1].cryomodules)
    return cryomoduleObjects


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
            raise ValueError("Cryomodule {} not found in any linac region.".format(key))
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
