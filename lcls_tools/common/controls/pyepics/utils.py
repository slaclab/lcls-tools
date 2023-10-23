from time import sleep

from epics import PV as epics_pv, caget as epics_caget, caput as epics_caput

# These are the values that decide whether a PV is alarming (and if so, how)
EPICS_NO_ALARM_VAL = 0
EPICS_MINOR_VAL = 1
EPICS_MAJOR_VAL = 2
EPICS_INVALID_VAL = 3


class PVInvalidError(Exception):
    def __init__(self, message):
        super(PVInvalidError, self).__init__(message)


class PV(epics_pv):
    def __init__(self, pvname):
        super().__init__(pvname, connection_timeout=0.01)

    def __str__(self):
        return f"{self.pvname} PV Object"

    def caget(self, count=None, as_string=False, as_numpy=True, use_monitor=True):
        attempt = 1
        while True:
            if attempt > 3:
                raise PVInvalidError(f"{self} caget failed 3 times, aborting")
            value = epics_caget(
                self.pvname,
                as_string=as_string,
                count=count,
                as_numpy=as_numpy,
                use_monitor=use_monitor,
            )
            if value is not None:
                break
            attempt += 1
            print(f"{self.pvname} did not return a valid value, retrying")
            sleep(0.5)
        return value

    def caput(self, value):
        attempt = 1
        while True:
            if attempt > 3:
                raise PVInvalidError(f"{self} caget failed 3 times, aborting")
            status = epics_caput(self.pvname, value)
            if status == 1:
                break
            attempt += 1
            print(f"{self} caput did not execute successfully, retrying")
            sleep(0.5)
        return status

    def get(
        self,
        count=None,
        as_string=False,
        as_numpy=True,
        timeout=None,
        with_ctrlvars=False,
        use_monitor=True,
        use_caget=True,
    ):
        if use_caget:
            return self.caget(
                as_string=as_string, as_numpy=as_numpy, use_monitor=use_monitor
            )

        else:
            self.connect()

            value = super().get(
                count, as_string, as_numpy, timeout, with_ctrlvars, use_monitor
            )
            if value is not None:
                return value
            else:
                print(f"{self} get failed, trying caget instead")
                return self.caget(
                    as_string=as_string, as_numpy=as_numpy, use_monitor=use_monitor
                )

    def put(
        self,
        value,
        wait=True,
        timeout=30.0,
        use_complete=False,
        callback=None,
        callback_data=None,
        retry=True,
        use_caput=True,
    ):
        if use_caput:
            return self.caput(value)

        status = super().put(
            value,
            wait=wait,
            timeout=timeout,
            use_complete=use_complete,
            callback=callback,
            callback_data=callback_data,
        )

        if retry and (status != 1):
            print(f"{self} put not successful, using caput")
            self.caput(value)
