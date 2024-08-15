import unittest
from pydantic import ValidationError
import pandas as pd
from datetime import datetime, timedelta
from lcls_tools.common.data_analysis.archiver_data_process import (
    PVModel, create_df, merge_dfs_by_timestamp_column,
    merge_dfs_with_margin_by_timestamp_column, get_formatted_timestamps)


class TestPVModel(unittest.TestCase):

    def test_valid_pv_model(self):
        pv = PVModel(pv_str="TEST:PV", start="2024/01/01 12:00:00",
                     end="2024/01/01 13:00:00")
        self.assertEqual(pv.pv_str, "TEST:PV")
        self.assertEqual(pv.start, "2024/01/01 12:00:00")
        self.assertEqual(pv.end, "2024/01/01 13:00:00")

    def test_empty_pv_str(self):
        with self.assertRaises(ValidationError):
            PVModel(pv_str="", start="2024/01/01 12:00:00",
                    end="2024/01/01 13:00:00")

    def test_invalid_pv_str(self):
        with self.assertRaises(ValidationError):
            PVModel(pv_str="INVALIDPV", start="2024/01/01 12:00:00",
                    end="2024/01/01 13:00:00")

    def test_empty_start_date(self):
        with self.assertRaises(ValidationError):
            PVModel(pv_str="TEST:PV", start="", end="2024/01/01 13:00:00")

    def test_empty_end_date(self):
        with self.assertRaises(ValidationError):
            PVModel(pv_str="TEST:PV", start="2024/01/01 12:00:00", end="")

    def test_start_date_after_end_date(self):
        with self.assertRaises(ValidationError):
            PVModel(pv_str="TEST:PV", start="2024/01/01 13:00:00",
                    end="2024/01/01 12:00:00")

    def test_end_date_too_far_in_future(self):
        future_date = ((datetime.now() + timedelta(days=1)).
                       strftime("%Y/%m/%d %H:%M:%S"))
        with self.assertRaises(ValidationError):
            PVModel(pv_str="TEST:PV", start="2024/01/01 12:00:00",
                    end=future_date)

    def test_excessive_date_range(self):
        with self.assertRaises(ValidationError):
            PVModel(pv_str="TEST:PV", start="2020/01/01 00:00:00",
                    end="2024/01/01 12:00:00")


class TestMergeDFs(unittest.TestCase):

    def test_merge_dfs_by_timestamp_valid(self):
        df1 = pd.DataFrame({"Timestamp": ["2024/01/01 12:00:00",
                                          "2024/01/01 13:00:00"],
                            "PV1": [1, 2]})
        df2 = pd.DataFrame({"Timestamp": ["2024/01/01 12:00:00",
                                          "2024/01/01 13:00:00"],
                            "PV2": [3, 4]})
        merged_df = merge_dfs_by_timestamp_column(df1, df2)
        self.assertEqual(len(merged_df), 2)
        self.assertIn("Timestamp", merged_df.columns)
        self.assertIn("PV1", merged_df.columns)
        self.assertIn("PV2", merged_df.columns)

    def test_merge_dfs_by_timestamp_empty(self):
        df1 = pd.DataFrame()
        df2 = pd.DataFrame()
        merged_df = merge_dfs_by_timestamp_column(df1, df2)
        self.assertTrue(merged_df.empty)

    def test_merge_dfs_with_margin_valid(self):
        df1 = pd.DataFrame({"Timestamp": pd.to_datetime(
            ["2024/01/01 12:00:00", "2024/01/01 13:00:00"]),
            "PV1": [1, 2]})
        df2 = pd.DataFrame({"Timestamp": pd.to_datetime(
            ["2024/01/01 12:00:10", "2024/01/01 13:00:10"]), "PV2": [3, 4]})
        merged_df = merge_dfs_with_margin_by_timestamp_column(df1, df2, 15)
        self.assertEqual(len(merged_df), 2)
        self.assertIn("PV2 Time Uncert", merged_df.columns)

    def test_merge_dfs_with_margin_out_of_range(self):
        df1 = pd.DataFrame({"Timestamp": pd.to_datetime(
            ["2024/01/01 12:00:00", "2024/01/01 13:00:00"]),
            "PV1": [1, 2]})
        df2 = pd.DataFrame({"Timestamp": pd.to_datetime(
            ["2024/01/01 12:00:30", "2024/01/01 13:00:30"]),
            "PV2": [3, 4]})
        merged_df = merge_dfs_with_margin_by_timestamp_column(df1, df2, 10)
        self.assertTrue(merged_df.empty)


class TestFormattedTimestamps(unittest.TestCase):
    def test_get_formatted_timestamps_empty_df(self):
        with self.assertRaises(AssertionError):
            get_formatted_timestamps([])

    def test_get_formatted_timestamps_different_days(self):
        df1 = pd.DataFrame({"Timestamp": ["2024/01/01 12:00:00",
                                          "2024/01/02 13:00:00"],
                            "PV1": [1, 2]})
        formatted = get_formatted_timestamps([df1])
        self.assertEqual(formatted[0], "01 12:00:00")
        self.assertEqual(formatted[1], "02 13:00:00")


if __name__ == '__main__':
    unittest.main()
