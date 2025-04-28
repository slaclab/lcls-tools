from typing import Any
from lcls_tools.common.devices.wire import Wire
from lcls_tools.common.devices.reader import create_lblm
from lcls_tools.common.data.fit.projection import ProjectionFit
from lcls_tools.common.measurements.measurement import Measurement
import time
import edef
import os
from pydantic import ConfigDict, SerializeAsAny, BaseModel
from lcls_tools.common.measurements.utils import NDArrayAnnotatedType
from lcls_tools.common.measurements.tmit_loss import TMITLoss
import numpy as np
import pandas as pd
import epics


class WireBeamProfileMeasurementResult(BaseModel):
    position_data: NDArrayAnnotatedType
    detector_data: NDArrayAnnotatedType
    raw_data: NDArrayAnnotatedType
    metadata: SerializeAsAny[Any]
    fit_result: NDArrayAnnotatedType
    rms_sizes: dict
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class WireBeamProfileMeasurement(Measurement):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str = "beam_profile"
    device: Wire
    beampath: str
    beam_fit: BaseModel = ProjectionFit
    fit_profile: bool = True

    def measure(self, beampath, my_wire) -> dict:
        """
        Perform a wire scan measurement.

        Parameters:
        - beam_path (str): The selected beam path determines which timing
          buffer to reserve.
        - my_wire (Wire): An lcls-tools wire object.

        Returns:
        dict: A dictionary containing the measured bunch charge values and
        additional statistics if multiple shots are taken.

        If n_shots is 1, the function returns a dictionary with the key
        "bunch_charge_nC" and the corresponding single measurement value.

        If n_shots is greater than 1, the function performs multiple
        measurements with the specified wait time and returns a dictionary
        with the key "bunch_charge_nC"  containing a list of measured
        values. Additionally, statistical information (mean, standard
        deviation, etc.) is included in the dictionary.
        """

        # TODO: Jitter Correction
        # TODO: Charge Normalization

        # Reserve a BSA/EDEF buffer
        my_buffer = self.reserve_buffer(beampath)

        # Create dictionary of devices for WS (WS + detectors)
        devices = self.create_device_dictionary(my_wire, my_buffer)

        # Start the buffer and move the wire
        self.scan_with_wire(my_wire, my_buffer)

        # Get position and detector data from the buffer
        data = self.get_bsa_data(my_wire, devices, beampath, my_buffer)

        # Determine the profile range indices
        # e.g., u range = (13000, 18000) -> position_data[100:250]
        idxs = self.get_profile_ranges(my_wire, data)

        # Separate detector data by profile
        bsa_data_by_plane = self.split_data_by_plane(idxs, data)

        # Fit detector data by profile
        fit_result_idx = self.fit_data_by_plane(bsa_data_by_plane)

        # Convert fit parameters from index-space to physical-space
        fit_result_phys = self.convert_fit_to_physical(
            my_wire, bsa_data_by_plane, fit_result_idx
        )

        rms_sizes = self.get_rms_sizes(fit_result_phys)

        return WireBeamProfileMeasurementResult(
            position_data=bsa_data_by_plane[f"{my_wire.name}"],
            detector_data=bsa_data_by_plane,
            raw_data=data,
            fit_result=fit_result_phys,
            rms_sizes=rms_sizes,
            metadata=self.model_dump(),
        )

    def reserve_buffer(self, beampath):
        """
        Reserves an appropriate buffer based on the beampath.

        Uses BSABuffer for SC paths and EventDefinition for CU.
        Raises BufferError if beampath is unrecognized.

        Parameters:
            beampath (str): The beamline path identifier.

        Returns:
            object: A buffer object for data collection.
        """
        user = os.getlogin()
        if "SC" in beampath:
            # Reserve BSA buffer for SC destinations
            my_buffer = edef.BSABuffer("LCLS Tools Wire Scan", user=user)
            my_buffer.n_measurements = 1600

            # Set mode to 'Inclusion'
            my_buffer.destination_mode = 2

            # Clear all previous destinations
            dst_pv_prefix = "BSA:SYS0:1:" + str(my_buffer.number) + ":DST"
            for d in range(1, 6):
                clear_dst_pv = dst_pv_prefix + str(d)
                epics.caput(clear_dst_pv, 0)

            # Get DST index
            if beampath == "SC_DIAG0":
                dst_num = "1"
            elif beampath == "SC_BSYD":
                dst_num = "2"
            elif beampath == "SC_HXR":
                dst_num = "3"
            elif beampath == "SC_SXR":
                dst_num = "4"
            elif beampath == "SC_DASEL":
                dst_num = "5"

            # Set appropriate DST for chosen beampath
            set_dst_pv = dst_pv_prefix + dst_num
            epics.caput(set_dst_pv, 1)

            return my_buffer
        elif "CU" in beampath:
            # Reserve eDef buffer for CU destinations
            my_buffer = edef.EventDefinition("LCLS Tools Wire Scan", user=user)
            my_buffer.n_measurements = 1600
            return my_buffer
        else:
            raise BufferError

    def create_device_dictionary(self, my_wire, my_buffer):
        """
        Creates a device dictionary for a wire scan setup.

        Includes the wire device and any associated LBLM devices
        based on metadata.

        Parameters:
            my_wire (Wire): An lcls-tools Wire object.
        Returns:
            dict: A mapping of device names to device objects.
        """
        devices = {f"{my_wire.name}": my_wire}
        for lblm in my_wire.metadata.lblms:
            if lblm == "TMITLOSS":
                devices["TMITLOSS"] = TMITLoss(my_buffer=my_buffer)
            else:
                devices[lblm] = create_lblm(area=f"{my_wire.area}", name=lblm)
        return devices

    def scan_with_wire(self, my_wire, my_buffer):
        """
        Starts the buffer and wire scan with brief delays.

        Delays ensure the buffer is active before the scan begins
        and allows time for the buffer to update its state.
        """
        # Start wire scan
        my_wire.start_scan()

        # Give wire time to initialize
        time.sleep(3)

        # Start buffer
        my_buffer.start()

        # Wait briefly before checking buffer 'ready'
        time.sleep(0.1)

    def get_bsa_data(self, my_wire, devices, beampath, my_buffer):
        """
        Collects wire scan and detector data after buffer completes.

        Waits for buffer to finish, then gathers data from the wire
        and associated devices. Adds TMIT loss if in supported area.
        Releases the buffer after data collection.

        Returns:
            dict: Collected data keyed by device name.
        """
        data = {}
        # Wait for buffer 'ready'
        while not my_buffer.is_acquisition_complete():
            time.sleep(0.1)

        # Get buffer data and put into results dictionary
        data[f"{my_wire.name}"] = my_wire.position_buffer(my_buffer)

        if "SC" in beampath:
            for lblm in my_wire.metadata.lblms:
                if lblm == "TMITLOSS":
                    data["TMITLOSS"] = devices["TMITLOSS"].measure(
                        beampath=beampath, region=my_wire.area
                    )
                else:
                    data[lblm] = devices[lblm].fast_buffer(my_buffer)
        elif "CU" in beampath:
            # CU LBLMs use "QDCRAW" signal
            data.update(
                {
                    lblm: devices[lblm].qdcraw_buffer(my_buffer)
                    for lblm in my_wire.metadata.lblms
                }
            )

        # Release EDEF/BSA
        my_buffer.release()

        # Return dictionary of Wire position, LBLM waveforms, BPM waveforms
        return data

    def get_profile_ranges(self, my_wire, data):
        """
        Finds sequential scan indices within each plane's position range.

        Filters wire position data to identify index ranges for x, y, and u
        planes, excluding non-continuous points like wire retractions.

        Returns:
            dict: Plane keys ('x', 'y', 'u') with lists of index arrays.
        """
        # Get wire data to detemine plane indices
        position_data = data[f"{my_wire.name}"]

        # Hold plane ranges
        ranges = {}

        # Hold sequential indices (avoid catching return wires)
        seq_idxs = {}

        for plane in ["x", "y", "u"]:
            # Get range methods e.g. x_range()
            method_name = f"{plane}_range"
            ranges[plane] = getattr(my_wire, method_name)

            # Get indices of when position is within a range
            idx = np.where(
                (position_data >= ranges[plane][0])
                & (position_data <= ranges[plane][1])
            )[0]
            # Get only sequential non-decreasing indices to avoid picking up
            # wire retraction
            # data, ex. [100, 101, 102] not [101, 102, 103, 304, 305, 306]
            chunks = np.split(idx, np.where(np.diff(idx) != 1)[0] + 1)

            # Only keep chunks that are larger than 0
            seq_idxs[plane] = [chunk for chunk in chunks if len(chunk) > 0]

            # If two chunks are returned, only keep the first one
            if len(seq_idxs[plane]) >= 2:
                seq_idxs[plane] = seq_idxs[plane][0]

            # If an empty index is returned (e.g., wire didn't make
            # it to X plane), then an empty index list will be returned
            # If successful, a numpy.ndarray will be returned
            # If a list is returned, leave it out
            seq_idxs = {k: v for k, v in seq_idxs.items() if not isinstance(v, list)}

        return seq_idxs

    def split_data_by_plane(self, seq_idxs, data):
        """
        Organizes detector data by scan plane for each device.

        Uses sequential indices to separate full device data into
        x, y, and u plane datasets.

        Returns:
            dict: Nested dict with planes as keys and device data per plane.
        """
        # Make dictionary to hold individual datasets by plane
        # Ultimately will be detector_data[<plane>][<device_name>]
        planes = list(seq_idxs.keys())
        bsa_data_by_plane = {plane: {} for plane in planes}
        devices = list(data.keys())

        for device in devices:
            # TMIT Loss returns as a pd.Series, so convert to numpy first
            if isinstance(data[device], pd.Series):
                data[device] = data[device].to_numpy()
            device_data = data[device]
            for plane in planes:
                # Separate out device data by plane
                idx = seq_idxs.get(plane)
                device_plane_data = device_data[idx]
                # Flatten data so it is guaranteed to be 1D
                bsa_data_by_plane[plane][device] = device_plane_data.flatten()

        return bsa_data_by_plane

    def fit_data_by_plane(self, my_wire, bsa_data_by_plane):
        """
        Fits detector data for each plane and device.

        Applies beam fitting to x, y, and u projections
        for all devices in the detector data.

        Returns:
            dict: Fit results organized by plane and device.
        """
        # Get list of planes from data set
        planes = list(bsa_data_by_plane.keys())
        fit_result = {plane: {} for plane in planes}

        for plane in planes:
            # Get list of devices (LBLMs)
            devices = list(bsa_data_by_plane[plane].keys())

            # Don't do fit on wire position!
            devices.remove(my_wire.name)
            for device in devices:
                # Instantiate beam_fit
                proj_fit = self.beam_fit()
                proj_data = bsa_data_by_plane[plane][device]
                fit_result[plane][device] = proj_fit.fit_projection(proj_data)

        return fit_result

    def convert_fit_to_physical(self, my_wire, bsa_data_by_plane, fit_result):
        """
        Convert Gaussian fit results from index space to physical position.

        Updates the 'mean' and 'sigma' of each fit using the average spacing
        between position values and the starting position of the scan.
        """
        # Loop over each scan plane (e.g., 'x', 'y', 'u')
        planes = list(bsa_data_by_plane.keys())
        for plane in planes:
            devices = list(bsa_data_by_plane[plane].keys())
            # Loop over each device in the current plane
            for device in devices:
                # Get the starting physical position of the wire scan
                posn_start = bsa_data_by_plane[plane][my_wire.name][0]

                # Estimate the spacing between position samples
                posn_diff = np.mean(np.diff(bsa_data_by_plane[plane][my_wire.name]))

                # Convert the fitted mean from index to physical position
                mean_phys = fit_result[plane][device]["mean"] * posn_diff + posn_start

                # Convert the fitted sigma (standard deviation) to physical units
                sigma_phys = fit_result[plane][device]["sigma"] * posn_diff

                # Update the fit result with physical values
                fit_result[plane][device]["mean"] = mean_phys
                fit_result[plane][device]["sigma"] = sigma_phys

    def get_rms_sizes(fit_result_phys):
        """
        Extract RMS beam sizes ('sigma') from nested fit results.

        Args:
            fit_result_phys (dict): Nested dictionary of the format
                fit_result[plane][device]['sigma'], containing Gaussian fit data.

        Returns:
            dict: Nested dictionary with the same plane and device structure,
                containing only the 'sigma' values representing RMS beam sizes.
        """
        rms_sizes = {
            device: (
                fit_result_phys['x'][device]['sigma'],
                fit_result_phys['x'][device]['sigma']
            )
            for device in fit_result_phys['x']
        }
        return rms_sizes
