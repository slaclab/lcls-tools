import json
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Union, Optional

import requests

from lcls_tools.common.controls.pyepics.utils import EPICS_INVALID_VAL

# The double braces are to allow for partial formatting
ARCHIVER_URL_FORMATTER = (
    "http://{MACHINE}-archapp.slac.stanford.edu/retrieval/data/{{SUFFIX}}"
)

# If daylight savings time, SLAC is 7 hours behind UTC otherwise 8
if time.localtime().tm_isdst:
    UTC_DELTA_T = "-07:00"
else:
    UTC_DELTA_T = "-08:00"

SINGLE_RESULT_SUFFIX = "getDataAtTime?at={TIME}" + UTC_DELTA_T + "&includeProxies=true"
RANGE_RESULT_SUFFIX = "getData.json"

TIMEOUT = 3


@dataclass
class ArchiverValue:
    """
    Using keys from documentation found at:
    https://slacmshankar.github.io/epicsarchiver_docs/userguide.html
    """

    secs: int = None
    val: Union[float, int, str] = None
    nanos: int = None
    severity: int = None
    status: int = None
    fields: Optional[Dict] = None
    _timestamp: Optional[datetime] = None

    @property
    def timestamp(self):
        if not self._timestamp:
            self._timestamp = datetime.fromtimestamp(self.secs) + timedelta(
                microseconds=self.nanos / 1000
            )
        return self._timestamp

    @property
    def is_valid(self):
        return self.severity is not None and self.severity != EPICS_INVALID_VAL


class ArchiveDataHandler:
    def __init__(self, value_list: List[ArchiverValue] = None):
        self.value_list: List[ArchiverValue] = value_list if value_list else []

    def __str__(self):
        data = {
            "timestamps": self.epoch_timestamps,
            "values": self.values,
            "is_valid": self.validities,
        }
        return json.dumps(data, indent=4, sort_keys=True, default=str)

    @property
    def timestamps(self):
        return list(map(lambda value: value.timestamp, self.value_list))

    @property
    def epoch_timestamps(self):
        return list(map(lambda value: value.timestamp.timestamp(), self.value_list))

    @property
    def values(self):
        return list(map(lambda value: value.val, self.value_list))

    @property
    def validities(self):
        return list(map(lambda value: value.is_valid, self.value_list))


class Archiver:
    def __init__(self, machine: str):
        """
        machine is a string that is either "lcls" or "facet"
        """
        self.url_formatter = ARCHIVER_URL_FORMATTER.format(MACHINE=machine)

    def get_data_at_time(self, pv_list, time_requested):
        # type: (List[str], datetime) -> Dict[str, ArchiverValue]

        suffix = SINGLE_RESULT_SUFFIX.format(
            TIME=time_requested.isoformat(timespec="microseconds")
        )
        url = self.url_formatter.format(SUFFIX=suffix)

        response = requests.post(
            url=url, data={"pv": ",".join(pv_list)}, timeout=TIMEOUT
        )

        result: Dict[str, ArchiverValue] = {}

        try:
            json_data = json.loads(response.text)
            for pv, data in json_data.items():
                result[pv] = ArchiverValue(**data)

        except ValueError:
            print(
                "JSON error with {PVS} at {TIME}".format(
                    PVS=pv_list, TIME=time_requested
                )
            )
        return result

    def get_data_with_time_interval(self, pv_list, start_time, end_time, time_delta):
        # type: (List[str], datetime, datetime, timedelta) -> Dict[str, ArchiveDataHandler]
        curr_time = start_time

        result: Dict[str, ArchiveDataHandler] = defaultdict(ArchiveDataHandler)

        while curr_time < end_time:
            value: Dict[str, ArchiverValue] = self.get_data_at_time(pv_list, curr_time)
            for pv, archiver_value in value.items():
                result[pv].value_list.append(archiver_value)

            curr_time += time_delta

        return result

    # returns timestamps in UTC
    def get_values_over_time_range(
        self, pv_list, start_time, end_time, time_delta=None
    ):
        # type: (List[str], datetime, datetime, timedelta) -> Dict[str, ArchiveDataHandler]

        if time_delta:
            return self.get_data_with_time_interval(
                pv_list, start_time, end_time, time_delta
            )

        else:
            url = self.url_formatter.format(SUFFIX=RANGE_RESULT_SUFFIX)
            result: Dict[str, ArchiveDataHandler] = defaultdict(ArchiveDataHandler)

            # TODO figure out how to send all PVs at once
            for pv in pv_list:
                response = requests.get(
                    url=url,
                    timeout=TIMEOUT,
                    params={
                        "pv": pv,
                        "from": start_time.isoformat(timespec="microseconds")
                        + UTC_DELTA_T,
                        "to": end_time.isoformat(timespec="microseconds") + UTC_DELTA_T,
                    },
                )

                try:
                    json_data = json.loads(response.text)
                    # It returns a list of len 1 for some godforsaken reason...
                    # unless the archiver returns no data in which case the list is empty...
                    if len(json_data) == 0:
                        result[pv] = ArchiveDataHandler()
                    else:
                        element = json_data.pop()
                        for datum in element["data"]:
                            data_obj: ArchiverValue = ArchiverValue(**datum)
                            result[pv].value_list.append(data_obj)

                except ValueError:
                    print("JSON error with {pv}".format(pv=pv))

            return result
