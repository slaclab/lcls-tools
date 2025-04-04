from lcls_tools.common.devices.reader import create_bpm
from lcls_tools.common.measurements.measurement import Measurement
import meme.names
import pandas as pd


class TMITLoss(Measurement):
    name: str = "TMIT Loss Beam Size"

    def __init__(self, my_buffer, **kwargs):
        super().__init__(**kwargs)
        self.my_buffer = my_buffer

    def find_bpms(self, beampath):
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

        bpms_elements = meme.names.list_elements("BPMS:%TMIT",
                                                 tag=beampath, sort_by="z")
        bpms_devices = meme.names.list_devices("BPMS:%TMIT",
                                               tag=beampath, sort_by="z")
        areas_bpn = [device.split(":")[1] for device in bpms_devices]
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
        for index, row in bpms_elements.iterrows():
            element = row['Element']
            area = row['Area']
            bpm_obj_dict[element] = create_bpm(name=element, area=area)
        return bpm_obj_dict

    def get_bpm_data(self, bpm_obj_dict, my_buffer):
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

        for element, bpm in bpm_obj_dict.items():
            try:
                bpm_data = bpm.tmit_buffer(my_buffer)
                data[f"{element}"] = bpm_data
            except BufferError:
                data[f"{element}"] = None

        df = pd.DataFrame(data)
        return df.T

    def get_bpm_idx(self, region, bpms_devices):
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
        valid_regions = {"HTR", "DIAG0", "COL1", "EMIT2", "BYP", "SPD", "LTUS"}
        if region not in valid_regions:
            raise ValueError(f"Invalid region '{region}'."
                             "Must be one of {valid_regions}")

        if region == "HTR":
            bpms_before_wire = ["BPMS:GUNB:925", "BPMS:HTR:120",
                                "BPMS:HTR:320"]
            bpms_after_wire = ["BPMS:HTR:760", "BPMS:HTR:830",
                               "BPMS:HTR:860", "BPMS:HTR:960"]
        elif region == "DIAG0":
            bpms_before_wire = ["BPMS:DIAG0:190", "BPMS:DIAG0:210",
                                "BPMS:DIAG0:230", "BPMS:DIAG0:270",
                                "BPMS:DIAG0:285", "BPMS:DIAG0:330",
                                "BPMS:DIAG0:370", "BPMS:DIAG0:390"]
            bpms_after_wire = ["BPMS:DIAG0:470", "BPMS:DIAG0:520"]
        elif region == "COL1":
            bpms_before_wire = ["BPMS:BC1B:125", "BPMS:BC1B:440",
                                "BPMS:COL1:120", "BPMS:COL1:260",
                                "BPMS:COL1:280", "BPMS:COL1:320"]
            bpms_after_wire = ["BPMS:BPN27:400", "BPMS:BPN28:200",
                               "BPMS:BPN28:400", "BPMS:SPD:135",
                               "BPMS:SPD:255", "BPMS:SPD:340",
                               "BPMS:SPD:420", "BPMS:SPD:525"]
        elif region == "EMIT2":
            bpms_before_wire = ["BPMS:BC2B:150", "BPMS:BC2B:530",
                                "BPMS:EMIT2:150", "BPMS:EMIT2:300"]
            bpms_after_wire = ["BPMS:SPS:780", "BPMS:SPS:830",
                               "BPMS:SPS:840", "BPMS:SLTS:150",
                               "BPMS:SLTS:430", "BPMS:SLTS:460"]
        elif region == "BYP":
            bpms_before_wire = ["BPMS:L3B:3583", "BPMS:EXT:351",
                                "BPMS:EXT:748", "BPMS:DOG:120",
                                "BPMS:DOG:135", "BPMS:DOG:150",
                                "BPMS:DOG:200", "BPMS:DOG:215",
                                "BPMS:DOG:230", "BPMS:DOG:280",
                                "BPMS:DOG:335", "BPMS:DOG:355",
                                "BPMS:DOG:405"]
            bpms_after_wire = ["BPMS:BPN23:400", "BPMS:BPN24:400",
                               "BPMS:BPN25:400", "BPMS:BPN26:400",
                               "BPMS:BPN27:400", "BPMS:BPN28:200",
                               "BPMS:BPN28:400", "BPMS:SPD:135",
                               "BPMS:SPD:255", "BPMS:SPD:340",
                               "BPMS:SPD:420", "BPMS:SPD:525",
                               "BPMS:SPD:570", "BPMS:SPD:700",
                               "BPMS:SPD:955"]
        elif region == "SPD":
            bpms_before_wire = ["BPMS:SPD:135", "BPMS:SPD:255",
                                "BPMS:SPD:340", "BPMS:SPD:420",
                                "BPMS:SPD:525", "BPMS:SPD:570"]
            bpms_after_wire = ["BPMS:SPD:700", "BPMS:SPD:955",
                               "BPMS:SLTD:625"]
        elif region == "LTUS":
            bpms_before_wire = ["BPMS:BPN27:400", "BPMS:BPN28:200",
                                "BPMS:BPN28:400", "BPMS:SPD:135",
                                "BPMS:SPD:255", "BPMS:SPD:340",
                                "BPMS:SPS:572", "BPMS:SPS:580",
                                "BPMS:SPS:640", "BPMS:SPS:710",
                                "BPMS:SPS:770", "BPMS:SPS:780",
                                "BPMS:SPS:830", "BPMS:SPS:840",
                                "BPMS:SLTS:150"]
            bpms_after_wire = ["BPMS:DMPS:381", "BPMS:DMPS:502",
                               "BPMS:DMPS:693"]

        # Create a lookup dictionary for index mapping
        idx_map = {value: idx for idx, value in enumerate(bpms_devices)}

        # Find indices of BPMs before and after the wire
        idx_before = [idx_map[item] for item in bpms_before_wire
                      if item in idx_map]
        idx_after = [idx_map[item] for item in bpms_after_wire
                     if item in idx_map]

        return idx_before, idx_after

    def calc_tmit_loss(self, df, idx_before, idx_after):
        """
        Calculate the Transmission Monitor Intensity (TMIT) loss.

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
        ironed_before = df_ironed.iloc[idx_before, :]
        mean_iron_before = ironed_before.mean()

        # Normalize by mean TMIT before the wire
        df_normed = df_ironed.div(mean_iron_before, axis=1)

        # Compute mean ratios before and after the wire
        normed_before = df_normed.iloc[idx_before,]
        normed_after = df_normed.iloc[idx_after]

        mean_before = normed_before.mean()
        mean_after = normed_after.mean()

        # Compute TMIT Loss percentage
        tmit_loss = (mean_after - mean_before) * 100
        return tmit_loss

    def measure(self, beampath, region):
        """
        Compute the Transmission Monitor Intensity (TMIT) loss for a given
        beam path and region.

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
        bpms_elements, bpms_devices = self.find_bpms(beampath)
        idx_before, idx_after = self.get_bpm_idx(region, bpms_devices)
        bpm_objs = self.create_bpms(bpms_elements)

        data = self.get_bpm_data(bpm_objs, self.my_buffer)

        tmit_loss = self.calc_tmit_loss(data, idx_before, idx_after)
        return tmit_loss
