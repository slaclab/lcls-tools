import unittest
from unittest.mock import patch
from pydantic import ValidationError
import pandas as pd
import numpy as np
from lcls_tools.common.data_analysis.plotting_base import (FontBase, LabelBase,
                                                           PlottingBase)


class TestPlottingBase(unittest.TestCase):

    def test_fontbase_initialization(self):
        font = FontBase(family="Arial", color="blue", size=12)
        self.assertEqual(font.family, "Arial")
        self.assertEqual(font.color, "blue")
        self.assertEqual(font.size, 12)

    def test_fontbase_validation(self):
        with self.assertRaises(ValidationError):
            FontBase(family="Arial", color="blue", size=-5)

    def test_labelbase_initialization(self):
        label = LabelBase(x_axis="Time", y_axis="Value")
        self.assertEqual(label.x_axis, "Time")
        self.assertEqual(label.y_axis, "Value")

    def test_plottingbase_initialization(self):
        df = pd.DataFrame({
            "Timestamp": pd.date_range(start="2024/06/05 00:00:00", periods=5,
                                       freq="D"),
            "PV1": np.random.random(5)
        })
        plot = PlottingBase(pv_dataframes=[df])
        self.assertEqual(plot.figure_width, 10)
        self.assertEqual(plot.figure_height, 7)

    def test_plottingbase_validation(self):
        with self.assertRaises(ValidationError):
            PlottingBase(pv_dataframes=[], figure_width=-10)

    @patch("lcls_tools.common.data_analysis.plotting_base.plt.show")
    def test_plot_pvs_correlation(self, mock):
        df = pd.DataFrame({
            "PVX": np.random.random(5),
            "PVY": np.random.random(5)
        })
        plot = PlottingBase(pv_dataframes=[], df_correlation=df, pv_x="PVX",
                            pv_y="PVY")
        plot.plot_pvs_correlation()

    @patch("lcls_tools.common.data_analysis.plotting_base.plt.show")
    def test_empty_pv_over_time(self, mock):
        with self.assertRaises(AssertionError):
            plot = PlottingBase(pv_dataframes=[])
            plot.plot_pv_over_time()

    @patch("lcls_tools.common.data_analysis.plotting_base.plt.show")
    def test_empty_pv_correlation(self, mock):
        with self.assertRaises(AssertionError):
            plot = PlottingBase(pv_dataframes=[],
                                df_correlation=pd.DataFrame())
            plot.plot_pvs_correlation()

    @patch("lcls_tools.common.data_analysis.plotting_base.plt.show")
    def test_incorrect_pv_columns_correlation(self, mock):
        df = pd.DataFrame({
            "PVX": np.random.random(5),
            "PVY": np.random.random(5)
        })
        with self.assertRaises(AssertionError):
            plot = PlottingBase(pv_dataframes=[], df_correlation=df,
                                pv_x="PV1", pv_y="PV2")
            plot.plot_pvs_correlation()

    def test_fontbase_non_string_family(self):
        with self.assertRaises(ValidationError):
            FontBase(family=123, color="blue", size=12)

    def test_fontbase_invalid_color(self):
        with self.assertRaises(ValidationError):
            FontBase(family="Arial", color=123, size=12)

    @patch("lcls_tools.common.data_analysis.plotting_base.plt.show")
    def test_plot_correlation_with_fit_line(self, mock):
        df = pd.DataFrame({
            "PVX": np.random.random(5),
            "PVY": np.random.random(5)
        })
        plot = PlottingBase(pv_dataframes=[], df_correlation=df, pv_x="PVX",
                            pv_y="PVY", has_fit_line=True)
        plot.plot_pvs_correlation()

    @patch("lcls_tools.common.data_analysis.plotting_base.plt.show")
    def test_plot_correlation_with_colormap(self, mock):
        df = pd.DataFrame({
            "PVX": np.random.random(50),
            "PVY": np.random.random(50)
        })
        plot = PlottingBase(pv_dataframes=[], df_correlation=df, pv_x="PVX",
                            pv_y="PVY", is_scatter_plot=True,
                            is_cmap=True)
        plot.plot_pvs_correlation()


if __name__ == "__main__":
    unittest.main()
