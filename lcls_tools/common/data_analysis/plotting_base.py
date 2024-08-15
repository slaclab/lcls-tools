from pydantic import BaseModel, PositiveInt
from typing import Literal
import pandas as pd
from lcls_tools.common.data_analysis import archiver_data_process as data_processor
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import gaussian_kde


class FontBase(BaseModel):
    family: str
    color: str
    size: PositiveInt


class LabelBase(BaseModel):
    x_axis: str
    y_axis: str


class PlottingBase(BaseModel):
    """Base class for all plotting. Can be used for plotting over time as well
    as for correlations between PVs.

    :param pv_dataframes: list of DataFrames from which to plot multiple PVs
    over time
    :param df_correlation: DataFrame from which to plot correlations, with two
    non-Timeframe columns for PVs.
    :param pv_x: The PV to plot on the x-axis, when plotting a correlation.
    :param pv_y: The PV to plot on the y-axis, when plotting a correlation.
    :param pv_x_label: The label for the PV that will be plotted on the x-axis.
    :param pv_y_label: The label for the PV that will be plotted on the y-axis.
    :param pv_labels: The labels for the PVs, when plotting PVs over time, in
    order of pv_dataframes
    :param figure_width: The width of the matplotlib figure.
    :param figure_height: The height of the matplotlib figure.
    :param figure_title: The title of the matplotlib figure.
    :param figure_title_font_size: The font size of the title of the matplotlib
    figure.
    :param has_smart_title: Boolean for whether the figure title is an
    auto-generated title from axis labels.
    :param has_axis_labels: Boolean for whether to rename axis labels to
    specified labels, instead of PV names.
    :param figure_title_color: The color of the title of the matplotlib figure.
    :param x_axis_label: The label for the x-axis of the matplotlib figure.
    :param y_axis_label: The label for the y-axis of the matplotlib figure.
    :param x_axis_label_color: Color of the x-axis of the matplotlib figure.
    :param y_axis_label_color: Color of the y-axis of the matplotlib figure.
    :param all_label_font_family: The font family for all labels of the
    matplotlib figure.
    :param axis_label_font_size: The font size of the axis labels of the
    matplotlib figure.
    :param num_axis_ticks: The number of ticks along the axes of the matplotlib
    figure.
    :param x_axis_tick_font_size: The font size of the x-axis ticks on the
    matplotlib figure.
    :param y_axis_tick_font_size: The font size of the y-axis ticks on the
    matplotlib figure.
    :param has_smart_timestamps: Boolean for whether the figure title is an
    auto-formatted timestamp from axis labels.
    :param is_scatter_plot: Boolean for whether to plot a scatter plot instead
    of a line or line-and-marker plot.
    :param is_cmap: Boolean for whether to plot a color density map when
    plotting a scatter plot for a correlation.
    :param is_line_and_marker_plot: Boolean for whether to plot a
    line-and-marker plot when plotting a line plot.
    :param has_fit_line: Boolean for whether to plot a line of best fit for a
    scatter plot, for a correlation.
    :param marker_size: The size of the marker when plotting a line-and-marker
    plot.
    :param pv_colors: A tuple of colors to rotate through when plotting PVs
    over time.
    :param correlation_color: The color of the points or line when plotting a
    correlation.
    :param line_types: A tuple of line types to rotate through when plotting
    PVs over time.
    :param correlation_line_type: The line type for a correlation plot.
    :param marker_types: A tuple of marker types to rotate through when
    plotting PVs over time.
    :param correlation_marker_type: The marker type for a correlation plot.
    """

    pv_dataframes: list[pd.DataFrame]
    df_correlation: pd.DataFrame = None
    pv_x: str = None
    pv_y: str = None
    pv_x_label: str = None
    pv_y_label: str = None
    pv_labels: list[str] = None
    figure_width: PositiveInt = 10
    figure_height: PositiveInt = 7
    figure_title: str = None
    figure_title_font_size: PositiveInt = 28
    has_smart_title: bool = False
    has_axis_labels: bool = False
    figure_title_color: str = "black"
    x_axis_label: str = "Timestamp"
    y_axis_label: str = "PV"
    x_axis_label_color: str = "black"
    y_axis_label_color: str = "black"
    all_label_font_family: str = "DejaVu Sans"
    axis_label_font_size: PositiveInt = 23
    num_axis_ticks: PositiveInt = 4
    x_axis_tick_font_size: PositiveInt = 18
    y_axis_tick_font_size: PositiveInt = 18
    has_smart_timestamps: bool = True
    is_scatter_plot: bool = False
    is_cmap: bool = False
    is_line_and_marker_plot: bool = False
    has_fit_line: bool = False
    marker_size: PositiveInt = 5
    pv_colors: tuple[str] = ("tab:blue", "tab:orange", "tab:green", "tab:red",
                             "tab:purple")
    correlation_color: str = "tab:blue"
    line_types: tuple[Literal["solid", "dashed", "dashdot", "dotted"]] = \
        ("solid", "dashed", "dashdot", "dotted")
    correlation_line_type: Literal["solid", "dashed", "dashdot", "dotted"] = \
        "solid"
    marker_types: tuple[Literal[".", ",", "o", "v", "^", "<", ">", "1", "2",
                                "3", "4", "8", "s", "p", "P", "*", "h", "H",
                                "+", "x", "X", "D", "d", "|", "_", 0, 1, 2, 3,
                                4, 5, 6, 7, 8, 9, 10, 11, "none", "None", " ",
                                "", "$...$"]] = ("x", ".", "^", "s", "p", "*")
    correlation_marker_type: Literal[".", ",", "o", "v", "^", "<", ">", "1",
                                     "2", "3", "4", "8", "s", "p", "P", "*",
                                     "h", "H", "+", "x", "X", "D", "d", "|",
                                     "_", 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11,
                                     "none", "None", " ", "", "$...$"] = "o"

    class Config:
        """Allow pandas DataFrame as a type."""
        arbitrary_types_allowed = True

    def plot_pv_over_time(self):
        """Plots a nonempty list of PVs over time."""
        assert len(self.pv_dataframes) > 0, "Empty DataFrame given"
        fig, ax = plt.subplots(figsize=(self.figure_width, self.figure_height),
                               layout="constrained")
        # LEGEND LABELS
        if self.pv_labels is not None:
            # rename columns to label names
            for i in range(len(self.pv_dataframes)):
                df_curr = self.pv_dataframes[i]
                df_curr.rename(columns={df_curr.columns[1]: self.pv_labels[i]},
                               inplace=True)

        # PLOTTING
        # plot each DataFrame in df_list
        for i in range(len(self.pv_dataframes)):
            df_curr = self.pv_dataframes[i]  # current DataFrame plotted
            col = df_curr.columns[1]  # y-axis Series for each DataFrame
            if not self.is_scatter_plot:  # line plot
                # choose a line type and plot accordingly
                # cycle through the list
                curr_line_type = self.line_types[i % len(self.line_types)]
                # marker plot
                if self.is_line_and_marker_plot:
                    ax.plot(df_curr["Timestamp"], df_curr[col],
                            color=self.pv_colors[i % len(self.pv_colors)],
                            linestyle=curr_line_type, label=col,
                            marker=self.marker_types[i %
                                                     len(self.marker_types)],
                            markersize=self.marker_size)
                # line plot
                else:
                    ax.plot(df_curr["Timestamp"], df_curr[col],
                            color=self.pv_colors[i % len(self.pv_colors)],
                            linestyle=curr_line_type, label=col)
            # scatter plot
            else:
                ax.scatter(df_curr["Timestamp"], df_curr[col], label=col,
                           s=self.marker_size)

        font_x = FontBase(family=self.all_label_font_family,
                          color=self.x_axis_label_color,
                          size=self.axis_label_font_size)
        font_y = FontBase(family=self.all_label_font_family,
                          color=self.y_axis_label_color,
                          size=self.axis_label_font_size)
        font_title = FontBase(family=self.all_label_font_family,
                              color=self.figure_title_color,
                              size=self.figure_title_font_size)

        # LABELS
        ax.legend()
        plt.xlabel(self.x_axis_label, fontdict=font_x.model_dump())
        plt.ylabel(self.y_axis_label, fontdict=font_y.model_dump())
        ax.tick_params(axis="x", labelsize=self.x_axis_tick_font_size)
        ax.tick_params(axis="y", labelsize=self.y_axis_tick_font_size)
        # scientific notation outside range 10^-3 to 10^3
        ax.ticklabel_format(axis="y", style='sci', scilimits=(-3, 3))

        # TICKS
        if self.has_smart_timestamps:
            # remove redundant timestamp labels
            xticklabels = (data_processor.
                           get_formatted_timestamps(self.pv_dataframes))
            # set a fixed number of ticks to avoid warnings
            ax.set_xticks(range(len(xticklabels)))
            ax.set_xticklabels(xticklabels)
        # reduce the amount of ticks for both axes
        ax.xaxis.set_major_locator(plt.MaxNLocator(self.num_axis_ticks))
        ax.yaxis.set_major_locator(plt.MaxNLocator(self.num_axis_ticks))

        # TITLE
        if not self.has_smart_title:
            plt.title("PVs vs. Time", fontdict=font_title.model_dump())
        else:
            # create a title using the PV names
            pv_list = [df_curr.columns[1] for df_curr in self.pv_dataframes]
            plt.title(f"{", ".join(pv_list)} vs. Time",
                      fontdict=font_title.model_dump())
        plt.show()

    def plot_pvs_correlation(self):
        """Plot a correlation between two PVs."""
        assert self.df_correlation is not None, "Empty DataFrame given."
        assert (self.pv_x in self.df_correlation.columns and self.pv_y in
                self.df_correlation.columns), \
            "PVs not found in the given DataFrame."

        fig, ax = plt.subplots(figsize=(self.figure_width, self.figure_height),
                               layout="constrained")

        # LEGEND, PV LABELS
        if self.pv_x_label is not None and self.pv_y_label is not None:
            self.df_correlation.rename(columns={self.pv_x: self.pv_x_label,
                                                self.pv_y: self.pv_y_label},
                                       inplace=True)
        else:
            self.pv_x_label = self.pv_x
            self.pv_y_label = self.pv_y

        # PLOTTING
        if not self.is_scatter_plot:  # line plot
            # with marker
            if self.is_line_and_marker_plot:
                ax.plot(self.df_correlation[self.pv_x_label],
                        self.df_correlation[self.pv_y_label],
                        color=self.correlation_color,
                        linestyle=self.correlation_line_type,
                        marker=self.correlation_marker_type,
                        markersize=self.marker_size)
            # without marker
            else:
                ax.plot(self.df_correlation[self.pv_x_label],
                        self.df_correlation[self.pv_y_label],
                        color=self.correlation_color,
                        linestyle=self.correlation_line_type)
        # scatter plot
        else:
            if not self.is_cmap:
                ax.scatter(self.df_correlation[self.pv_x_label],
                           self.df_correlation[self.pv_y_label],
                           color=self.correlation_color, s=self.marker_size)
            # colormap plot
            else:
                xy = np.vstack([self.df_correlation[self.pv_x_label],
                                self.df_correlation[self.pv_y_label]])
                z = gaussian_kde(xy)(xy)
                ax.scatter(self.df_correlation[self.pv_x_label],
                           self.df_correlation[self.pv_y_label], c=z,
                           cmap="viridis")
            if self.has_fit_line:
                # create a line of best fit
                slope, intercept = np.polyfit(
                    self.df_correlation[self.pv_x_label],
                    self.df_correlation[self.pv_y_label], deg=1)
                ax.axline(xy1=(0, intercept), slope=slope,
                          label=f"y = {slope:.3f}x + {intercept:.3f}",
                          color="red")

        # LABELS
        axis_labels = LabelBase(x_axis=self.pv_x, y_axis=self.pv_y)
        font_x = FontBase(family=self.all_label_font_family,
                          color=self.x_axis_label_color,
                          size=self.axis_label_font_size)
        font_y = FontBase(family=self.all_label_font_family,
                          color=self.y_axis_label_color,
                          size=self.axis_label_font_size)
        font_title = FontBase(family=self.all_label_font_family,
                              color=self.figure_title_color,
                              size=self.figure_title_font_size)

        if (self.has_axis_labels and self.pv_x_label is not None and
                self.pv_y_label is not None):
            axis_labels.x_axis = self.pv_x_label
            axis_labels.y_axis = self.pv_y_label

        if self.has_smart_title:
            plt.title(f"{axis_labels.y_axis} vs. {axis_labels.x_axis}",
                      fontdict=font_title.model_dump())
        else:
            plt.title(f"{self.figure_title}",
                      fontdict=font_title.model_dump())

        plt.xlabel(axis_labels.x_axis, fontdict=font_x.model_dump())
        plt.ylabel(axis_labels.y_axis, fontdict=font_y.model_dump())
        ax.tick_params(axis="x", labelsize=self.x_axis_tick_font_size)
        ax.tick_params(axis="y", labelsize=self.y_axis_tick_font_size)
        # scientific notation outside range 10^-3 to 10^3
        ax.ticklabel_format(axis="y", style='sci', scilimits=(-3, 3))
        ax.xaxis.set_major_locator(plt.MaxNLocator(self.num_axis_ticks))
        ax.yaxis.set_major_locator(plt.MaxNLocator(self.num_axis_ticks))
        plt.show()
