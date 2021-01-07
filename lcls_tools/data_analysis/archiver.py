from datetime import datetime, timedelta
import json
# from typing import List, Dict, Union
import requests
from unittest import TestCase, main as test

# Python compatibility. The first branch is for 3, the second for 2
try:
    from unittest import mock
except ImportError:
    import mock

# The double braces are to allow for partial formatting
ARCHIVER_URL_FORMATTER = "http://{MACHINE}-archapp.slac.stanford.edu/retrieval/data/{{SUFFIX}}"
SINGLE_RESULT_SUFFIX = "getDataAtTime?at={TIME}-07:00&includeProxies=true"
RANGE_RESULT_SUFFIX = "getData.json"

TIMEOUT = 3


class Archiver(object):
    def __init__(self, machine):
        # type: (str) -> None
        self.url_formatter = ARCHIVER_URL_FORMATTER.format(MACHINE=machine)

    def getDataAtTime(self, pvList, timeRequested):
        # type: (List[str], datetime) -> Dict[str, str]

        suffix = SINGLE_RESULT_SUFFIX.format(TIME=timeRequested.isoformat())
        url = self.url_formatter.format(SUFFIX=suffix)

        response = requests.post(url=url, data={"pv": ",".join(pvList)},
                                 timeout=TIMEOUT)

        results = {}

        try:
            jsonData = json.loads(response.text)
            for key, val in jsonData.items():
                results[key] = val[u'val']

        except ValueError:
            print("JSON error with {PVS} at {TIME}".format(PVS=pvList,
                                                           TIME=timeRequested))
        return results

    def getDataWithTimeInterval(self, pvList, startTime, endTime, timeDelta):
        # type: (List[str], datetime, datetime, timedelta) -> Dict[str, Dict[str, List[Union[datetime, str]]]]
        currTime = startTime
        results = {}
        for pv in pvList:
            results[pv] = {"times": [], "values": []}

        while currTime < endTime:
            result = self.getDataAtTime(pvList, currTime)
            for key, val in result.items():
                results[key]["times"].append(currTime)
                results[key]["values"].append(val)
            currTime += timeDelta

        return results

    # returns timestamps in UTC
    def getValuesOverTimeRange(self, pvList, startTime, endTime, timeDelta=None):
        # type: (List[str], datetime, datetime, timedelta) -> Dict[str, Dict[str, List[Union[datetime, str]]]]

        if timeDelta:
            return self.getDataWithTimeInterval(pvList, startTime, endTime, timeDelta)
        else:
            url = self.url_formatter.format(SUFFIX=RANGE_RESULT_SUFFIX)

            results = {}

            # TODO figure out how to send all PVs at once
            for pv in pvList:

                response = requests.get(url=url, timeout=TIMEOUT,
                                        params={"pv": pv,
                                                "from": startTime.isoformat() + "-07:00",
                                                "to": endTime.isoformat() + "-07:00"})

                try:
                    jsonData = json.loads(response.text)
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


