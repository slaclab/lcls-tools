from pydantic import BaseModel, ValidationInfo, field_validator
import pandas as pd
from datetime import datetime
from lcls_tools.common.data_analysis import archiver as arch

# Maximum amount of years between datetimes in a request for PV data
MAX_YEAR_RANGE = 2


class PVModel(BaseModel):
    """Model class that contains parameters that define the pv_str and the
    start and end dates of the dataset.

    :param pv_str: The PV to plot.
    :param start: The start date of the plot in YYYY/MM/DD HH:MM:SS format.
    :param end: The end date of the plot in YYYY/MM/DD HH:MM:SS format.
    """

    pv_str: str
    start: str
    end: str

    @field_validator("pv_str")
    def check_pv_str(cls, pv_str: str) -> str:
        assert pv_str != "", "PV string is empty."
        assert ":" in pv_str, "PV string is invalid."
        return pv_str

    @field_validator("end", mode="after")
    def check_start_end_str(cls, end: str, info: ValidationInfo):
        start = info.data.get("start")
        assert start is not None, "Start date must be provided."
        assert end is not None, "Start date must be provided."
        assert start != "" and start != " ", "Start string is empty"
        assert end != "" and end != " ", "End string is empty."
        start_datetime = datetime.strptime(start, "%Y/%m/%d %H:%M:%S")
        end_datetime = datetime.strptime(end, "%Y/%m/%d %H:%M:%S")
        current_datetime = datetime.now()
        assert (start_datetime
                < current_datetime and end_datetime < current_datetime), \
            "Invalid date, too far in future."
        assert start_datetime < end_datetime, \
            "End date must be greater than start date."
        assert end_datetime.year - start_datetime.year <= MAX_YEAR_RANGE, \
            "Too long of a time range given."
        return end


def pv(pv_str: str, start: str, end: str) -> PVModel:
    """Returns a PVModel instance. Used exclusively with the create_df function
    to return a DataFrame for a PV."""
    return PVModel(pv_str=pv_str, start=start, end=end)


def create_df(pv_model: PVModel) -> pd.DataFrame:
    """Create and return a DataFrame given a PV and start/end date.

    Column titles of the DataFrame are "Timestamp" and the pv_str.
    """

    start = pv_model.start
    end = pv_model.end
    pv_str = pv_model.pv_str

    # specify a start and end date
    format_string = "%Y/%m/%d %H:%M:%S"
    # create a datetime object
    start_date_obj = datetime.strptime(start, format_string)
    end_date_obj = datetime.strptime(end, format_string)
    # submit request with a list of PVs
    data = arch.get_values_over_time_range([pv_str], start_date_obj,
                                           end_date_obj)
    # create a dictionary for a PV, access it with timestamps and values
    # methods from archiver.py
    pv_dict = data[pv_str]
    pv_timestamps = pv_dict.timestamps
    pv_values = pv_dict.values
    pv_clean_timestamps = [pv_timestamps[i].strftime(format_string) for i in
                           range(len(pv_timestamps))]  # clean and reformat
    # timestamps from the dict
    # create df with columns
    return pd.DataFrame({"Timestamp": pv_clean_timestamps, pv_str: pv_values})


def merge_dfs_by_timestamp_column(df_x: pd.DataFrame, df_y: pd.DataFrame)\
        -> pd.DataFrame:
    """Given two DataFrames of PVs, return a single DataFrame with matching and
    aligned timestamps.

    :param df_y: The name of the PV or the DataFrame that will be plotted on
    the y-axis.
    :param df_x: The name of the PV that will be plotted on the x-axis.
    """
    if df_x.empty or df_y.empty:
        return pd.DataFrame()
    return pd.merge(df_y, df_x, on="Timestamp")  # merge DataFrames on equal
    # timestamp strings


def merge_dfs_with_margin_by_timestamp_column(df_1: pd.DataFrame,
                                              df_2: pd.DataFrame,
                                              time_margin_seconds: float):
    """Merges two DataFrames on similar timestamps, where timestamps differ by
    less than the time specified by the time_margin parameter.

    Creates additional columns that store the time difference between the true
    and comparison timestamps.

    Use the pandas method merge_asof to merge the DataFrames within a tolerance
    value (pandas.pydata.org/docs/reference/api/pandas.merge_asof.html).

    According to the pd.merge_asof() function, the first DataFrame parameter in
    the function defines what the second DataFrame is compared to.

    Therefore, the first DataFrame will have a time-axis uncertainty of 0.
    The second DataFrame will have some uncertainty ranging from 0 to the
    time_margin_seconds value.

    :param df_1: First DataFrame with a Timestamp column.
    :param df_2: Second DataFrame with a Timestamp column.
    :param time_margin_seconds: The time margin between two timestamps as given
    in seconds, useful for defining the
    propagated error for a correlation.
    """

    # must convert the values in the Timestamp column to datetime objects
    df_1["Timestamp"] = pd.to_datetime(df_1["Timestamp"])
    df_2["Timestamp"] = pd.to_datetime(df_2["Timestamp"])

    # compute time difference between the second and first DataFrames,
    # add a new column to the second DataFrame
    df_merged = pd.merge_asof(df_1, df_2, on="Timestamp", direction="nearest",
                              tolerance=pd.
                              Timedelta(f"{time_margin_seconds}s"))
    # get time uncertainty
    df_merged[f"{df_2.columns[1]} Time Uncert"] = \
        (df_merged[df_2.columns[1]] - df_merged[df_1.columns[1]])

    # Convert values in the Timestamp column back to String objects,
    # remove NaN rows, and return
    timestamp_list = df_merged["Timestamp"].to_list()
    df_merged["Timestamp"] = timestamp_list
    return df_merged.dropna(how="any")


def get_formatted_timestamps(df_list: list[pd.DataFrame]) -> list[str]:
    """Removes redundant timestamp labels if they are the same throughout all
    the data points.
    """

    assert len(df_list) > 0, "DataFrame list is empty."
    date_list = df_list[0]["Timestamp"].tolist()
    # compares the first and last timestamp
    first_date = date_list[0]
    last_date = date_list[-1]
    date_format_list = ["%Y/", "%m/", "%d", " ", "%H:", "%M:", "%S"]
    # go character by character, comparing digits until they differ,
    # then formatting appropriately
    for i in range(len(first_date)):
        curr_first_date = first_date[i]
        curr_last_date = last_date[i]
        # if the current year, month, day, etc. is not the same,
        # then print the remaining timestamps on the axis
        if curr_first_date != curr_last_date:
            break
        if (curr_first_date
                == "/" or curr_first_date == ":" or curr_last_date == " "):
            del date_format_list[0]
    date_format_str = "".join(date_format_list)
    # returns a list of reformatted timestamp strings that will be plotted
    return [datetime.strptime(date, "%Y/%m/%d %H:%M:%S").
            strftime(date_format_str) for date in date_list]
