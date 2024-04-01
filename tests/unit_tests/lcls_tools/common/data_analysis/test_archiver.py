import unittest
from datetime import datetime

import requests

from lcls_tools.common.data_analysis.archiver import Archiver, ArchiverValue

# Python compatibility. The first branch is for 3, the second for 2
try:
    import unittest.mock as mock
except ImportError:
    import mock


class TestArchiver(unittest.TestCase):
    def setUp(self) -> None:
        self.archiver = Archiver("lcls")
        self.time = datetime(
            year=2024, month=4, day=1, hour=14, minute=56, second=30, microsecond=10
        )
        self.pv_lst = ["ACCL:L0B:0110:DFBEST", "ACCL:L0B:0110:AACTMEAN"]

        self.json_data = {
            "ACCL:L0B:0110:AACTMEAN": {
                "nanos": 706573951,
                "secs": 1712008589,
                "severity": 0,
                "status": 0,
                "val": 6.509116634443234,
            },
            "ACCL:L0B:0110:DFBEST": {
                "nanos": 351862628,
                "secs": 1712008589,
                "severity": 0,
                "status": 0,
                "val": -0.5760000000000001,
            },
        }

        self.single_result = {
            "ACCL:L0B:0110:DFBEST": ArchiverValue(
                secs=1712008589,
                val=-0.5760000000000001,
                nanos=351862628,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            "ACCL:L0B:0110:AACTMEAN": ArchiverValue(
                secs=1712008589,
                val=6.509116634443234,
                nanos=706573951,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
        }

        self.expected_single_result = {
            "ACCL:L0B:0110:DFBEST": ArchiverValue(
                secs=1712008589,
                val=-0.5760000000000001,
                nanos=351862628,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            "ACCL:L0B:0110:AACTMEAN": ArchiverValue(
                secs=1712008589,
                val=6.509116634443234,
                nanos=706573951,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
        }
        return super().setUp()

    def tearDown(self) -> None:
        return super().tearDown()

    # Utility class to be used for mocking a response to requests.post
    class MockResponse(object):
        def __init__(self):
            self.text = ""

    @mock.patch("requests.post")
    @mock.patch("json.loads")
    def test_get_data_at_time_mocked_data(self, mockedLoads, mockedPost):
        mockedLoads.return_value = self.json_data
        mockedPost.return_value = self.MockResponse()

        self.assertEqual(
            self.archiver.get_data_at_time(self.pv_lst, self.time),
            self.expected_single_result,
        )

    def test_get_data_at_time(self):
        try:
            self.assertEqual(
                self.archiver.get_data_at_time(self.pv_lst, self.time),
                self.expected_single_result,
            )
        except requests.exceptions.Timeout:
            self.skipTest("test_get_data_at_time connection timed out")
        except requests.exceptions.ConnectionError:
            self.skipTest(
                "test_get_data_at_time connection unsuccessful as network was unreachable."
            )

    def test_get_data_no_microseconds(self):
        time_no_miscroseconds = datetime(
            year=2024, month=3, day=25, hour=14, minute=7, second=20
        )

        pv = "ACCL:L0B:0110:AACTMEAN"

        expected_result = {
            "ACCL:L0B:0110:AACTMEAN": ArchiverValue(
                secs=1711400839,
                val=0.0004232343591732812,
                nanos=299095469,
                severity=2,
                status=5,
                fields=None,
                _timestamp=None,
            )
        }

        try:
            self.assertEqual(
                self.archiver.get_data_at_time(
                    pv_list=[pv], time_requested=time_no_miscroseconds
                ),
                expected_result,
            )

        except requests.exceptions.Timeout:
            self.skipTest("test_get_data_no_microseconds connection timed out")
        except requests.exceptions.ConnectionError:
            self.skipTest(
                "test_get_data_no_microseconds connection unsuccessful as network was unreachable."
            )

    # def test_get_data_with_time_interval(self):
    #     try:
    #         self.assertEqual(
    #             self.archiver.get_data_with_time_interval(
    #                 self.pv_lst,
    #                 self.time - timedelta(days=10),
    #                 self.time,
    #                 timedelta(days=1),
    #             ),
    #             self.expectedDeltaResult,
    #         )
    #
    #     except requests.exceptions.Timeout:
    #         self.skipTest("test_get_data_with_time_interval connection timed out")
    #     except requests.exceptions.ConnectionError:
    #         self.skipTest(
    #             "test_get_data_with_time_interval connection unsuccessful as network was unreachable."
    #         )

    # def test_get_data_with_time_interval_mocked(self):
    #     def side_effect(pvList, time):
    #         self.assertEqual(pvList, self.pv_lst)
    #
    #         if time == datetime(2020, 10, 4, 11, 56, 30, 10):
    #             return ArchiverData(
    #                 timeStamps=[datetime(2020, 10, 4, 11, 56, 30, 10)],
    #                 values={
    #                     "BEND:LTUH:280:BDES": [10.69994225003475],
    #                     "BEND:LTUH:220:BDES": [10.6999430312505],
    #                 },
    #             )
    #         elif time == datetime(2020, 10, 5, 11, 56, 30, 10):
    #             return ArchiverData(
    #                 timeStamps=[datetime(2020, 10, 5, 11, 56, 30, 10)],
    #                 values={
    #                     "BEND:LTUH:280:BDES": [10.69994225003475],
    #                     "BEND:LTUH:220:BDES": [10.6999430312505],
    #                 },
    #             )
    #         elif time == datetime(2020, 10, 6, 11, 56, 30, 10):
    #             return ArchiverData(
    #                 timeStamps=[datetime(2020, 10, 6, 11, 56, 30, 10)],
    #                 values={
    #                     "BEND:LTUH:280:BDES": [10.69994225003475],
    #                     "BEND:LTUH:220:BDES": [10.6999430312505],
    #                 },
    #             )
    #         elif time == datetime(2020, 10, 7, 11, 56, 30, 10):
    #             return ArchiverData(
    #                 timeStamps=[datetime(2020, 10, 7, 11, 56, 30, 10)],
    #                 values={
    #                     "BEND:LTUH:280:BDES": [10.69994225003475],
    #                     "BEND:LTUH:220:BDES": [10.6999430312505],
    #                 },
    #             )
    #         elif time == datetime(2020, 10, 8, 11, 56, 30, 10):
    #             return ArchiverData(
    #                 timeStamps=[datetime(2020, 10, 8, 11, 56, 30, 10)],
    #                 values={
    #                     "BEND:LTUH:280:BDES": [10.69994225003475],
    #                     "BEND:LTUH:220:BDES": [10.6999430312505],
    #                 },
    #             )
    #         elif time == datetime(2020, 10, 9, 11, 56, 30, 10):
    #             return ArchiverData(
    #                 timeStamps=[datetime(2020, 10, 9, 11, 56, 30, 10)],
    #                 values={
    #                     "BEND:LTUH:280:BDES": [10.69998960449891],
    #                     "BEND:LTUH:220:BDES": [10.699989622852124],
    #                 },
    #             )
    #         elif time == datetime(2020, 10, 10, 11, 56, 30, 10):
    #             return ArchiverData(
    #                 timeStamps=[datetime(2020, 10, 10, 11, 56, 30, 10)],
    #                 values={
    #                     "BEND:LTUH:280:BDES": [10.709996462228325],
    #                     "BEND:LTUH:220:BDES": [10.709996502988615],
    #                 },
    #             )
    #         elif time == datetime(2020, 10, 11, 11, 56, 30, 10):
    #             return ArchiverData(
    #                 timeStamps=[datetime(2020, 10, 11, 11, 56, 30, 10)],
    #                 values={
    #                     "BEND:LTUH:280:BDES": [10.709943385505909],
    #                     "BEND:LTUH:220:BDES": [10.709944052738756],
    #                 },
    #             )
    #         elif time == datetime(2020, 10, 12, 11, 56, 30, 10):
    #             return ArchiverData(
    #                 timeStamps=[datetime(2020, 10, 12, 11, 56, 30, 10)],
    #                 values={
    #                     "BEND:LTUH:280:BDES": [10.709999116032312],
    #                     "BEND:LTUH:220:BDES": [10.709999125516292],
    #                 },
    #             )
    #         elif time == datetime(2020, 10, 13, 11, 56, 30, 10):
    #             return ArchiverData(
    #                 timeStamps=[datetime(2020, 10, 13, 11, 56, 30, 10)],
    #                 values={
    #                     "BEND:LTUH:280:BDES": [10.70997130324195],
    #                     "BEND:LTUH:220:BDES": [10.709944052743765],
    #                 },
    #             )
    #         else:
    #             raise Exception("Unexpected datetime")
    #
    #     self.archiver.getDataAtTime = mock.MagicMock(name="getDataAtTime")
    #     self.archiver.getDataAtTime.side_effect = side_effect
    #
    #     self.assertEqual(
    #         self.archiver.getDataWithTimeInterval(
    #             self.pvList,
    #             self.time - timedelta(days=10),
    #             self.time,
    #             timedelta(days=1),
    #         ),
    #         self.expectedDeltaResult,
    #     )

    # def test_get_values_over_time_range_without_timedelta(self):
    #     try:
    #         self.assertEqual(
    #             self.archiver.get_values_over_time_range(
    #                 self.pv_lst, self.time - timedelta(days=10), self.time
    #             ),
    #             self.expectedNoDeltaResult,
    #         )
    #
    #     except requests.exceptions.Timeout:
    #         self.skipTest("test_get_values_over_time_range connection timed out")
    #     except requests.exceptions.ConnectionError:
    #         self.skipTest(
    #             "test_get_values_over_time_range connection unsuccessful as network was unreachable."
    #         )

    # def test_get_values_over_time_range_with_timedelta(self):
    #     try:
    #         self.assertEqual(
    #             self.archiver.get_values_over_time_range(
    #                 self.pv_lst,
    #                 self.time - timedelta(days=10),
    #                 self.time,
    #                 timedelta(-1),
    #             ),
    #             self.expectedNoDeltaResult,
    #         )
    #
    #     except requests.exceptions.Timeout:
    #         self.skipTest("test_get_values_over_time_range connection timed out")
    #     except requests.exceptions.ConnectionError:
    #         self.skipTest(
    #             "test_get_values_over_time_range connection unsuccessful as network was unreachable."
    #         )
