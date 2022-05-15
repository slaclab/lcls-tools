from datetime import datetime

from epics import PV as epicsPV

# These are the values that decide whether a PV is alarming (and if so, how)
EPICS_NO_ALARM_VAL = 0
EPICS_MINOR_VAL = 1
EPICS_MAJOR_VAL = 2
EPICS_INVALID_VAL = 3


class PVInvalidError(Exception):
    def __init__(self, message):
        super(PVInvalidError, self).__init__(message)


class PV(epicsPV):
    def __init__(self, pvname):
        super().__init__(pvname, connection_timeout=0.01)

    def put(self, value, wait=False, timeout=30.0,
            use_complete=False, callback=None, callback_data=None,
            waitForPut=True):
        super(PV, self).put(value, wait, timeout, use_complete, callback,
                            callback_data)
        if waitForPut:
            if self.severity == EPICS_INVALID_VAL or not self.connected:
                raise PVInvalidError("{pv} invalid or disconnected, aborting wait for put"
                                     .format(pv=self.pvname))
            while self.value != value:
                print("setting {pv} to {val} at {time}".format(pv=self.pvname,
                                                               val=value,
                                                               time=datetime.now()))