class Tester(TestCase):

    def __init__(self, *args, **kwargs):
        super(Tester, self).__init__(*args, **kwargs)
        self.archiver = Archiver("lcls")

        self.time = datetime(year=2020, month=10, day=14, hour=11,
                             minute=56, second=30, microsecond=10)

        self.pvList = ["BEND:LTUH:220:BDES", "BEND:LTUH:280:BDES"]

        self.jsonDict = {u'BEND:LTUH:280:BDES': {u'nanos': 230452646, u'status': 0,
                                                 u'secs': 1602694677, u'severity': 0,
                                                 u'val': 10.7099896749672},
                         u'BEND:LTUH:220:BDES': {u'nanos': 230327182, u'status': 0,
                                                 u'secs': 1602694677, u'severity': 0,
                                                 u'val': 10.709989796551309}}

        self.expectedSingleResult = {'BEND:LTUH:280:BDES': 10.7099896749672,
                                     'BEND:LTUH:220:BDES': 10.709989796551309}

        multiResult280 = {'values': [10.69994225003475, 10.69994225003475,
                                     10.69994225003475, 10.69994225003475,
                                     10.69994225003475, 10.69998960449891,
                                     10.709996462228325, 10.709943385505909,
                                     10.709999116032312, 10.70997130324195],
                          'times': [datetime(2020, 10, 4, 11, 56, 30, 10),
                                    datetime(2020, 10, 5, 11, 56, 30, 10),
                                    datetime(2020, 10, 6, 11, 56, 30, 10),
                                    datetime(2020, 10, 7, 11, 56, 30, 10),
                                    datetime(2020, 10, 8, 11, 56, 30, 10),
                                    datetime(2020, 10, 9, 11, 56, 30, 10),
                                    datetime(2020, 10, 10, 11, 56, 30, 10),
                                    datetime(2020, 10, 11, 11, 56, 30, 10),
                                    datetime(2020, 10, 12, 11, 56, 30, 10),
                                    datetime(2020, 10, 13, 11, 56, 30, 10)]}

        multiResult220 = {'values': [10.6999430312505, 10.6999430312505,
                                     10.6999430312505, 10.6999430312505,
                                     10.6999430312505, 10.699989622852124,
                                     10.709996502988615, 10.709944052738756,
                                     10.709999125516292, 10.709944052743765],
                          'times': [datetime(2020, 10, 4, 11, 56, 30, 10),
                                    datetime(2020, 10, 5, 11, 56, 30, 10),
                                    datetime(2020, 10, 6, 11, 56, 30, 10),
                                    datetime(2020, 10, 7, 11, 56, 30, 10),
                                    datetime(2020, 10, 8, 11, 56, 30, 10),
                                    datetime(2020, 10, 9, 11, 56, 30, 10),
                                    datetime(2020, 10, 10, 11, 56, 30, 10),
                                    datetime(2020, 10, 11, 11, 56, 30, 10),
                                    datetime(2020, 10, 12, 11, 56, 30, 10),
                                    datetime(2020, 10, 13, 11, 56, 30, 10)]}
        
        self.expectedDeltaResult = {'BEND:LTUH:280:BDES': multiResult280,
                                    'BEND:LTUH:220:BDES': multiResult220}

    class MockResponse(object):
        def __init__(self):
            self.text = ""

    @mock.patch("requests.post")
    @mock.patch("json.loads")
    def testGetDataAtTimeMockedData(self, mockedLoads, mockedPost):

        mockedLoads.return_value = self.jsonDict
        mockedPost.return_value = self.MockResponse()

        self.assertEqual(self.archiver.getDataAtTime(self.pvList,
                                                     self.time),
                         self.expectedSingleResult)

    def testGetDataAtTime(self):
        try:
            self.assertEqual(self.archiver.getDataAtTime(self.pvList,
                                                         self.time),
                             self.expectedSingleResult)
        except requests.exceptions.Timeout:
            self.skipTest("testGetDataAtTime connection timed out")

    def testGetDataWithTimeInterval(self):
        try:
            self.assertEqual(self.archiver.getDataWithTimeInterval(self.pvList,
                                                                   self.time - timedelta(days=10),
                                                                   self.time,
                                                                   timedelta(days=1)),
                             self.expectedDeltaResult)

        except requests.exceptions.Timeout:
            self.skipTest("testGetDataWithTimeInterval connection timed out")

    def testGetDataWithTimeIntervalMocked(self):
        def side_effect(pvList, time):
            self.assertEqual(pvList, self.pvList)

            if time == datetime(2020, 10, 4, 11, 56, 30, 10):
                return {u'BEND:LTUH:280:BDES': 10.69994225003475,
                        u'BEND:LTUH:220:BDES': 10.6999430312505}
            elif time == datetime(2020, 10, 5, 11, 56, 30, 10):
                return {u'BEND:LTUH:280:BDES': 10.69994225003475,
                        u'BEND:LTUH:220:BDES': 10.6999430312505}
            elif time == datetime(2020, 10, 6, 11, 56, 30, 10):
                return {u'BEND:LTUH:280:BDES': 10.69994225003475,
                        u'BEND:LTUH:220:BDES': 10.6999430312505}
            elif time == datetime(2020, 10, 7, 11, 56, 30, 10):
                return {u'BEND:LTUH:280:BDES': 10.69994225003475,
                        u'BEND:LTUH:220:BDES': 10.6999430312505}
            elif time == datetime(2020, 10, 8, 11, 56, 30, 10):
                return {u'BEND:LTUH:280:BDES': 10.69994225003475,
                        u'BEND:LTUH:220:BDES': 10.6999430312505}
            elif time == datetime(2020, 10, 9, 11, 56, 30, 10):
                return {u'BEND:LTUH:280:BDES': 10.69998960449891,
                        u'BEND:LTUH:220:BDES': 10.699989622852124}
            elif time == datetime(2020, 10, 10, 11, 56, 30, 10):
                return {u'BEND:LTUH:280:BDES': 10.709996462228325,
                        u'BEND:LTUH:220:BDES': 10.709996502988615}
            elif time == datetime(2020, 10, 11, 11, 56, 30, 10):
                return {u'BEND:LTUH:280:BDES': 10.709943385505909,
                        u'BEND:LTUH:220:BDES': 10.709944052738756}
            elif time == datetime(2020, 10, 12, 11, 56, 30, 10):
                return {u'BEND:LTUH:280:BDES': 10.709999116032312,
                        u'BEND:LTUH:220:BDES': 10.709999125516292}
            elif time == datetime(2020, 10, 13, 11, 56, 30, 10):
                return {u'BEND:LTUH:280:BDES': 10.70997130324195,
                        u'BEND:LTUH:220:BDES': 10.709944052743765}
            else:
                raise Exception("Unexpected datetime")

        self.archiver.getDataAtTime = mock.MagicMock(name="getDataAtTime")
        self.archiver.getDataAtTime.side_effect = side_effect

        self.assertEqual(self.archiver.getDataWithTimeInterval(self.pvList,
                                                               self.time - timedelta(days=10),
                                                               self.time,
                                                               timedelta(days=1)),
                         self.expectedDeltaResult)


if __name__ == "__main__":
    test()
