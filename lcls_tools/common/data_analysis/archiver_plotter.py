import sys
from datetime import datetime
import pandas as pd
from pandas import DataFrame
import matplotlib.pyplot as plt
import lcls_tools.common.data_analysis.archiver as arch


class ArchiverPlotter:
    def __init__(self):
        self.max_year_range = 5  # set the maximum timeframe for which to request PV data
        self.font_x = {
            "family": "",
            "color": "",
            "size": 16
        }
        self.font_y = {
            "family": "",
            "color": "",
            "size": 16
        }
        self.font_title = {
            "family": "",
            "color": "",
            "size": 20
        }
        self.label_settings = {
            "y_axis": "",
            "x_axis": ""
        }
        self.tick_x_size = 10
        self.tick_y_size = 10
        return

    def set_fonts(self, label_font: str, xlabel_color: str, ylabel_color: str, title_color: str, tick_size_x: int,
                  tick_size_y: int, title_size: int, label_size: int):
        """Sets font instance variables."""
        self.font_x["family"] = label_font
        self.font_y["family"] = label_font
        self.font_title["family"] = label_font
        self.font_x["color"] = xlabel_color
        self.font_y["color"] = ylabel_color
        self.font_title["color"] = title_color
        self.font_x["size"] = label_size
        self.font_y["size"] = label_size
        self.tick_x_size = tick_size_x
        self.tick_y_size = tick_size_y
        self.font_title["size"] = title_size
        return None

    """HELPER METHODS FOR PLOTTING"""

    def create_df(self, pv_str: str, start: str, end: str) -> DataFrame:
        """Create and return a DataFrame given a PV and start/end date.

        Column titles of the DataFrame are "timestamps" and the pv_str. 

        :param pv_str: The PV to plot.
        :param start: The start date of the plot in YYYY/MM/DD HH:MM:SS format.
        :param end: The end date of the plot in YYYY/MM/DD HH:MM:SS format.
        """

        # ERROR HANDLING
        if pv_str == "":
            raise ValueError("Empty PV string given")
        if ":" not in pv_str:  # check if there are any illegal characters
            raise KeyError("Invalid PV string given")
        if start == "" or end == "":
            raise ValueError("Empty start or end date string given")
        if int(end.split("/")[0]) - int(start.split("/")[0]) > self.max_year_range:
            raise ValueError("Too large of a dataset requested")

        # specify a start and end date
        format_string = "%Y/%m/%d %H:%M:%S"
        start_date_obj = datetime.strptime(start, format_string)  # create a datetime object
        end_date_obj = datetime.strptime(end, format_string)
        # submit request with a list of PVs
        data = arch.get_values_over_time_range([pv_str], start_date_obj, end_date_obj)
        # create a dictionary for a PV, access it with timestamps and values methods from archiver.py
        pv_dict = data[pv_str]
        pv_timestamps = pv_dict.timestamps
        pv_values = pv_dict.values
        pv_clean_timestamps = [pv_timestamps[i].strftime(format_string) for i in
                               range(len(pv_timestamps))]  # clean and reformat timestamps from the dict
        return pd.DataFrame({"timestamps": pv_clean_timestamps, pv_str: pv_values})  # create df with columns

    def create_correlation_df(self, df_x: pd.DataFrame, df_y: pd.DataFrame) -> pd.DataFrame:
        """Given two DataFrames of PVs, return a single DataFrame with matching and aligned timestamps.

        :param df_y: The name of the PV or the DataFrame that will be plotted on the y-axis.
        :param df_x: The name of the PV that will be plotted on the x-axis.
        """
        if df_x.empty or df_y.empty:
            return pd.DataFrame()
        return pd.merge(df_y, df_x, on="timestamps")  # merge DataFrames on equal timestamp strings

    def get_formatted_timestamps(self, df_list: list[pd.DataFrame]) -> list[str]:
        """Removes redundant timestamp labels if they are the same throughout all the data points."""
        if len(df_list) == 0:  # handle empty lists
            return []
        date_list = df_list[0]["timestamps"].tolist()
        # compares the first and last timestamp
        first_date = date_list[0]
        last_date = date_list[-1]
        date_format_list = ["%Y/", "%m/", "%d", " ", "%H:", "%M:", "%S"]
        # go character by character, comparing digits until they differ, then formatting appropriately
        for i in range(len(first_date)):
            curr_first_date = first_date[i]
            curr_last_date = last_date[i]
            # if the current year, month, day, etc. is not the same, then print the remaining timestamps on the axis
            if curr_first_date != curr_last_date:
                break
            if curr_first_date == "/" or curr_first_date == ":" or curr_last_date == " ":
                del date_format_list[0]
        date_format_str = "".join(date_format_list)
        # returns a list of reformatted timestamp strings that will be plotted
        return [datetime.strptime(date, "%Y/%m/%d %H:%M:%S").strftime(date_format_str) for date in date_list]

    """PLOTTING METHODS"""

    def plot_pv_over_time(self,
                          df_list: list[pd.DataFrame],
                          width: int = 10,
                          height: int = 7,
                          xlabel: str = "Timestamp",
                          ylabel: str = "PV",
                          xlabel_color: str = "black",
                          ylabel_color: str = "black",
                          title_color: str = "black",
                          label_font: str = "Helvetica",
                          label_size: int = 16,
                          pv_colors: tuple[str] = ("tab:blue", "tab:orange", "tab:green", "tab:red", "tab:purple"),
                          line_types: tuple[str] = ("solid", "dashed", "dashdot", "dotted"),
                          marker_types: tuple[str] = ("x", ".", "^", "s", "p", "*"),
                          is_scatter: bool = False,
                          is_marker: bool = False,
                          marker_size: int = 5,
                          pv_labels: list[str] = None,
                          num_ticks: int = 7,
                          tick_size_x: int = 10,
                          tick_size_y: int = 10,
                          title_size: int = 20,
                          smart_title: bool = False,
                          smart_timestamps: bool = True):
        """Plots a nonempty list of PVs over time.

        :param df_list: A list of DataFrames from which to plot the PVs.

        :param width: The width of the plot to be rendered. 
        :param height: The height of the plot to be rendered. 
        :param xlabel: The label that will be on the bottom of the plot.
        :param ylabel: The label that will be to the left of the plot.
        :param xlabel_color: The color of the x label/s.
        :param ylabel_color: The color of the y label/s.
        :param title_color: The color of the title.
        :param label_font: The font for all the labels for the plot.
        :param label_size: The size of the labels for the plot.
        :param pv_colors: A list of colors for each pv that is plotted, in the order of df_list. 
        :param line_types: A list of all line types for each pv that is plotted, in the order of df_list.
        :param marker_types: A list of all markers for each pv that is plotted, in the order of df_list.
        :param is_scatter: A boolean for whether to plot all points as scatter, or to plot as lines.
        :param is_marker: A boolean for whether to plot all points as markers.
        :param marker_size: The size of the scatter marker, if scatter is chosen as a line_types option. 
        :param pv_labels: A list of labels for each PV, in the order of df_list.
        :param num_ticks: The number of ticks along the x-axis of the plot.
        :param tick_size_x: The size of the tick labels along the x-axis of the plot.
        :param tick_size_y: The size of the tick labels along the x-axis of the plot.
        :param title_size: The size of the title of the plot.
        :param smart_title: A boolean for whether to list the PVs in the title.
        :param smart_timestamps: A boolean for whether to reduce redundant timestamp labels.
        """

        # ERROR HANDLING
        if len(df_list) == 0:
            raise ValueError("Empty DataFrame given")

        fig, ax = plt.subplots(figsize=(width, height), layout="constrained")

        # LEGEND LABELS
        if pv_labels is not None:
            # rename columns to label names
            for i in range(len(df_list)):
                df_curr = df_list[i]
                df_curr.rename(columns={df_curr.columns[1]: pv_labels[i]}, inplace=True)

        # PLOTTING
        for i in range(len(df_list)):  # plot each DataFrame in df_list
            df_curr = df_list[i]  # current DataFrame plotted
            col = df_curr.columns[1]  # y-axis Series for each of the DataFrames
            if not is_scatter:  # line plot
                # choose a line type and plot accordingly
                curr_line_type = line_types[i % len(line_types)]  # cycle through the list
                # marker plot
                if is_marker:
                    ax.plot(df_curr["timestamps"], df_curr[col], color=pv_colors[i % len(pv_colors)],
                            linestyle=curr_line_type, label=col,
                            marker=marker_types[i % len(marker_types)], markersize=marker_size)
                # line plot
                else:
                    ax.plot(df_curr["timestamps"], df_curr[col], color=pv_colors[i % len(pv_colors)],
                            linestyle=curr_line_type, label=col)
            # scatter plot
            else:
                ax.scatter(df_curr["timestamps"], df_curr[col], label=col, s=marker_size)

        # LABELS
        ax.legend()
        self.set_fonts(label_font, xlabel_color, ylabel_color, title_color, tick_size_x, tick_size_y, title_size,
                       label_size)
        plt.xlabel(xlabel, fontdict=self.font_x)
        plt.ylabel(ylabel, fontdict=self.font_y)
        ax.tick_params(axis="x", labelsize=self.tick_x_size)
        ax.tick_params(axis="y", labelsize=self.tick_y_size)
        ax.ticklabel_format(axis="y", style='sci', scilimits=(-3, 3))  # scientific notation outside range 10^-3 to 10^3

        # TICKS
        if smart_timestamps:
            xticklabels = self.get_formatted_timestamps(df_list)  # remove redundant timestamp labels
            ax.set_xticks(range(len(xticklabels)))  # set a fixed number of ticks to avoid warnings
            ax.set_xticklabels(xticklabels)
        ax.xaxis.set_major_locator(plt.MaxNLocator(num_ticks))  # reduce the amount of ticks for both axes
        ax.yaxis.set_major_locator(plt.MaxNLocator(num_ticks))

        # TITLE
        if not smart_title:
            plt.title("PVs vs. Time", fontdict=self.font_title)
        else:
            # create a title using the PV names
            pv_list = [df_curr.columns[1] for df_curr in df_list]
            plt.title(f"{", ".join(pv_list)} vs. Time", fontdict=self.font_title)

        plt.show()

    def plot_correl(self,
                    df: pd.DataFrame,
                    pv_x: str,
                    pv_y: str,
                    width: int = 10,
                    height: int = 7,
                    xlabel_color: str = "black",
                    ylabel_color: str = "black",
                    title_color: str = "black",
                    label_font: str = "Helvetica",
                    label_size: int = 16,
                    correl_color: str = "tab:blue",
                    line_type: str = "solid",
                    marker_type: str = ".",
                    is_scatter: bool = True,
                    is_marker: bool = False,
                    marker_size: int = 5,
                    pv_xlabel: str = None,
                    pv_ylabel: str = None,
                    num_ticks: int = 7,
                    tick_size_x: int = 10,
                    tick_size_y: int = 10,
                    title_size: int = 20,
                    smart_labels: bool = False):
        """Plot the correlation of two PVs. 

        :param df: The DataFrame from which the PVs are plotted. 
        :param pv_x: The PV to be plotted on the x-axis. 
        :param pv_y: The PV to be plotted on the y-axis.

        :param width: The width of the plot to be rendered.
        :param height: The height of the plot to be rendered.
        :param xlabel_color: The color of the x label/s.
        :param ylabel_color: The color of the y label/s.
        :param title_color: The color of the title.
        :param label_font: The font for all the labels for the plot.
        :param label_size: The size of the labels for the plot.
        :param correl_color: The color of the correlation plot.
        :param line_type: The default line type for the plot.
        :param marker_type: The default marker type for the plot.
        :param is_scatter: A boolean for whether to plot all points as scatter, or to plot as lines.
        :param is_marker: A boolean for whether to plot all points as markers.
        :param marker_size: The size of the scatter marker, if scatter is chosen as a line_types option.
        :param pv_xlabel: The label for the x-axis.
        :param pv_ylabel: The label for the y-axis.
        :param num_ticks: The number of ticks along the x-axis of the plot.
        :param tick_size_x: The size of the tick labels along the x-axis of the plot.
        :param tick_size_y: The size of the tick labels along the x-axis of the plot.
        :param title_size: The size of the title of the plot.
        :param smart_labels: A boolean for whether to list the PVs in the title.
        """

        # ERROR HANDLING
        if pv_x not in df.columns or pv_y not in df.columns:
            raise ValueError("PVs not found in the given DataFrame.")

        fig, ax = plt.subplots(figsize=(width, height), layout="constrained")

        # LEGEND LABELS
        if pv_xlabel is not None and pv_ylabel is not None:
            df.rename(columns={pv_x: pv_xlabel, pv_y: pv_ylabel}, inplace=True)
        else:
            pv_xlabel = pv_x
            pv_ylabel = pv_y

        # PLOTTING
        if not is_scatter:  # line plot
            # with marker
            if is_marker:
                ax.plot(df[pv_xlabel], df[pv_ylabel], color=correl_color, linestyle=line_type, marker=marker_type,
                        markersize=marker_size)
            # without marker
            else:
                ax.plot(df[pv_xlabel], df[pv_ylabel], color=correl_color, linestyle=line_type)
        # scatter plot
        else:
            ax.scatter(df[pv_xlabel], df[pv_ylabel], color=correl_color, s=marker_size)

        # LABELS
        if smart_labels and pv_xlabel is not None and pv_ylabel is not None:
            self.label_settings["y_axis"] = pv_ylabel
            self.label_settings["x_axis"] = pv_xlabel

        self.set_fonts(label_font, xlabel_color, ylabel_color, title_color, tick_size_x, tick_size_y, title_size,
                       label_size)
        plt.title(f"{self.label_settings["y_axis"]} vs. {self.label_settings["x_axis"]}", fontdict=self.font_title)
        plt.xlabel(self.label_settings["x_axis"], fontdict=self.font_x)
        plt.ylabel(self.label_settings["y_axis"], fontdict=self.font_y)
        ax.tick_params(axis="x", labelsize=self.tick_x_size)
        ax.tick_params(axis="y", labelsize=self.tick_y_size)
        ax.ticklabel_format(axis="y", style='sci', scilimits=(-3, 3))  # scientific notation outside range 10^-3 to 10^3
        ax.xaxis.set_major_locator(plt.MaxNLocator(num_ticks))
        ax.yaxis.set_major_locator(plt.MaxNLocator(num_ticks))

        plt.show()
