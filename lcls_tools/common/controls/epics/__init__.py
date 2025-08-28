from time import sleep
from unittest.mock import MagicMock

import epics
from p4p.client.thread import Context

# These are the values that decide whether a PV is alarming (and if so, how)
EPICS_NO_ALARM_VAL = 0
EPICS_MINOR_VAL = 1
EPICS_MAJOR_VAL = 2
EPICS_INVALID_VAL = 3


PVA_CONTEXT = Context("pva", nt=False)


class PVInvalidError(Exception):
    def __init__(self, message):
        super(PVInvalidError, self).__init__(message)


def pv_get_direct(pvname, unwrap=True):
    value = PVA_CONTEXT.get(pvname)
    if value is None:
        value = epics.caget(pvname)
    elif unwrap:
        value = value["value"]
    return value


class PV:
    def __init__(
        self,
        pvname,
        connection_timeout=0.01,
        callback=None,
        verbose=False,
        auto_monitor=None,
        connection_callback=None,
        access_callback=None,
    ):
        self.pvname = pvname
        self.connection_timeout = connection_timeout
        self.callback = callback
        self.verbose = verbose
        self.auto_monitor = auto_monitor
        self.connection_callback = connection_callback
        self.access_callback = access_callback
        self.caobj = epics.PV(
            pvname=self.pvname,
            connection_timeout=self.connection_timeout,
            verbose=self.verbose,
            auto_monitor=self.auto_monitor,
        )

    def __str__(self):
        return f"{self.pvname} PV Object"

    @property
    def val(self):
        return pv_get_direct(self.pvname, timeout=self.connection_timeout)

    def caget(self, unwrap=True, as_string=False, as_numpy=True):
        attempt = 1
        while True:
            if attempt > 3:
                raise PVInvalidError(f"{self} caget failed 3 times, aborting")
            value = PVA_CONTEXT.get(self.pvname)
            if value is None:
                value = self.caobj.get(as_string=as_string, as_numpy=as_numpy)
            elif unwrap:
                value = value["value"]
                if as_string:
                    value = str(value)

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
            status = PVA_CONTEXT.put(self.pvname, value)
            if status is None:
                status = self.caobj.put(value)
                if status is None:
                    break
            attempt += 1
            print(f"{self} caput did not execute successfully, retrying")
            sleep(0.5)
        return status

    def get(
        self,
        unwrap=True,
        as_string=False,
        as_numpy=True,
        timeout=None,
        use_caget=True,
    ):
        if use_caget:
            return self.caget(unwrap=unwrap, as_string=as_string, as_numpy=as_numpy)
        return self.val

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
            # Mimic CA logic
            return self.caput(value)

        status = self.caput(
            value,
            wait=wait,
            timeout=timeout,
            use_complete=use_complete,
            callback=callback,
            callback_data=callback_data,
        )

        if retry and (status != 1):
            print(f"{self} put not successful, retrying...")
            self.caput(
                value,
                wait=wait,
                timeout=timeout,
                use_complete=use_complete,
                callback=callback,
                callback_data=callback_data,
            )


def make_mock_pv(
    pv_name: str = None, get_val=None, severity=EPICS_NO_ALARM_VAL
) -> MagicMock:
    return MagicMock(
        pvname=pv_name,
        put=MagicMock(return_value=1),
        get=MagicMock(return_value=get_val),
        severity=severity,
    )
