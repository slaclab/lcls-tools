from epics import PV
from epics.ca import CASeverityException
from time import sleep

SSA_STATUS_ON_VALUE = 3
SSA_SLOPE_LOWER_LIMIT = 0.5
SSA_SLOPE_UPPER_LIMIT = 1.5
# TODO add limits for the HL cavities
LOADED_Q_LOWER_LIMIT = 3.895e7
LOADED_Q_UPPER_LIMIT = 4.305e7
CAVITY_SCALE_UPPER_LIMIT = 40
CAVITY_SCALE_LOWER_LIMIT = 10
DESIGN_Q_LOADED = 4.1e7


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
