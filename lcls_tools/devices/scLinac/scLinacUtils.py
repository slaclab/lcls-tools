from epics import PV
from time import sleep

SSA_STATUS_ON_VALUE = 3
SSA_SLOPE_CHANGE_TOL = 0.15
LOADED_Q_CHANGE_TOL = 0.15e7
CAVITY_SCALE_CHANGE_TOL = 0.2


class SSACalibrationError(Exception):
    """
    Exception thrown during cavity SSA calibration
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class CavityCalibrationError(Exception):
    """
    Exception thrown during cavity SSA calibration
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
    startPV.put(1)

    # 2 is running
    while statusPV.value == 2:
        sleep(1)

    # 0 is crashed
    if statusPV.value == 0:
        raise exception("{pv} crashed".format(pv=startPV))


def pushAndSaveCalibrationChange(measuredPV: PV, currentPV: PV, tolerance: float,
                                 pushPV: PV, savePV: PV,
                                 exception: Exception = Exception):
    if abs(measuredPV.value - currentPV.value) < tolerance:
        pushPV.put(1)
        savePV.put(1)
    else:
        raise exception("Change to {pv} too large".format(pv=currentPV.pvname))
