from datetime import datetime, timedelta
from json import loads
from typing import List, Dict, Union
from requests import post, get


# The double braces are to allow for partial formatting
ARCHIVER_URL_FORMATTER = "http://{MACHINE}-archapp.slac.stanford.edu/retrieval/data/{{SUFFIX}}"
SINGLE_RESULT_SUFFIX = "getDataAtTime?at={TIME}-07:00&includeProxies=true"
RANGE_RESULT_SUFFIX = "getData.json"


class Archiver(object):
    def __init__(self, machine):
        # type: (str) -> None
        self.url_formatter = ARCHIVER_URL_FORMATTER.format(MACHINE=machine)

    def getDataAtTime(self, pvList, timeRequested):
        # type: (List[str], datetime) -> Dict[str, str]

        suffix = SINGLE_RESULT_SUFFIX.format(TIME=timeRequested.isoformat())
        url = self.url_formatter.format(SUFFIX=suffix)

        response = post(url=url, data={"pv": ",".join(pvList)})

        results = {}

        try:
            jsonData = loads(response.text)
            for key, val in jsonData.items():
                results[key.encode('ascii', 'ignore')] = val[u'val']

        except ValueError:
            print("JSON error with {PVS} at {TIME}".format(PVS=pvList,
                                                           TIME=timeRequested))
        return results

    def getDataWithTimeInterval(self, pvList, startTime, endTime, timeInterval):
        # type: (List[str], datetime, datetime, int) -> Dict[str, Dict[str, List[Union[datetime, str]]]]
        currTime = startTime
        results = {}
        for pv in pvList:
            results[pv] = {"times": [], "values": []}

        while currTime < endTime:
            result = self.getDataAtTime(pvList, currTime)
            for key, val in result.items():
                results[key]["times"].append(currTime)
                results[key]["values"].append(val)
            currTime += timedelta(seconds=timeInterval)

        return results

    # returns timestamps in UTC
    def getValuesOverTimeRange(self, pvList, startTime, endTime, timeInterval=None):
        # type: (List[str], datetime, datetime, int) -> Dict[str, Dict[str, List[Union[datetime, str]]]]

        if timeInterval:
            return self.getDataWithTimeInterval(pvList, startTime, endTime, timeInterval)
        else:
            url = self.url_formatter.format(SUFFIX=RANGE_RESULT_SUFFIX)

            results = {}

            # TODO figure out how to send all PVs at once
            for pv in pvList:

                response = get(url=url, params={"pv": pv,
                                                "from": startTime.isoformat()+"-07:00",
                                                "to": endTime.isoformat()+"-07:00"})

                try:
                    jsonData = loads(response.text)
                    # It returns a list of len 1 for some godforsaken reason...
                    element = jsonData.pop()
                    result = {"times": [], "values": []}
                    for datum in element[u'data']:
                        result["times"].append(datum[u'secs'])
                        result["values"].append(datum[u'val'])

                    results[pv] = result

                except ValueError:
                    print("JSON error with {PVS}".format(PVS=pvList))

            return results


if __name__ == "__main__":
    archiver = Archiver("lcls")
    testList = ["BEND:LTUH:220:BDES", "BEND:LTUH:280:BDES"]
    print("getDataAtTime")
    print(archiver.getDataAtTime(testList, datetime.now()))
    print()
    print("getDataWithTimeInterval")
    print(archiver.getDataWithTimeInterval(testList,
                                           datetime.now() - timedelta(seconds=10),
                                           datetime.now(), 1))
    print()
    print("getValuesOverTimeRange")
    print(archiver.getValuesOverTimeRange(testList,
                                          datetime.now() - timedelta(days=10),
                                          datetime.now()))