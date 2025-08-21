import json
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union

import requests

from lcls_tools.common.controls.epics import EPICS_INVALID_VAL

ARCHIVER_URL_FORMATTER = "http://lcls-archapp.slac.stanford.edu/retrieval/data/{SUFFIX}"


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

    def __hash__(self):
        return self.secs ^ hash(self.val) ^ self.nanos ^ self.severity ^ self.status

    @property
    def timestamp(self) -> datetime:
        if not self._timestamp:
            self._timestamp = datetime.fromtimestamp(self.secs) + timedelta(
                microseconds=self.nanos / 1000
            )
        return self._timestamp

    @property
    def is_valid(self) -> bool:
        return self.severity is not None and self.severity != EPICS_INVALID_VAL


class ArchiveDataHandler:
    def __init__(self, value_list: List[ArchiverValue] = None):
        self.value_list: List[ArchiverValue] = value_list if value_list else []

    def __str__(self):
        data = {
            "timestamps": self.timestamps,
            "values": self.values,
            "is_valid": self.validities,
        }
        return json.dumps(data, indent=4, sort_keys=True, default=str)

    def __eq__(self, other):
        if not isinstance(other, ArchiveDataHandler):
            return False

        else:
            return set(self.value_list) == set(other.value_list)

    @property
    def timestamps(self) -> List[datetime]:
        """
        Current documentation indicates that matplotlib can handle datetime
        objects directly; needs validation
        @return: list of datetimes
        """
        return list(map(lambda value: value.timestamp, self.value_list))

    @property
    def values(self) -> List[Union[str, int, float]]:
        return list(map(lambda value: value.val, self.value_list))

    @property
    def validities(self) -> List[bool]:
        return list(map(lambda value: value.is_valid, self.value_list))


def get_data_at_time(
    pv_list: List[str], time_requested: datetime
) -> Dict[str, ArchiverValue]:
    suffix = SINGLE_RESULT_SUFFIX.format(
        TIME=time_requested.isoformat(timespec="microseconds")
    )
    url = ARCHIVER_URL_FORMATTER.format(SUFFIX=suffix)
    data = {"pv": ",".join(pv_list)}

    response = requests.post(url=url, data=data, timeout=TIMEOUT)

    result: Dict[str, ArchiverValue] = {}

    try:
        json_data = json.loads(response.text)
        for pv, data in json_data.items():
            result[pv] = ArchiverValue(**data)

    except ValueError:
        print(
            "JSON error with {PVS} at {TIME}".format(PVS=pv_list, TIME=time_requested)
        )

    return result


def get_data_with_time_interval(
    pv_list: List[str],
    start_time: datetime,
    end_time: datetime,
    time_delta: timedelta,
) -> Dict[str, ArchiveDataHandler]:
    curr_time = start_time
    result: Dict[str, ArchiveDataHandler] = defaultdict(ArchiveDataHandler)

    while curr_time < end_time:
        value: Dict[str, ArchiverValue] = get_data_at_time(pv_list, curr_time)
        for pv, archiver_value in value.items():
            result[pv].value_list.append(archiver_value)

        curr_time += time_delta

    return result


# returns timestamps in UTC
def get_values_over_time_range(
    pv_list: List[str],
    start_time: datetime,
    end_time: datetime,
    time_delta: timedelta = None,
) -> Dict[str, ArchiveDataHandler]:
    if time_delta:
        return get_data_with_time_interval(pv_list, start_time, end_time, time_delta)

    else:
        url = ARCHIVER_URL_FORMATTER.format(SUFFIX=RANGE_RESULT_SUFFIX)
        result: Dict[str, ArchiveDataHandler] = defaultdict(ArchiveDataHandler)

        # TODO figure out how to send all PVs at once
        for pv in pv_list:
            response = requests.get(
                url=url,
                timeout=TIMEOUT,
                params={
                    "pv": pv,
                    "from": start_time.isoformat(timespec="microseconds") + UTC_DELTA_T,
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
