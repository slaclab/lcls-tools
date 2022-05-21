from datetime import datetime
from time import sleep

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
        attempt = 1
        while self.severity == EPICS_INVALID_VAL or not self.connected:
            if attempt >= 5:
                raise PVInvalidError("{pv} invalid or disconnected, aborting wait for put"
                                     .format(pv=self.pvname))
            attempt += 1
            sleep(1)

        if waitForPut:
            while self.value != value:
                print("waiting for {pv} to be {val} at {time}".format(pv=self.pvname,
                                                                      val=value,
                                                                      time=datetime.now()))
                sleep(0.3)
