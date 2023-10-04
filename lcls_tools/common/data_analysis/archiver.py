import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Union
from unittest import TestCase, main as test

import numpy as np
import requests

# Python compatibility. The first branch is for 3, the second for 2
try:
    from unittest import mock
except ImportError:
    import mock

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


class Tester(TestCase):
    def __init__(self, *args, **kwargs):
        super(Tester, self).__init__(*args, **kwargs)
        self.archiver = Archiver("lcls")

        self.time = datetime(
            year=2020, month=10, day=14, hour=11, minute=56, second=30, microsecond=10
        )

        self.pvList = ["BEND:LTUH:220:BDES", "BEND:LTUH:280:BDES"]

        self.jsonDict = {
            "BEND:LTUH:280:BDES": {
                "nanos": 230452646,
                "status": 0,
                "secs": 1602694677,
                "severity": 0,
                "val": 10.7099896749672,
            },
            "BEND:LTUH:220:BDES": {
                "nanos": 230327182,
                "status": 0,
                "secs": 1602694677,
                "severity": 0,
                "val": 10.709989796551309,
            },
        }

        self.expectedSingleResult = ArchiverData(
            timeStamps=[self.time],
            values={
                "BEND:LTUH:280:BDES": [10.7099896749672],
                "BEND:LTUH:220:BDES": [10.709989796551309],
            },
        )

        times = [
            datetime(2020, 10, 4, 11, 56, 30, 10),
            datetime(2020, 10, 5, 11, 56, 30, 10),
            datetime(2020, 10, 6, 11, 56, 30, 10),
            datetime(2020, 10, 7, 11, 56, 30, 10),
            datetime(2020, 10, 8, 11, 56, 30, 10),
            datetime(2020, 10, 9, 11, 56, 30, 10),
            datetime(2020, 10, 10, 11, 56, 30, 10),
            datetime(2020, 10, 11, 11, 56, 30, 10),
            datetime(2020, 10, 12, 11, 56, 30, 10),
            datetime(2020, 10, 13, 11, 56, 30, 10),
        ]

        multiResult280 = [
            10.69994225003475,
            10.69994225003475,
            10.69994225003475,
            10.69994225003475,
            10.69994225003475,
            10.69998960449891,
            10.709996462228325,
            10.709943385505909,
            10.709999116032312,
            10.70997130324195,
        ]

        multiResult220 = [
            10.6999430312505,
            10.6999430312505,
            10.6999430312505,
            10.6999430312505,
            10.6999430312505,
            10.699989622852124,
            10.709996502988615,
            10.709944052738756,
            10.709999125516292,
            10.709944052743765,
        ]

        self.expectedDeltaResult = ArchiverData(
            timeStamps=times,
            values={
                "BEND:LTUH:280:BDES": multiResult280,
                "BEND:LTUH:220:BDES": multiResult220,
            },
        )

        times220 = [
            datetime(2020, 10, 1, 10, 7, 28, 958256),
            datetime(2020, 10, 8, 12, 45, 6, 319376),
            datetime(2020, 10, 8, 12, 46, 35, 772626),
            datetime(2020, 10, 9, 19, 28, 22, 560327),
            datetime(2020, 10, 9, 19, 28, 22, 574587),
            datetime(2020, 10, 10, 7, 2, 54, 736791),
            datetime(2020, 10, 10, 7, 2, 54, 749858),
            datetime(2020, 10, 10, 11, 28, 31, 542118),
            datetime(2020, 10, 10, 11, 28, 31, 558124),
            datetime(2020, 10, 10, 11, 30, 11, 597275),
            datetime(2020, 10, 10, 11, 30, 11, 611033),
            datetime(2020, 10, 10, 12, 12, 27, 536147),
            datetime(2020, 10, 10, 12, 12, 27, 548572),
            datetime(2020, 10, 10, 12, 14, 17, 51221),
            datetime(2020, 10, 10, 12, 14, 17, 63504),
            datetime(2020, 10, 10, 19, 13, 49, 999732),
            datetime(2020, 10, 10, 19, 13, 50, 20727),
            datetime(2020, 10, 10, 21, 17, 50, 745971),
            datetime(2020, 10, 10, 21, 17, 50, 759017),
            datetime(2020, 10, 11, 8, 16, 40, 807250),
            datetime(2020, 10, 11, 8, 16, 40, 828308),
            datetime(2020, 10, 11, 13, 35, 59, 856847),
            datetime(2020, 10, 11, 13, 35, 59, 873173),
            datetime(2020, 10, 11, 19, 10, 53, 267398),
            datetime(2020, 10, 11, 19, 10, 53, 283267),
            datetime(2020, 10, 12, 7, 1, 58, 347961),
            datetime(2020, 10, 12, 7, 1, 58, 363723),
            datetime(2020, 10, 12, 7, 3, 58, 147691),
            datetime(2020, 10, 12, 7, 3, 58, 163525),
            datetime(2020, 10, 12, 8, 52, 59, 762773),
            datetime(2020, 10, 12, 8, 52, 59, 774941),
            datetime(2020, 10, 12, 8, 55, 23, 547260),
            datetime(2020, 10, 12, 8, 55, 23, 556180),
            datetime(2020, 10, 12, 19, 10, 56, 622353),
            datetime(2020, 10, 12, 19, 10, 56, 646231),
            datetime(2020, 10, 13, 7, 2, 45, 437514),
            datetime(2020, 10, 13, 7, 2, 45, 453417),
            datetime(2020, 10, 13, 19, 22, 23, 953137),
            datetime(2020, 10, 13, 19, 22, 23, 956755),
            datetime(2020, 10, 13, 20, 50, 35, 47622),
            datetime(2020, 10, 13, 20, 50, 35, 61813),
            datetime(2020, 10, 13, 22, 41, 53, 685372),
            datetime(2020, 10, 13, 22, 41, 53, 701048),
            datetime(2020, 10, 14, 8, 18, 56, 806400),
            datetime(2020, 10, 14, 8, 18, 59, 31178),
            datetime(2020, 10, 14, 8, 39, 51, 310347),
            datetime(2020, 10, 14, 8, 39, 51, 326525),
            datetime(2020, 10, 14, 9, 48, 12, 690673),
            datetime(2020, 10, 14, 9, 48, 12, 706435),
            datetime(2020, 10, 14, 9, 57, 2, 59583),
            datetime(2020, 10, 14, 9, 57, 2, 72604),
            datetime(2020, 10, 14, 9, 57, 57, 213193),
            datetime(2020, 10, 14, 9, 57, 57, 230327),
        ]

        values220 = [
            10.6999430312505,
            10.699979249418897,
            10.699989622852124,
            10.67654020042446,
            9.770055309041588,
            9.793692412032708,
            10.709944052743694,
            10.709972026207458,
            10.709986012939506,
            10.709993006305572,
            10.709996502988615,
            10.70999825133014,
            10.7099991255009,
            10.709999562586281,
            10.709999781128973,
            10.686298700721027,
            9.77005590174055,
            9.770027949616914,
            9.770013973555422,
            9.793692331297219,
            10.709944052738756,
            10.709972026204987,
            10.709986012938272,
            10.686298673830388,
            9.770055901738909,
            9.793692413190362,
            10.709944052743765,
            10.709972026371666,
            10.70998601318578,
            10.709993006428709,
            10.709996503050183,
            10.709998251360922,
            10.709999125516292,
            10.686298699440549,
            9.770055901740472,
            9.770055901740472,
            10.709944052743765,
            10.674551039870032,
            9.33804076038104,
            9.33802038007131,
            9.338010189916668,
            9.338005094839403,
            9.338002547300784,
            9.37342598109211,
            10.709959185874963,
            10.709979592937366,
            10.709989796468655,
            10.674551128973944,
            9.338040760145944,
            9.373426056057786,
            10.70995918620558,
            10.709979593102673,
            10.709989796551309,
        ]

        times280 = [
            datetime(2020, 10, 1, 10, 7, 28, 959441),
            datetime(2020, 10, 8, 12, 45, 6, 319491),
            datetime(2020, 10, 8, 12, 46, 35, 772712),
            datetime(2020, 10, 9, 19, 28, 22, 560535),
            datetime(2020, 10, 9, 19, 28, 22, 574701),
            datetime(2020, 10, 10, 7, 2, 54, 736911),
            datetime(2020, 10, 10, 7, 2, 54, 749977),
            datetime(2020, 10, 10, 11, 28, 31, 543509),
            datetime(2020, 10, 10, 11, 28, 31, 558468),
            datetime(2020, 10, 10, 11, 30, 11, 597557),
            datetime(2020, 10, 10, 11, 30, 11, 611438),
            datetime(2020, 10, 10, 12, 12, 27, 536397),
            datetime(2020, 10, 10, 12, 12, 27, 548782),
            datetime(2020, 10, 10, 12, 14, 17, 51767),
            datetime(2020, 10, 10, 12, 14, 17, 64163),
            datetime(2020, 10, 10, 19, 13, 50, 99),
            datetime(2020, 10, 10, 19, 13, 50, 20908),
            datetime(2020, 10, 10, 21, 17, 50, 746146),
            datetime(2020, 10, 10, 21, 17, 50, 759728),
            datetime(2020, 10, 11, 8, 16, 40, 807748),
            datetime(2020, 10, 11, 8, 16, 40, 828411),
            datetime(2020, 10, 11, 13, 35, 59, 857087),
            datetime(2020, 10, 11, 13, 35, 59, 873564),
            datetime(2020, 10, 11, 19, 10, 53, 267692),
            datetime(2020, 10, 11, 19, 10, 53, 283628),
            datetime(2020, 10, 12, 7, 1, 58, 348162),
            datetime(2020, 10, 12, 7, 1, 58, 363988),
            datetime(2020, 10, 12, 7, 3, 58, 147805),
            datetime(2020, 10, 12, 7, 3, 58, 163655),
            datetime(2020, 10, 12, 8, 52, 59, 763044),
            datetime(2020, 10, 12, 8, 52, 59, 774990),
            datetime(2020, 10, 12, 8, 55, 23, 547646),
            datetime(2020, 10, 12, 8, 55, 23, 556382),
            datetime(2020, 10, 12, 19, 10, 56, 623227),
            datetime(2020, 10, 12, 19, 10, 56, 646271),
            datetime(2020, 10, 13, 7, 2, 45, 437934),
            datetime(2020, 10, 13, 7, 2, 45, 453955),
            datetime(2020, 10, 13, 19, 22, 23, 953208),
            datetime(2020, 10, 13, 19, 22, 23, 957532),
            datetime(2020, 10, 13, 20, 50, 35, 48059),
            datetime(2020, 10, 13, 20, 50, 35, 62517),
            datetime(2020, 10, 13, 22, 41, 53, 685774),
            datetime(2020, 10, 13, 22, 41, 53, 701386),
            datetime(2020, 10, 14, 8, 18, 53, 995482),
            datetime(2020, 10, 14, 8, 18, 59, 31493),
            datetime(2020, 10, 14, 8, 39, 51, 310522),
            datetime(2020, 10, 14, 8, 39, 51, 326574),
            datetime(2020, 10, 14, 9, 48, 12, 691229),
            datetime(2020, 10, 14, 9, 48, 12, 706604),
            datetime(2020, 10, 14, 9, 57, 2, 59711),
            datetime(2020, 10, 14, 9, 57, 2, 72728),
            datetime(2020, 10, 14, 9, 57, 57, 213338),
            datetime(2020, 10, 14, 9, 57, 57, 230453),
        ]

        values280 = [
            10.69994225003475,
            10.699979211981582,
            10.69998960449891,
            10.687312044187102,
            9.770055963611634,
            9.770055963611634,
            10.709943385515894,
            10.709971693095635,
            10.709985846885697,
            10.709992923780774,
            10.709996462228325,
            10.709998231452104,
            10.709999116063994,
            10.709999558369939,
            10.70999977952291,
            10.697186720340568,
            9.77005656216933,
            9.770028279242446,
            9.770014137779373,
            9.782807864659569,
            10.709943385505909,
            10.709971693090642,
            10.7099858468832,
            10.69718666591663,
            9.770056562166012,
            9.782808030382437,
            10.709943385516041,
            10.709971692757772,
            10.709985846378824,
            10.709992923527338,
            10.709996462101607,
            10.709998231388743,
            10.709999116032312,
            10.697186717748826,
            9.770056562169172,
            9.770056562169172,
            10.70997130324195,
            10.70997130324195,
            9.338041239945333,
            9.338020621211182,
            9.338010311844357,
            9.338005157161007,
            9.338002579819346,
            9.357603822477754,
            10.709958700542789,
            10.709979350271261,
            10.7099896751356,
            10.690381982944237,
            9.33804124242413,
            9.33804124242413,
            10.709958699869212,
            10.709979349934471,
            10.7099896749672,
        ]

        self.expectedNoDeltaResult = ArchiverData(
            timeStamps={"BEND:LTUH:280:BDES": times280, "BEND:LTUH:220:BDES": times220},
            values={"BEND:LTUH:280:BDES": values280, "BEND:LTUH:220:BDES": values220},
        )

    # Utility class to be used for mocking a response to requests.post
    class MockResponse(object):
        def __init__(self):
            self.text = ""

    @mock.patch("requests.post")
    @mock.patch("json.loads")
    def testGetDataAtTimeMockedData(self, mockedLoads, mockedPost):
        mockedLoads.return_value = self.jsonDict
        mockedPost.return_value = self.MockResponse()

        self.assertEqual(
            self.archiver.getDataAtTime(self.pvList, self.time),
            self.expectedSingleResult,
        )

    def testGetDataAtTime(self):
        try:
            self.assertEqual(
                self.archiver.getDataAtTime(self.pvList, self.time),
                self.expectedSingleResult,
            )
        except requests.exceptions.Timeout:
            self.skipTest("testGetDataAtTime connection timed out")

    def testGetDataWithTimeInterval(self):
        try:
            self.assertEqual(
                self.archiver.getDataWithTimeInterval(
                    self.pvList,
                    self.time - timedelta(days=10),
                    self.time,
                    timedelta(days=1),
                ),
                self.expectedDeltaResult,
            )

        except requests.exceptions.Timeout:
            self.skipTest("testGetDataWithTimeInterval connection timed out")

    def testGetDataWithTimeIntervalMocked(self):
        def side_effect(pvList, time):
            self.assertEqual(pvList, self.pvList)

            if time == datetime(2020, 10, 4, 11, 56, 30, 10):
                return ArchiverData(
                    timeStamps=[datetime(2020, 10, 4, 11, 56, 30, 10)],
                    values={
                        "BEND:LTUH:280:BDES": [10.69994225003475],
                        "BEND:LTUH:220:BDES": [10.6999430312505],
                    },
                )
            elif time == datetime(2020, 10, 5, 11, 56, 30, 10):
                return ArchiverData(
                    timeStamps=[datetime(2020, 10, 5, 11, 56, 30, 10)],
                    values={
                        "BEND:LTUH:280:BDES": [10.69994225003475],
                        "BEND:LTUH:220:BDES": [10.6999430312505],
                    },
                )
            elif time == datetime(2020, 10, 6, 11, 56, 30, 10):
                return ArchiverData(
                    timeStamps=[datetime(2020, 10, 6, 11, 56, 30, 10)],
                    values={
                        "BEND:LTUH:280:BDES": [10.69994225003475],
                        "BEND:LTUH:220:BDES": [10.6999430312505],
                    },
                )
            elif time == datetime(2020, 10, 7, 11, 56, 30, 10):
                return ArchiverData(
                    timeStamps=[datetime(2020, 10, 7, 11, 56, 30, 10)],
                    values={
                        "BEND:LTUH:280:BDES": [10.69994225003475],
                        "BEND:LTUH:220:BDES": [10.6999430312505],
                    },
                )
            elif time == datetime(2020, 10, 8, 11, 56, 30, 10):
                return ArchiverData(
                    timeStamps=[datetime(2020, 10, 8, 11, 56, 30, 10)],
                    values={
                        "BEND:LTUH:280:BDES": [10.69994225003475],
                        "BEND:LTUH:220:BDES": [10.6999430312505],
                    },
                )
            elif time == datetime(2020, 10, 9, 11, 56, 30, 10):
                return ArchiverData(
                    timeStamps=[datetime(2020, 10, 9, 11, 56, 30, 10)],
                    values={
                        "BEND:LTUH:280:BDES": [10.69998960449891],
                        "BEND:LTUH:220:BDES": [10.699989622852124],
                    },
                )
            elif time == datetime(2020, 10, 10, 11, 56, 30, 10):
                return ArchiverData(
                    timeStamps=[datetime(2020, 10, 10, 11, 56, 30, 10)],
                    values={
                        "BEND:LTUH:280:BDES": [10.709996462228325],
                        "BEND:LTUH:220:BDES": [10.709996502988615],
                    },
                )
            elif time == datetime(2020, 10, 11, 11, 56, 30, 10):
                return ArchiverData(
                    timeStamps=[datetime(2020, 10, 11, 11, 56, 30, 10)],
                    values={
                        "BEND:LTUH:280:BDES": [10.709943385505909],
                        "BEND:LTUH:220:BDES": [10.709944052738756],
                    },
                )
            elif time == datetime(2020, 10, 12, 11, 56, 30, 10):
                return ArchiverData(
                    timeStamps=[datetime(2020, 10, 12, 11, 56, 30, 10)],
                    values={
                        "BEND:LTUH:280:BDES": [10.709999116032312],
                        "BEND:LTUH:220:BDES": [10.709999125516292],
                    },
                )
            elif time == datetime(2020, 10, 13, 11, 56, 30, 10):
                return ArchiverData(
                    timeStamps=[datetime(2020, 10, 13, 11, 56, 30, 10)],
                    values={
                        "BEND:LTUH:280:BDES": [10.70997130324195],
                        "BEND:LTUH:220:BDES": [10.709944052743765],
                    },
                )
            else:
                raise Exception("Unexpected datetime")

        self.archiver.getDataAtTime = mock.MagicMock(name="getDataAtTime")
        self.archiver.getDataAtTime.side_effect = side_effect

        self.assertEqual(
            self.archiver.getDataWithTimeInterval(
                self.pvList,
                self.time - timedelta(days=10),
                self.time,
                timedelta(days=1),
            ),
            self.expectedDeltaResult,
        )

    def testGetValuesOverTimeRange(self):
        try:
            self.assertEqual(
                self.archiver.getValuesOverTimeRange(
                    self.pvList, self.time - timedelta(days=10), self.time
                ),
                self.expectedNoDeltaResult,
            )

        except requests.exceptions.Timeout:
            self.skipTest("testGetValuesOverTimeRange connection timed out")


if __name__ == "__main__":
    test()
