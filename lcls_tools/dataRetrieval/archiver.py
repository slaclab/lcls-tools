from datetime import datetime, timedelta
from json import loads
from typing import List, Dict, Union
from requests import post


# The double braces are to allow for partial formatting
ARCHIVER_URL_FORMATTER = "http://{MACHINE}-archapp.slac.stanford.edu/retrieval/data/{{SUFFIX}}"
SINGLE_RESULT_SUFFIX = "getDataAtTime?at={TIME}-07:00&includeProxies=true"
RANGE_RESULT_SUFFIX = "getData.json?pv={PV}&from={START}&to={END}&donotchunk"


class Archiver(object):
    def __init__(self, machine):
        # type: (str) -> None
        self.url_formatter = ARCHIVER_URL_FORMATTER.format(MACHINE=machine)

    def getDataAtTime(self, pvList, timeRequested):
        # type: (List[str], datetime) -> Dict[str, str]

        suffix = SINGLE_RESULT_SUFFIX.format(TIME=timeRequested.isoformat())
        url = self.url_formatter.format(SUFFIX=suffix)
        print(url)
        print({"pv": ",".join(pvList)})

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

    # def getValuesOverTimeRange(self):


if __name__ == "__main__":
    print(Archiver("lcls").getDataAtTime(["BEND:LTUH:220:BDES"], datetime.now()))