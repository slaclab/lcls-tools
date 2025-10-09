import unittest
import unittest.mock as mock
from datetime import datetime, timedelta

import requests
from typing import DefaultDict
from collections import defaultdict

from lcls_tools.common.data.archiver import (
    ArchiveDataHandler,
    ArchiverValue,
    get_data_at_time,
    get_data_with_time_interval,
    get_values_over_time_range,
)

AACT_META = {"DBRType": "DBR_SCALAR_DOUBLE"}
DF_META = {"DBRType": "DBR_SCALAR_DOUBLE"}


class TestArchiver(unittest.TestCase):
    def setUp(self) -> None:
        self.maxDiff = None
        self.time = datetime(
            year=2024, month=4, day=1, hour=14, minute=56, second=30, microsecond=10
        )
        self.pv_lst = ["ACCL:L0B:0110:DFBEST", "ACCL:L0B:0110:AACTMEAN"]

        self.json_data = {
            "ACCL:L0B:0110:AACTMEAN": {
                "meta": AACT_META,
                "nanos": 706573951,
                "secs": 1712008589,
                "severity": 0,
                "status": 0,
                "val": 6.509116634443234,
                "fields": {},
            },
            "ACCL:L0B:0110:DFBEST": {
                "meta": DF_META,
                "nanos": 351862628,
                "secs": 1712008589,
                "severity": 0,
                "status": 0,
                "val": -0.5760000000000001,
                "fields": {},
            },
        }

        self.single_result = {
            "ACCL:L0B:0110:DFBEST": ArchiverValue(
                secs=1712008589,
                val=-0.5760000000000001,
                nanos=351862628,
                severity=0,
                status=0,
                fields={},
                _timestamp=None,
            ),
            "ACCL:L0B:0110:AACTMEAN": ArchiverValue(
                secs=1712008589,
                val=6.509116634443234,
                nanos=706573951,
                severity=0,
                status=0,
                fields={},
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
                fields={},
                _timestamp=None,
                meta=DF_META,
            ),
            "ACCL:L0B:0110:AACTMEAN": ArchiverValue(
                secs=1712008589,
                val=6.509116634443234,
                nanos=706573951,
                severity=0,
                status=0,
                fields={},
                _timestamp=None,
                meta=AACT_META,
            ),
        }

        dfbest_lst = [
            ArchiverValue(
                meta=DF_META,
                secs=1711144589,
                val=-0.10400000000000001,
                nanos=643901554,
                severity=0,
                status=0,
                fields={},
                _timestamp=None,
            ),
            ArchiverValue(
                meta=DF_META,
                secs=1711230989,
                val=-1.1280000000000001,
                nanos=644712314,
                severity=0,
                status=0,
                fields={},
                _timestamp=None,
            ),
            ArchiverValue(
                meta=DF_META,
                secs=1711317389,
                val=-1.712,
                nanos=650207766,
                severity=0,
                status=0,
                fields={},
                _timestamp=None,
            ),
            ArchiverValue(
                meta=DF_META,
                secs=1711403789,
                val=0.0,
                nanos=652453946,
                severity=3,
                status=14,
                fields={},
                _timestamp=None,
            ),
            ArchiverValue(
                meta=DF_META,
                secs=1711490181,
                val=0.0,
                nanos=644099825,
                severity=3,
                status=14,
                fields={},
                _timestamp=None,
            ),
            ArchiverValue(
                meta=DF_META,
                secs=1711576583,
                val=0.0,
                nanos=335606946,
                severity=3,
                status=14,
                fields={},
                _timestamp=None,
            ),
            ArchiverValue(
                meta=DF_META,
                secs=1711662980,
                val=0.0,
                nanos=335472655,
                severity=3,
                status=14,
                fields={},
                _timestamp=None,
            ),
            ArchiverValue(
                meta=DF_META,
                secs=1711749389,
                val=-0.004,
                nanos=339083194,
                severity=3,
                status=14,
                fields={},
                _timestamp=None,
            ),
            ArchiverValue(
                meta=DF_META,
                secs=1711835789,
                val=-1.068,
                nanos=347603983,
                severity=0,
                status=0,
                fields={},
                _timestamp=None,
            ),
            ArchiverValue(
                meta=DF_META,
                secs=1711922189,
                val=-1.592,
                nanos=339947228,
                severity=0,
                status=0,
                fields={},
                _timestamp=None,
            ),
        ]
        aactmean_lst = [
            ArchiverValue(
                meta=AACT_META,
                secs=1711144589,
                val=6.5092583877407435,
                nanos=814986356,
                severity=0,
                status=0,
                fields={},
                _timestamp=None,
            ),
            ArchiverValue(
                meta=AACT_META,
                secs=1711230989,
                val=6.50903783824157,
                nanos=45399642,
                severity=0,
                status=0,
                fields={},
                _timestamp=None,
            ),
            ArchiverValue(
                meta=AACT_META,
                secs=1711317388,
                val=6.509005035059151,
                nanos=888839911,
                severity=0,
                status=0,
                fields={},
                _timestamp=None,
            ),
            ArchiverValue(
                meta=AACT_META,
                secs=1711403789,
                val=0.0014643136084407868,
                nanos=693785347,
                severity=2,
                status=5,
                fields={},
                _timestamp=None,
            ),
            ArchiverValue(
                meta=AACT_META,
                secs=1711490189,
                val=0.0004538000381352912,
                nanos=828662425,
                severity=2,
                status=5,
                fields={},
                _timestamp=None,
            ),
            ArchiverValue(
                meta=AACT_META,
                secs=1711576589,
                val=0.00041344532175155213,
                nanos=399083384,
                severity=2,
                status=5,
                fields={},
                _timestamp=None,
            ),
            ArchiverValue(
                meta=AACT_META,
                secs=1711662989,
                val=0.00040902722895514007,
                nanos=228827866,
                severity=2,
                status=5,
                fields={},
                _timestamp=None,
            ),
            ArchiverValue(
                meta=AACT_META,
                secs=1711749389,
                val=0.00042876622143185557,
                nanos=928502917,
                severity=2,
                status=5,
                fields={},
                _timestamp=None,
            ),
            ArchiverValue(
                meta=AACT_META,
                secs=1711835789,
                val=6.509181480616865,
                nanos=284106860,
                severity=0,
                status=0,
                fields={},
                _timestamp=None,
            ),
            ArchiverValue(
                meta=AACT_META,
                secs=1711922189,
                val=6.509128665496809,
                nanos=98839769,
                severity=0,
                status=0,
                fields={},
                _timestamp=None,
            ),
        ]

        # Needed to make a DefaultDict[str, ArchiveDataHandler]
        self.expected_time_delta_result: DefaultDict[str, ArchiveDataHandler] = (
            defaultdict(ArchiveDataHandler)
        )
        self.expected_time_delta_result["ACCL:L0B:0110:DFBEST"] = ArchiveDataHandler(
            value_list=dfbest_lst
        )
        self.expected_time_delta_result["ACCL:L0B:0110:AACTMEAN"] = ArchiveDataHandler(
            value_list=aactmean_lst
        )

        return super().setUp()

    def tearDown(self) -> None:
        return super().tearDown()

    class MockResponse(object):
        """
        Utility class to be used for mocking a response to requests.post
        There should not be a need for an actual response, so this is a blank
        class for now
        """

        def __init__(self):
            self.text = ""

    @mock.patch("requests.post")
    @mock.patch("json.loads")
    def test_get_data_at_time_mocked_data(
        self, mocked_loads: mock.MagicMock, mocked_post: mock.MagicMock
    ):
        """
        We want requests.post to do nothing and json.loads to return a very
        specific archiver result
        @param mocked_loads: provided by the unit test as specific by @mock.patch
        @param mocked_post: provided by the unit test as specific by @mock.patch
        @return: None
        """
        mocked_loads.return_value = self.json_data
        mocked_post.return_value = self.MockResponse()

        self.assertEqual(
            get_data_at_time(self.pv_lst, self.time),
            self.expected_single_result,
        )

    def test_get_data_at_time(self):
        try:
            self.assertEqual(
                get_data_at_time(self.pv_lst, self.time),
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
                meta=AACT_META,
                secs=1711400839,
                val=0.0004232343591732812,
                nanos=299095469,
                severity=2,
                status=5,
                fields={},
                _timestamp=None,
            )
        }

        try:
            self.assertEqual(
                get_data_at_time(pv_list=[pv], time_requested=time_no_miscroseconds),
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
            actual_result = get_data_with_time_interval(
                self.pv_lst,
                self.time - timedelta(days=10),
                self.time,
                timedelta(days=1),
            )

            self.assertEqual(
                actual_result,
                self.expected_time_delta_result,
            )

        except requests.exceptions.Timeout:
            self.skipTest("test_get_data_with_time_interval connection timed out")
        except requests.exceptions.ConnectionError:
            self.skipTest(
                "test_get_data_with_time_interval connection unsuccessful as network was unreachable."
            )

    @mock.patch("lcls_tools.common.data.archiver.get_data_at_time")
    def test_get_data_with_time_interval_mocked(self, mocked_get_data: mock.MagicMock):
        """
        We want to overload the call to get_data_at_time that
        get_data_with_time_interval makes
        @param mocked_get_data: magic mock provided by this unit test as directed
                                by the @mock.patch decorator
        @return: None
        """

        def side_effect(pv_list, time_stamp):
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
                        fields={},
                        _timestamp=None,
                        meta={"DBRType": "DBR_SCALAR_DOUBLE"},
                    ),
                    "ACCL:L0B:0110:AACTMEAN": ArchiverValue(
                        secs=1712008589,
                        val=6.509116634443234,
                        nanos=706573951,
                        severity=0,
                        status=0,
                        fields={},
                        _timestamp=None,
                        meta={"DBRType": "DBR_SCALAR_DOUBLE"},
                    ),
                },
                "2024-03-31 14:56:30.000010": {
                    "ACCL:L0B:0110:DFBEST": ArchiverValue(
                        secs=1711922189,
                        val=-1.592,
                        nanos=339947228,
                        severity=0,
                        status=0,
                        fields={},
                        _timestamp=None,
                        meta={"DBRType": "DBR_SCALAR_DOUBLE"},
                    ),
                    "ACCL:L0B:0110:AACTMEAN": ArchiverValue(
                        secs=1711922189,
                        val=6.509128665496809,
                        nanos=98839769,
                        severity=0,
                        status=0,
                        fields={},
                        _timestamp=None,
                        meta={"DBRType": "DBR_SCALAR_DOUBLE"},
                    ),
                },
                "2024-03-30 14:56:30.000010": {
                    "ACCL:L0B:0110:DFBEST": ArchiverValue(
                        secs=1711835789,
                        val=-1.068,
                        nanos=347603983,
                        severity=0,
                        status=0,
                        fields={},
                        _timestamp=None,
                        meta={"DBRType": "DBR_SCALAR_DOUBLE"},
                    ),
                    "ACCL:L0B:0110:AACTMEAN": ArchiverValue(
                        secs=1711835789,
                        val=6.509181480616865,
                        nanos=284106860,
                        severity=0,
                        status=0,
                        fields={},
                        _timestamp=None,
                        meta={"DBRType": "DBR_SCALAR_DOUBLE"},
                    ),
                },
                "2024-03-29 14:56:30.000010": {
                    "ACCL:L0B:0110:DFBEST": ArchiverValue(
                        secs=1711749389,
                        val=-0.004,
                        nanos=339083194,
                        severity=3,
                        status=14,
                        fields={},
                        _timestamp=None,
                        meta={"DBRType": "DBR_SCALAR_DOUBLE"},
                    ),
                    "ACCL:L0B:0110:AACTMEAN": ArchiverValue(
                        secs=1711749389,
                        val=0.00042876622143185557,
                        nanos=928502917,
                        severity=2,
                        status=5,
                        fields={},
                        _timestamp=None,
                        meta={"DBRType": "DBR_SCALAR_DOUBLE"},
                    ),
                },
                "2024-03-28 14:56:30.000010": {
                    "ACCL:L0B:0110:DFBEST": ArchiverValue(
                        secs=1711662980,
                        val=0.0,
                        nanos=335472655,
                        severity=3,
                        status=14,
                        fields={},
                        _timestamp=None,
                        meta={"DBRType": "DBR_SCALAR_DOUBLE"},
                    ),
                    "ACCL:L0B:0110:AACTMEAN": ArchiverValue(
                        secs=1711662989,
                        val=0.00040902722895514007,
                        nanos=228827866,
                        severity=2,
                        status=5,
                        fields={},
                        _timestamp=None,
                        meta={"DBRType": "DBR_SCALAR_DOUBLE"},
                    ),
                },
                "2024-03-27 14:56:30.000010": {
                    "ACCL:L0B:0110:DFBEST": ArchiverValue(
                        secs=1711576583,
                        val=0.0,
                        nanos=335606946,
                        severity=3,
                        status=14,
                        fields={},
                        _timestamp=None,
                        meta={"DBRType": "DBR_SCALAR_DOUBLE"},
                    ),
                    "ACCL:L0B:0110:AACTMEAN": ArchiverValue(
                        secs=1711576589,
                        val=0.00041344532175155213,
                        nanos=399083384,
                        severity=2,
                        status=5,
                        fields={},
                        _timestamp=None,
                        meta={"DBRType": "DBR_SCALAR_DOUBLE"},
                    ),
                },
                "2024-03-26 14:56:30.000010": {
                    "ACCL:L0B:0110:DFBEST": ArchiverValue(
                        secs=1711490181,
                        val=0.0,
                        nanos=644099825,
                        severity=3,
                        status=14,
                        fields={},
                        _timestamp=None,
                        meta={"DBRType": "DBR_SCALAR_DOUBLE"},
                    ),
                    "ACCL:L0B:0110:AACTMEAN": ArchiverValue(
                        secs=1711490189,
                        val=0.0004538000381352912,
                        nanos=828662425,
                        severity=2,
                        status=5,
                        fields={},
                        _timestamp=None,
                        meta={"DBRType": "DBR_SCALAR_DOUBLE"},
                    ),
                },
                "2024-03-25 14:56:30.000010": {
                    "ACCL:L0B:0110:DFBEST": ArchiverValue(
                        secs=1711403789,
                        val=0.0,
                        nanos=652453946,
                        severity=3,
                        status=14,
                        fields={},
                        _timestamp=None,
                        meta={"DBRType": "DBR_SCALAR_DOUBLE"},
                    ),
                    "ACCL:L0B:0110:AACTMEAN": ArchiverValue(
                        secs=1711403789,
                        val=0.0014643136084407868,
                        nanos=693785347,
                        severity=2,
                        status=5,
                        fields={},
                        _timestamp=None,
                        meta={"DBRType": "DBR_SCALAR_DOUBLE"},
                    ),
                },
                "2024-03-24 14:56:30.000010": {
                    "ACCL:L0B:0110:DFBEST": ArchiverValue(
                        secs=1711317389,
                        val=-1.712,
                        nanos=650207766,
                        severity=0,
                        status=0,
                        fields={},
                        _timestamp=None,
                        meta={"DBRType": "DBR_SCALAR_DOUBLE"},
                    ),
                    "ACCL:L0B:0110:AACTMEAN": ArchiverValue(
                        secs=1711317388,
                        val=6.509005035059151,
                        nanos=888839911,
                        severity=0,
                        status=0,
                        fields={},
                        _timestamp=None,
                        meta={"DBRType": "DBR_SCALAR_DOUBLE"},
                    ),
                },
                "2024-03-23 14:56:30.000010": {
                    "ACCL:L0B:0110:DFBEST": ArchiverValue(
                        secs=1711230989,
                        val=-1.1280000000000001,
                        nanos=644712314,
                        severity=0,
                        status=0,
                        fields={},
                        _timestamp=None,
                        meta={"DBRType": "DBR_SCALAR_DOUBLE"},
                    ),
                    "ACCL:L0B:0110:AACTMEAN": ArchiverValue(
                        secs=1711230989,
                        val=6.50903783824157,
                        nanos=45399642,
                        severity=0,
                        status=0,
                        fields={},
                        _timestamp=None,
                        meta={"DBRType": "DBR_SCALAR_DOUBLE"},
                    ),
                },
                "2024-03-22 14:56:30.000010": {
                    "ACCL:L0B:0110:DFBEST": ArchiverValue(
                        secs=1711144589,
                        val=-0.10400000000000001,
                        nanos=643901554,
                        severity=0,
                        status=0,
                        fields={},
                        _timestamp=None,
                        meta={"DBRType": "DBR_SCALAR_DOUBLE"},
                    ),
                    "ACCL:L0B:0110:AACTMEAN": ArchiverValue(
                        secs=1711144589,
                        val=6.5092583877407435,
                        nanos=814986356,
                        severity=0,
                        status=0,
                        fields={},
                        _timestamp=None,
                        meta={"DBRType": "DBR_SCALAR_DOUBLE"},
                    ),
                },
            }

            return time_map[str(time_stamp)]

        mocked_get_data.side_effect = side_effect

        actual_result = get_data_with_time_interval(
            self.pv_lst,
            self.time - timedelta(days=10),
            self.time,
            timedelta(days=1),
        )
        self.assertEqual(
            actual_result,
            self.expected_time_delta_result,
        )

    def test_get_values_over_time_range_with_timedelta(self):
        try:
            self.assertEqual(
                get_values_over_time_range(
                    self.pv_lst,
                    self.time - timedelta(days=10),
                    self.time,
                    timedelta(days=1),
                ),
                self.expected_time_delta_result,
            )

        except requests.exceptions.Timeout:
            self.skipTest("test_get_values_over_time_range connection timed out")
        except requests.exceptions.ConnectionError:
            self.skipTest(
                "test_get_values_over_time_range connection unsuccessful as network was unreachable."
            )

    def test_get_values_over_time_range_without_timedelta(self):
        dfbest_lst = [
            ArchiverValue(
                secs=1712008579,
                val=0.384,
                nanos=339654425,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
                meta=None,
            ),
            ArchiverValue(
                secs=1712008580,
                val=-0.136,
                nanos=335625034,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
                meta=None,
            ),
            ArchiverValue(
                secs=1712008581,
                val=-1.504,
                nanos=340185632,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
                meta=None,
            ),
            ArchiverValue(
                secs=1712008582,
                val=-0.392,
                nanos=335705244,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
                meta=None,
            ),
            ArchiverValue(
                secs=1712008583,
                val=2.524,
                nanos=335132113,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
                meta=None,
            ),
            ArchiverValue(
                secs=1712008584,
                val=2.468,
                nanos=343157132,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
                meta=None,
            ),
            ArchiverValue(
                secs=1712008585,
                val=-1.056,
                nanos=335973383,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
                meta=None,
            ),
            ArchiverValue(
                secs=1712008586,
                val=-0.524,
                nanos=335243245,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
                meta=None,
            ),
            ArchiverValue(
                secs=1712008587,
                val=0.772,
                nanos=342905024,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
                meta=None,
            ),
            ArchiverValue(
                secs=1712008588,
                val=1.564,
                nanos=335933803,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
                meta=None,
            ),
            ArchiverValue(
                secs=1712008589,
                val=-0.5760000000000001,
                nanos=351862628,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
                meta=None,
            ),
        ]

        aactmean_lst = [
            ArchiverValue(
                secs=1712008579,
                val=6.509116869696968,
                nanos=782748462,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
                meta=None,
            ),
            ArchiverValue(
                secs=1712008580,
                val=6.509116381950056,
                nanos=896122632,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
                meta=None,
            ),
            ArchiverValue(
                secs=1712008582,
                val=6.509115496941781,
                nanos=9162288,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
                meta=None,
            ),
            ArchiverValue(
                secs=1712008583,
                val=6.509114874488454,
                nanos=120870202,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
                meta=None,
            ),
            ArchiverValue(
                secs=1712008584,
                val=6.5091161400477375,
                nanos=139994427,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
                meta=None,
            ),
            ArchiverValue(
                secs=1712008585,
                val=6.5091153248503755,
                nanos=252011512,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
                meta=None,
            ),
            ArchiverValue(
                secs=1712008589,
                val=6.509116634443234,
                nanos=706573951,
                severity=0,
                status=0,
                fields=None,
                _timestamp=None,
                meta=None,
            ),
        ]

        expected_result: DefaultDict[str, ArchiveDataHandler] = defaultdict(
            ArchiveDataHandler
        )
        expected_result["ACCL:L0B:0110:DFBEST"] = ArchiveDataHandler(
            value_list=dfbest_lst
        )
        expected_result["ACCL:L0B:0110:AACTMEAN"] = ArchiveDataHandler(
            value_list=aactmean_lst
        )

        try:
            actual_result = get_values_over_time_range(
                self.pv_lst,
                self.time - timedelta(seconds=10),
                self.time,
            )
            self.assertEqual(
                actual_result,
                expected_result,
            )

        except requests.exceptions.Timeout:
            self.skipTest("test_get_values_over_time_range connection timed out")
        except requests.exceptions.ConnectionError:
            self.skipTest(
                "test_get_values_over_time_range connection unsuccessful as network was unreachable."
            )


if __name__ == "__main__":
    unittest.main()
