import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Union

import numpy as np
import requests

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
class ArchiverData:
    """
    A data class for easier data handling (so that external functions can
    invoke .values and .timestamps instead of having to remember dictionary keys
    """

    # todo make this not a union
    # Currently one list if timestamps are shared by all PVs else a dict of
    # pv -> timstamps
    timeStamps: Union[List[datetime], Dict[str, List[datetime]]]
    values: Dict[str, List]


class Archiver:
    def __init__(self, machine: str):
        """
        machine is a string that is either "lcls" or "facet"
        """
        self.url_formatter = ARCHIVER_URL_FORMATTER.format(MACHINE=machine)

    def getDataAtTime(self, pvList, timeRequested):
        # type: (List[str], datetime) -> ArchiverData

        suffix = SINGLE_RESULT_SUFFIX.format(TIME=timeRequested.isoformat())
        url = self.url_formatter.format(SUFFIX=suffix)

        response = requests.post(
            url=url, data={"pv": ",".join(pvList)}, timeout=TIMEOUT
        )

        values = {}
        times = [timeRequested]
        for pv in pvList:
            values[pv] = []

        try:
            jsonData = json.loads(response.text)
            for pv, data in jsonData.items():
                values[pv].append(data["val"])

        except ValueError:
            print(
                "JSON error with {PVS} at {TIME}".format(PVS=pvList, TIME=timeRequested)
            )
            print(jsonData)
        return ArchiverData(timeStamps=times, values=values)

    def getDataWithTimeInterval(self, pvList, startTime, endTime, timeDelta):
        # type: (List[str], datetime, datetime, timedelta) -> ArchiverData
        currTime = startTime
        times = []
        values = {}
        for pv in pvList:
            values[pv] = []

        while currTime < endTime:
            result = self.getDataAtTime(pvList, currTime)
            times.append(currTime)
            for pv, valueList in result.values.items():
                try:
                    values[pv].append(valueList.pop())
                except IndexError:
                    values[pv].append(np.nan)
            currTime += timeDelta

        return ArchiverData(timeStamps=times, values=values)

    # returns timestamps in UTC
    def getValuesOverTimeRange(self, pvList, startTime, endTime, timeDelta=None):
        # type: (List[str], datetime, datetime, timedelta) -> ArchiverData

        if timeDelta:
            return self.getDataWithTimeInterval(pvList, startTime, endTime, timeDelta)
        else:
            url = self.url_formatter.format(SUFFIX=RANGE_RESULT_SUFFIX)

            times = {}
            values = {}

            # TODO figure out how to send all PVs at once
            for pv in pvList:
                times[pv] = []
                values[pv] = []

                response = requests.get(
                    url=url,
                    timeout=TIMEOUT,
                    params={
                        "pv": pv,
                        "from": startTime.isoformat() + UTC_DELTA_T,
                        "to": endTime.isoformat() + UTC_DELTA_T,
                    },
                )

                try:
                    jsonData = json.loads(response.text)
                    # It returns a list of len 1 for some godforsaken reason...
                    # unless the archiver returns no data in which case the list is empty...
                    if len(jsonData) == 0:
                        times[pv].append([])
                        values[pv].append([])
                    else:
                        element = jsonData.pop()
                        for datum in element["data"]:
                            # TODO implement filtering by BSA PV

                            # Using keys from documentation found at:
                            # https://slacmshankar.github.io/epicsarchiver_docs/userguide.html
                            times[pv].append(
                                datetime.fromtimestamp(datum["secs"])
                                + timedelta(microseconds=datum["nanos"] / 1000)
                            )
                            values[pv].append(datum["val"])

                except ValueError:
                    print("JSON error with {pv}".format(pv=pv))

            return ArchiverData(timeStamps=times, values=values)
