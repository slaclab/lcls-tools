from datetime import datetime
from math import isclose
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
    
    def get(self, count=None, as_string=False, as_numpy=True,
            timeout=None, with_ctrlvars=False, use_monitor=True,
            retry_until_valid=True):
        
        self.connect()
        if retry_until_valid:
            value = super().get(count, as_string, as_numpy, timeout,
                                with_ctrlvars, use_monitor)
            while value is None:
                value = super().get(count, as_string, as_numpy, timeout,
                                    with_ctrlvars, use_monitor)
                print(f"{self.pvname} value is None, retrying")
                sleep(0.5)
            return value
        
        else:
            return super().get(count, as_string, as_numpy, timeout,
                               with_ctrlvars, use_monitor)
    
    def put(self, value, wait=True, timeout=30.0,
            use_complete=False, callback=None, callback_data=None,
            waitForPut=False):
        super(PV, self).put(value, wait=wait, timeout=timeout,
                            use_complete=use_complete, callback=callback,
                            callback_data=callback_data)
        
        if waitForPut:
            attempt = 1
            while self.severity == EPICS_INVALID_VAL or not self.connect():
                if attempt >= 5:
                    raise PVInvalidError("{pv} invalid or disconnected, aborting wait for put"
                                         .format(pv=self.pvname))
                attempt += 1
                sleep(0.1)
            
            if type(value) != float:
                while self.value != value:
                    self.printAndSleep(value)
            else:
                while not isclose(self.value, value, rel_tol=1e-06):
                    self.printAndSleep(value)
    
    def printAndSleep(self, value):
        print("waiting for {pv} to be {val} at {time}".format(pv=self.pvname,
                                                              val=value,
                                                              time=datetime.now()))
        sleep(1)
