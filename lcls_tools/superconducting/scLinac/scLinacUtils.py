from time import sleep

from epics import PV
from epics.ca import CASeverityException

SSA_STATUS_ON_VALUE = 3
SSA_SLOPE_LOWER_LIMIT = 0.5
SSA_SLOPE_UPPER_LIMIT = 1.5

# TODO add limits for the HL cavities
LOADED_Q_LOWER_LIMIT = 3.895e7
LOADED_Q_UPPER_LIMIT = 4.305e7
DESIGN_Q_LOADED = 4.1e7

CAVITY_SCALE_UPPER_LIMIT = 40
CAVITY_SCALE_LOWER_LIMIT = 10

RF_MODE_SELAP = 0
RF_MODE_SELA = 1
RF_MODE_SEL = 2
RF_MODE_SEL_RAW = 3
RF_MODE_PULSE = 4
RF_MODE_CHIRP = 5

SAFE_PULSED_DRIVE_LEVEL = 15
NOMINAL_PULSED_ONTIME = 70

STEPPER_TEMP_LIMIT = 70
DEFAULT_STEPPER_MAX_STEPS = 1000000
DEFAULT_STEPPER_SPEED = 20000
MAX_STEPPER_SPEED = 60000

# these values are based on the list of enum states found by probing {Magnettype}:L{x}B:{cm}85:CTRL
MAGNET_RESET_VALUE = 10
MAGNET_ON_VALUE = 11
MAGNET_OFF_VALUE = 12
MAGNET_DEGAUSS_VALUE = 13
MAGNET_TRIM_VALUE = 1


class PulseError(Exception):
    """
    Exception thrown during cavity SSA calibration
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class StepperError(Exception):
    """
    Exception thrown during cavity SSA calibration
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class SSACalibrationError(Exception):
    """
    Exception thrown during cavity SSA calibration
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class CavityQLoadedCalibrationError(Exception):
    """
    Exception thrown during cavity loaded Q measurement
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class CavityScaleFactorCalibrationError(Exception):
    """
    Exception thrown during cavity scale factor calibration
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class SSAPowerError(Exception):
    """
    Exception thrown while trying to turn an SSA on or off
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


def runCalibration(startPV: PV, statusPV: PV, exception: Exception = Exception):
    try:
        startPV.put(1)

        # 2 is running
        while statusPV.value == 2:
            sleep(1)

        # 0 is crashed
        if statusPV.value == 0:
            raise exception("{pv} crashed".format(pv=startPV))
    except CASeverityException:
        raise exception('CASeverityException')


def pushAndSaveCalibrationChange(measuredPV: PV, currentPV: PV, lowerLimit: float, upperLimit: float,
                                 pushPV: PV, savePV: PV,
                                 exception: Exception = Exception):
    if lowerLimit < measuredPV.value < upperLimit:
        pushPV.put(1)
        savePV.put(1)
    else:
        raise exception("Change to {pv} too large".format(pv=currentPV.pvname))
