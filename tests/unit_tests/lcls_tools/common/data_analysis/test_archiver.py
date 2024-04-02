import unittest
from datetime import datetime, timedelta

import requests

from lcls_tools.common.data_analysis.archiver import (
    ArchiveDataHandler,
    Archiver,
    ArchiverValue,
)

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

        dfbest_lst = [
            ArchiverValue(
                secs=1711144589,
                val=-0.10400000000000001,
                nanos=643901554,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711230989,
                val=-1.1280000000000001,
                nanos=644712314,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711317389,
                val=-1.712,
                nanos=650207766,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711403789,
                val=0.0,
                nanos=652453946,
                severity=3,
                status=14,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711490181,
                val=0.0,
                nanos=644099825,
                severity=3,
                status=14,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711576583,
                val=0.0,
                nanos=335606946,
                severity=3,
                status=14,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711662980,
                val=0.0,
                nanos=335472655,
                severity=3,
                status=14,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711749389,
                val=-0.004,
                nanos=339083194,
                severity=3,
                status=14,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711835789,
                val=-1.068,
                nanos=347603983,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711922189,
                val=-1.592,
                nanos=339947228,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
        ]
        aactmean_lst = [
            ArchiverValue(
                secs=1711144589,
                val=6.5092583877407435,
                nanos=814986356,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711230989,
                val=6.50903783824157,
                nanos=45399642,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711317388,
                val=6.509005035059151,
                nanos=888839911,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711403789,
                val=0.0014643136084407868,
                nanos=693785347,
                severity=2,
                status=5,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711490189,
                val=0.0004538000381352912,
                nanos=828662425,
                severity=2,
                status=5,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711576589,
                val=0.00041344532175155213,
                nanos=399083384,
                severity=2,
                status=5,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711662989,
                val=0.00040902722895514007,
                nanos=228827866,
                severity=2,
                status=5,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711749389,
                val=0.00042876622143185557,
                nanos=928502917,
                severity=2,
                status=5,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711835789,
                val=6.509181480616865,
                nanos=284106860,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711922189,
                val=6.509128665496809,
                nanos=98839769,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
        ]
        self.expected_time_delta_result = {
            "ACCL:L0B:0110:DFBEST": ArchiveDataHandler(value_list=dfbest_lst),
            "ACCL:L0B:0110:AACTMEAN": ArchiveDataHandler(value_list=aactmean_lst),
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

    def test_get_data_with_time_interval(self):
        try:
            result = self.archiver.get_data_with_time_interval(
                self.pv_lst,
                self.time - timedelta(days=10),
                self.time,
                timedelta(days=1),
            )

            self.assertEqual(
                result,
                self.expected_time_delta_result,
            )

        except requests.exceptions.Timeout:
            self.skipTest("test_get_data_with_time_interval connection timed out")
        except requests.exceptions.ConnectionError:
            self.skipTest(
                "test_get_data_with_time_interval connection unsuccessful as network was unreachable."
            )

    def test_get_data_with_time_interval_mocked(self):
        def side_effect(pv_list, time):
            self.assertEqual(pv_list, self.pv_lst)

            times = []

            for delta in range(0, 11):
                times.append(self.time - timedelta(days=delta))

            time_map = {
                "2024-04-01 14:56:30.000010": {
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
                },
                "2024-03-31 14:56:30.000010": {
                    "ACCL:L0B:0110:DFBEST": ArchiverValue(
                        secs=1711922189,
                        val=-1.592,
                        nanos=339947228,
                        severity=0,
                        status=0,
                        fields=None,
                        _timestamp=None,
                    ),
                    "ACCL:L0B:0110:AACTMEAN": ArchiverValue(
                        secs=1711922189,
                        val=6.509128665496809,
                        nanos=98839769,
                        severity=0,
                        status=0,
                        fields=None,
                        _timestamp=None,
                    ),
                },
                "2024-03-30 14:56:30.000010": {
                    "ACCL:L0B:0110:DFBEST": ArchiverValue(
                        secs=1711835789,
                        val=-1.068,
                        nanos=347603983,
                        severity=0,
                        status=0,
                        fields=None,
                        _timestamp=None,
                    ),
                    "ACCL:L0B:0110:AACTMEAN": ArchiverValue(
                        secs=1711835789,
                        val=6.509181480616865,
                        nanos=284106860,
                        severity=0,
                        status=0,
                        fields=None,
                        _timestamp=None,
                    ),
                },
                "2024-03-29 14:56:30.000010": {
                    "ACCL:L0B:0110:DFBEST": ArchiverValue(
                        secs=1711749389,
                        val=-0.004,
                        nanos=339083194,
                        severity=3,
                        status=14,
                        fields=None,
                        _timestamp=None,
                    ),
                    "ACCL:L0B:0110:AACTMEAN": ArchiverValue(
                        secs=1711749389,
                        val=0.00042876622143185557,
                        nanos=928502917,
                        severity=2,
                        status=5,
                        fields=None,
                        _timestamp=None,
                    ),
                },
                "2024-03-28 14:56:30.000010": {
                    "ACCL:L0B:0110:DFBEST": ArchiverValue(
                        secs=1711662980,
                        val=0.0,
                        nanos=335472655,
                        severity=3,
                        status=14,
                        fields=None,
                        _timestamp=None,
                    ),
                    "ACCL:L0B:0110:AACTMEAN": ArchiverValue(
                        secs=1711662989,
                        val=0.00040902722895514007,
                        nanos=228827866,
                        severity=2,
                        status=5,
                        fields=None,
                        _timestamp=None,
                    ),
                },
                "2024-03-27 14:56:30.000010": {
                    "ACCL:L0B:0110:DFBEST": ArchiverValue(
                        secs=1711576583,
                        val=0.0,
                        nanos=335606946,
                        severity=3,
                        status=14,
                        fields=None,
                        _timestamp=None,
                    ),
                    "ACCL:L0B:0110:AACTMEAN": ArchiverValue(
                        secs=1711576589,
                        val=0.00041344532175155213,
                        nanos=399083384,
                        severity=2,
                        status=5,
                        fields=None,
                        _timestamp=None,
                    ),
                },
                "2024-03-26 14:56:30.000010": {
                    "ACCL:L0B:0110:DFBEST": ArchiverValue(
                        secs=1711490181,
                        val=0.0,
                        nanos=644099825,
                        severity=3,
                        status=14,
                        fields=None,
                        _timestamp=None,
                    ),
                    "ACCL:L0B:0110:AACTMEAN": ArchiverValue(
                        secs=1711490189,
                        val=0.0004538000381352912,
                        nanos=828662425,
                        severity=2,
                        status=5,
                        fields=None,
                        _timestamp=None,
                    ),
                },
                "2024-03-25 14:56:30.000010": {
                    "ACCL:L0B:0110:DFBEST": ArchiverValue(
                        secs=1711403789,
                        val=0.0,
                        nanos=652453946,
                        severity=3,
                        status=14,
                        fields=None,
                        _timestamp=None,
                    ),
                    "ACCL:L0B:0110:AACTMEAN": ArchiverValue(
                        secs=1711403789,
                        val=0.0014643136084407868,
                        nanos=693785347,
                        severity=2,
                        status=5,
                        fields=None,
                        _timestamp=None,
                    ),
                },
                "2024-03-24 14:56:30.000010": {
                    "ACCL:L0B:0110:DFBEST": ArchiverValue(
                        secs=1711317389,
                        val=-1.712,
                        nanos=650207766,
                        severity=0,
                        status=0,
                        fields=None,
                        _timestamp=None,
                    ),
                    "ACCL:L0B:0110:AACTMEAN": ArchiverValue(
                        secs=1711317388,
                        val=6.509005035059151,
                        nanos=888839911,
                        severity=0,
                        status=0,
                        fields=None,
                        _timestamp=None,
                    ),
                },
                "2024-03-23 14:56:30.000010": {
                    "ACCL:L0B:0110:DFBEST": ArchiverValue(
                        secs=1711230989,
                        val=-1.1280000000000001,
                        nanos=644712314,
                        severity=0,
                        status=0,
                        fields=None,
                        _timestamp=None,
                    ),
                    "ACCL:L0B:0110:AACTMEAN": ArchiverValue(
                        secs=1711230989,
                        val=6.50903783824157,
                        nanos=45399642,
                        severity=0,
                        status=0,
                        fields=None,
                        _timestamp=None,
                    ),
                },
                "2024-03-22 14:56:30.000010": {
                    "ACCL:L0B:0110:DFBEST": ArchiverValue(
                        secs=1711144589,
                        val=-0.10400000000000001,
                        nanos=643901554,
                        severity=0,
                        status=0,
                        fields=None,
                        _timestamp=None,
                    ),
                    "ACCL:L0B:0110:AACTMEAN": ArchiverValue(
                        secs=1711144589,
                        val=6.5092583877407435,
                        nanos=814986356,
                        severity=0,
                        status=0,
                        fields=None,
                        _timestamp=None,
                    ),
                },
            }

            return time_map[str(time)]

        self.archiver.get_data_at_time = mock.MagicMock(name="get_data_at_time")
        self.archiver.get_data_at_time.side_effect = side_effect

        self.assertEqual(
            self.archiver.get_data_with_time_interval(
                self.pv_lst,
                self.time - timedelta(days=10),
                self.time,
                timedelta(days=1),
            ),
            self.expected_time_delta_result,
        )

    def test_get_values_over_time_range_without_timedelta(self):
        try:
            self.assertEqual(
                self.archiver.get_values_over_time_range(
                    self.pv_lst, self.time - timedelta(days=10), self.time
                ),
                self.expectedNoDeltaResult,
            )

        except requests.exceptions.Timeout:
            self.skipTest("test_get_values_over_time_range connection timed out")
        except requests.exceptions.ConnectionError:
            self.skipTest(
                "test_get_values_over_time_range connection unsuccessful as network was unreachable."
            )

    def test_get_values_over_time_range_with_timedelta(self):
        dfbest_lst = [
            ArchiverValue(
                secs=1711144579,
                val=-0.064,
                nanos=646824500,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711144580,
                val=-1.428,
                nanos=651779421,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711144581,
                val=-1.248,
                nanos=644160331,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711144582,
                val=-0.436,
                nanos=654723549,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711144583,
                val=1.472,
                nanos=645089755,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711144584,
                val=-1.172,
                nanos=645400162,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711144585,
                val=-0.632,
                nanos=657752634,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711144586,
                val=1.512,
                nanos=645096219,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711144587,
                val=1.364,
                nanos=644934776,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711144588,
                val=0.392,
                nanos=644432381,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711144589,
                val=-0.10400000000000001,
                nanos=643901554,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
        ]

        aactmean_lst = [
            ArchiverValue(
                secs=1711144579,
                val=6.509255890878457,
                nanos=987746610,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711144581,
                val=6.509258049946067,
                nanos=98389596,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711144582,
                val=6.509257530421206,
                nanos=114770550,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711144583,
                val=6.509256739492492,
                nanos=226437225,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711144584,
                val=6.509256903062449,
                nanos=338140932,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711144585,
                val=6.509256608192711,
                nanos=452886090,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711144586,
                val=6.509255910803729,
                nanos=570835181,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711144587,
                val=6.509256441099705,
                nanos=686557679,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711144588,
                val=6.5092569579434,
                nanos=703651446,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
            ArchiverValue(
                secs=1711144589,
                val=6.5092583877407435,
                nanos=814986356,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
            ),
        ]

        expected_result = {
            "ACCL:L0B:0110:DFBEST": ArchiveDataHandler(value_list=dfbest_lst),
            "ACCL:L0B:0110:AACTMEAN": ArchiveDataHandler(value_list=aactmean_lst),
        }

        try:
            self.assertEqual(
                self.archiver.get_values_over_time_range(
                    self.pv_lst,
                    self.time - timedelta(seconds=10),
                    self.time,
                ),
                expected_result,
            )

        except requests.exceptions.Timeout:
            self.skipTest("test_get_values_over_time_range connection timed out")
        except requests.exceptions.ConnectionError:
            self.skipTest(
                "test_get_values_over_time_range connection unsuccessful as network was unreachable."
            )
