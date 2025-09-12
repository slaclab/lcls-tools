from lcls_tools.common.devices.reader import create_bpm
from lcls_tools.common.measurements.measurement import Measurement
import meme.names
import pandas as pd
import numpy as np
from edef import BSABuffer
from lcls_tools.common.devices.wire import Wire
from pydantic import model_validator
from typing import Optional


class TMITLoss(Measurement):
    name: str = "TMIT Loss Beam Size"
    my_buffer: BSABuffer
    beampath: str
    region: str
    my_wire: Wire

    # Extra fields to be set after validation
    idx_before: Optional[list] = None
    idx_after: Optional[list] = None
    bpms: Optional[dict] = None

    @model_validator(mode="after")
    def run_setup(self) -> "TMITLoss":
        bpms_elements, bpms_devices = self.find_bpms()
        self.idx_before, self.idx_after = self.get_bpm_idx(bpms_devices)
        self.bpms = self.create_bpms(bpms_elements)
        return self

    def measure(self):
        """
        Compute the TMIT loss for a given beam path and region.

        This method orchestrates the full process of acquiring BPM data,
        normalizing it, and calculating TMIT loss by:
        - Reserving a data buffer.
        - Retrieving BPM elements and device names.
        - Identifying BPM indices before and after the wire.
        - Creating BPM objects.
        - Collecting TMIT data.
        - Computing the TMIT loss.

        Args:
            beampath (str): The beam path used to filter BPM elements.
            region (str): The region of interest, which determines the BPMs
                          used for before/after wire measurements.

        Returns:
            pd.Series: A Series representing the percentage TMIT loss for each
                       time sample.
        """
        # Retrieve data from BSA buffer
        data = self.get_bpm_data()

        # Calculate TMIT Loss
        tmit_loss_pd = self.calc_tmit_loss(data)
        tmit_loss = tmit_loss_pd.to_numpy()
        return tmit_loss

    def find_bpms(self):
        """
        Retrieve BPM elements and their corresponding EPICS names for a
        given beam path.

        This method queries BPM elements and devices using the `meme.names`
        module.  It extracts the area from each BPM device name and replaces
        any area containing "BPN" with "BYP" for proper YAML file lookup.

        Args:
            beampath (str): The beam path tag used to filter BPM elements
            and devices.

        Returns:
            tuple: A tuple containing:
                - pd.DataFrame: A DataFrame with BPM elements and their
                                corresponding areas.
                - list: A list of BPM device names.
        """
        # List of BPM MAD names based on beampath
        bpms_elements = meme.names.list_elements(
            "BPMS:%TMIT", tag=self.beampath, sort_by="z"
        )

        # List of BPM EPICS names based on beampath
        bpms_devices = meme.names.list_devices(
            "BPMS:%TMIT", tag=self.beampath, sort_by="z"
        )

        # Make Dataframe with two columns: First is the Element (MAD) name
        # Second column is the area
        areas_bpn = [device.split(":")[1] for device in bpms_devices]
        # If EPICS name uses "BPN" for area, instead use "BYP"
        areas = ["BYP" if "BPN" in item else item for item in areas_bpn]
        bpms_elements = pd.DataFrame({"Element": bpms_elements, "Area": areas})
        return bpms_elements, bpms_devices

    def create_bpms(self, bpms_elements):
        """
        Create BPM device objects for a given set of BPM elements.

        This method iterates through a DataFrame of BPM elements
        and their corresponding areas, creating BPM objects
        using the `create_bpm` function.

        Args:
            bpms_elements (pd.DataFrame): A DataFrame containing BPM
                                          element names and their
                                          associated areas. Must
                                          have columns:
                                          - 'Element' (str): The BPM
                                            element name.
                                          - 'Area' (str): The area
                                            associated with the BPM.

        Returns:
            dict: A dictionary where the keys are BPM element
            names and the values are the corresponding BPM
            objects created using `create_bpm`.
        """
        bpm_obj_dict = {}

        # Iterate through Dataframe of Elements and Areas
        for _, row in bpms_elements.iterrows():
            element = row["Element"]
            area = row["Area"]

            # Create an lcls-tools BPM object and append to dictionary
            bpm = create_bpm(name=element, area=area)
            if bpm is not None:
                bpm_obj_dict[element] = bpm

        if bpm_obj_dict:
            return bpm_obj_dict
        else:
            raise LookupError("No BPM objects could be created.")

    def get_bpm_data(self):
        """
        Retrieve TMIT buffer data for a set of BPMs.

        This method iterates through a dictionary of BPM objects and attempts
        to fetch their TMIT buffer data using a specified buffer. If data
        retrieval fails for a BPM, it is assigned a `None` value.

        Args:
            bpm_obj_dict (dict): A dictionary where keys are BPM element
                                 names (str) and values are BPM objects.
            my_buffer (BSABuffer): The buffer used to retrieve TMIT data for
                                 each BPM.

        Returns:
            pd.DataFrame: A transposed DataFrame where:
                          - Rows correspond to BPM elements.
                          - Columns contain the retrieved TMIT buffer data.
        """
        data = {}
        n_m = self.my_buffer.n_measurements

        for element, bpm in self.bpms.items():
            try:
                # Get data from BSA buffer
                bpm_data = bpm.tmit_buffer(self.my_buffer)
                if bpm_data is not None and len(bpm_data) > 0:
                    # BSA can return fewer points than requested.
                    # Pad with last value if difference is small.
                    if bpm_data.size < n_m:
                        pad_len = n_m - bpm_data.size
                        # 8 pads is 0.5% of the minimum buffer size 1600
                        # so only pad if small difference
                        if pad_len <= 8:
                            padding = np.full(pad_len, bpm_data[-1])
                            bpm_data = np.concatenate([bpm_data, padding])
                        if pad_len > 8:
                            raise BufferError(
                                f"BPM {element} returned {bpm_data.size} points, expected {n_m}."
                            )
                    data[element] = bpm_data
                else:
                    data[element] = None
            except (BufferError, TypeError):
                data[element] = None

        valid_lengths = [len(v) for v in data.values() if v is not None]
        if not valid_lengths:
            raise ValueError("No valid BPM data could be retrieved.")
        min_len = min(valid_lengths)

        for key, val in data.items():
            if val is None or len(val) < min_len:
                data[key] = np.zeros(min_len)
            else:
                data[key] = val[:min_len]

        df = pd.DataFrame(data)
        return df.T

    def get_bpm_idx(self, bpms_devices):
        """
        Retrieve the index positions of BPMs before and after the wire for a
        given region.

        This method selects predefined BPMs based on the specified region and
        finds their corresponding indices in `bpms_devices`.

        Args:
            region (str): The region of interest. Must be one of:
                          - "HTR", "DIAG0", "COL1", "EMIT2", "BYP",
                            "SPD", "LTUS".
            bpms_devices (list): A list of BPM device names.

        Returns:
            tuple: A tuple containing:
                - list: Indices of BPMs located **before** the wire.
                - list: Indices of BPMs located **after** the wire.
        """
        # Define valid regions
        tmit_regions = {"HTR", "DIAG0", "COL1", "EMIT2", "DOG", "BYP", "SPD", "LTUS"}
        if self.region not in tmit_regions:
            raise ValueError(
                f"Invalid region '{self.region}'. Must be one of {{valid_regions}}"
            )

        bpms_before_wire = self.my_wire.metadata.bpms_before_wire
        bpms_after_wire = self.my_wire.metadata.bpms_after_wire

        # Create a lookup dictionary for index mapping
        idx_map = {value: idx for idx, value in enumerate(bpms_devices)}

        # Find indices of BPMs before and after the wire
        idx_before = [idx_map[item] for item in bpms_before_wire if item in idx_map]
        idx_after = [idx_map[item] for item in bpms_after_wire if item in idx_map]

        return idx_before, idx_after

    def calc_tmit_loss(self, df):
        """
        Calculate the TMIT loss.

        This method normalizes the TMIT data by computing row-wise medians,
        then standardizes it relative to BPMs before a wire. The loss is
        computed as the percentage change in mean TMIT values before and
        after the wire.

        Args:
            df (pd.DataFrame): A DataFrame containing TMIT values, where
                               rows correspond to BPMs and columns to
                               time samples.
            idx_before (list): List of row indices corresponding to BPMs
                               before the wire.
            idx_after (list): List of row indices corresponding to BPMs
                              after the wire.

        Returns:
            pd.Series: A Series representing the percentage TMIT loss for each
                       time sample.
        """
        # Compute row-wise medians and normalize the DataFrame
        row_medians = df.median(axis=1)
        df_ironed = df.div(row_medians, axis=0)

        # Compute mean ironed TMIT for BPMs before the wire
        ironed_before = df_ironed.iloc[self.idx_before, :]
        mean_iron_before = ironed_before.mean()

        # Normalize by mean TMIT before the wire
        df_normed = df_ironed.div(mean_iron_before, axis=1)

        # Compute mean ratios before and after the wire
        normed_before = df_normed.iloc[self.idx_before]
        normed_after = df_normed.iloc[self.idx_after]

        mean_before = normed_before.mean()
        mean_after = normed_after.mean()

        # Compute TMIT Loss percentage
        tmit_loss = (mean_before - mean_after) * 100
        return tmit_loss
