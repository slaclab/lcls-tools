from typing import Any, Optional
from lcls_tools.common.devices.wire import Wire
from lcls_tools.common.devices.reader import create_lblm
from lcls_tools.common.data.fit.projection import ProjectionFit
from lcls_tools.common.measurements.measurement import Measurement
import time
import edef
import os
from pydantic import SerializeAsAny, BaseModel, ConfigDict, model_validator
from lcls_tools.common.measurements.utils import NDArrayAnnotatedType
from lcls_tools.common.measurements.tmit_loss import TMITLoss
import numpy as np
import pandas as pd
from typing_extensions import Self


class WireBeamProfileMeasurementResult(BaseModel):
    """
    Stores the results of a wire beam profile measurement.

    Attributes:
        position_data (np.ndarray): Wire position (um) data for each plane.
        detector_data (np.ndarray): Detector responses (loss counts) separated by plane.
        raw_data (np.ndarray): Raw unprocessed BSA data for all devices.
        metadata (Any): Metadata describing the measurement setup and parameters.
        fit_result (np.ndarray): Fit results from beam profile projections.
        rms_sizes (dict): RMS  beamsizes (sigma values) extracted from fits.

    Config:
        arbitrary_types_allowed: Allows use of non-standard types like np.ndarray.
        extra: Forbids extra fields not explicitly defined in the model.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    position_data: NDArrayAnnotatedType
    detector_data: NDArrayAnnotatedType
    raw_data: NDArrayAnnotatedType
    metadata: SerializeAsAny[Any]
    fit_result: NDArrayAnnotatedType
    rms_sizes: dict


class WireBeamProfileMeasurement(Measurement):
    """
    Performs a wire scan measurement and fits beam profiles.

    Attributes:
        name (str): Name identifier for the measurement type.
        device (Wire): Wire device used to perform the scan.
        beampath (str): Beamline path identifier for buffer and device selection.
        beam_fit (BaseModel): Model used to fit beam profiles (default: ProjectionFit).
        fit_profile (bool): Flag to enable or disable fitting of the beam profiles.
    """

    name: str = "beam_profile"
    my_wire: Wire
    beampath: str
    beam_fit: BaseModel = ProjectionFit
    fit_profile: bool = True

    # Extra fields to be set after validation
    my_buffer: Optional[edef.BSABuffer] = None
    devices: Optional[dict] = None
    data: Optional[dict] = None
    bsa_data_by_plane: Optional[dict] = None

    @model_validator(mode="after")
    def run_setup(self) -> Self:
        if self.my_buffer is None:
            print("Reserving BSA Buffer...")
            self.my_buffer = self.reserve_buffer()
            print(f"Reserved BSA Buffer {self.my_buffer.number}")
        print("Creating device dictionary...")
        self.devices = self.create_device_dictionary()
        return self

    def measure(self) -> WireBeamProfileMeasurementResult:
        """
        Perform a wire scan measurement and return processed beam profile data.

        Reserves a buffer, moves the wire, collects detector data, fits beam
        profiles, converts fit results to physical units, and extracts RMS
        beam sizes.

        Returns:
            WireBeamProfileMeasurementResult: Structured results including
            position data, detector responses, fit parameters, and RMS sizes.
        """
        # TODO: Jitter Correction
        # TODO: Charge Normalization

        # Start the buffer and move the wire
        self.scan_with_wire()

        # Get position and detector data from the buffer
        self.get_bsa_data()

        # Determine the profile range indices
        # e.g., u range = (13000, 18000) -> position_data[100:250]
        idxs = self.get_profile_ranges()

        # Separate detector data by profile
        self.split_data_by_plane(idxs)

        # Fit detector data by profile
        fit_result_idx = self.fit_data_by_plane()

        # Convert fit parameters from index-space to physical-space
        fit_result_phys = self.convert_fit_to_physical(fit_result_idx)

        # Make RMS sizes object for Emittance measurements
        rms_sizes = self.get_rms_sizes(fit_result_phys)

        return WireBeamProfileMeasurementResult(
            position_data=self.data[f"{self.my_wire.name}"],
            detector_data=self.bsa_data_by_plane,
            raw_data=self.data,
            fit_result=fit_result_phys,
            rms_sizes=rms_sizes,
            metadata=["TEST"],  # self.model_dump() threw error #TODO
        )

    def reserve_buffer(self):
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
        if self.beampath.startswith("SC"):
            # Reserve BSA buffer for SC destinations
            my_buffer = edef.BSABuffer("LCLS Tools Wire Scan", user=user)
            my_buffer.n_measurements = 1600

            # Set mode to 'Inclusion'
            my_buffer.destination_mode = 2

            # Clear all previous destinations
            my_buffer.clear_masks()

            # Set appropriate destination mask for chosen beampath
            my_buffer.destination_masks = [self.beampath]
            return my_buffer

        elif self.beampath.startswith("CU"):
            # Reserve eDef buffer for CU destinations
            my_buffer = edef.EventDefinition("LCLS Tools Wire Scan", user=user)
            my_buffer.n_measurements = 1600
            return my_buffer
        else:
            raise BufferError

    def create_device_dictionary(self):
        """
        Creates a device dictionary for a wire scan setup.

        Includes the wire device and any associated LBLM devices
        based on metadata.

        Parameters:
            my_wire (Wire): An lcls-tools Wire object.
        Returns:
            dict: A mapping of device names to device objects.
        """
        devices = {f"{self.my_wire.name}": self.my_wire}
        for lblm in self.my_wire.metadata.lblms:
            if lblm == "TMITLOSS":
                devices["TMITLOSS"] = TMITLoss(
                    my_buffer=self.my_buffer,
                    my_wire=self.my_wire,
                    beampath=self.beampath,
                    region=self.my_wire.area,
                )
            else:
                devices[lblm] = create_lblm(area=f"{self.my_wire.area}", name=lblm)
        return devices

    def scan_with_wire(self):
        """
        Starts the buffer and wire scan with brief delays.

        Delays ensure the buffer is active before the scan begins
        and allows time for the buffer to update its state.
        """
        # Start wire scan
        print("Starting wire motion procedure...")
        self.my_wire.start_scan()

        # Give wire time to initialize
        print("Waiting for wire initialization...")
        time.sleep(3)

        # Start buffer
        print("Starting BSA buffer...")
        self.my_buffer.start()

        # Wait briefly before checking buffer 'ready'
        time.sleep(0.1)

    def get_bsa_data(self):
        """
        Collects wire scan and detector data after buffer completes.

        Waits for buffer to finish, then gathers data from the wire
        and associated devices. Adds TMIT loss if in supported area.
        Releases the buffer after data collection.

        Returns:
            dict: Collected data keyed by device name.
        """
        self.data = {}
        # Wait for buffer 'ready'
        while not self.my_buffer.is_acquisition_complete():
            time.sleep(0.1)
            print(f"Wire position: {self.my_wire.motor_rbv}")
        print("BSA buffer data acquisition complete!")

        # Get buffer data and put into results dictionary
        self.data[f"{self.my_wire.name}"] = self.my_wire.position_buffer(self.my_buffer)

        if self.beampath.startswith("SC"):
            for lblm in self.my_wire.metadata.lblms:
                if lblm == "TMITLOSS":
                    print("Calculating TMIT Loss...")
                    self.data["TMITLOSS"] = self.devices["TMITLOSS"].measure()
                else:
                    self.data[lblm] = self.devices[lblm].fast_buffer(self.my_buffer)
        elif self.beampath.startswith("CU"):
            # CU LBLMs use "QDCRAW" signal
            self.data.update(
                {
                    lblm: self.devices[lblm].qdcraw_buffer(self.my_buffer)
                    for lblm in self.my_wire.metadata.lblms
                }
            )

        # Release EDEF/BSA
        print("Releasing BSA buffer")
        self.my_buffer.release()

    def get_profile_ranges(self):
        """
        Finds sequential scan indices within each plane's position range.

        Filters wire position data to identify index ranges for x, y, and u
        planes, excluding non-continuous points like wire retractions.

        Returns:
            dict: Plane keys ('x', 'y', 'u') with lists of index arrays.
        """
        # Get wire data to detemine plane indices
        position_data = self.data[f"{self.my_wire.name}"]

        # Hold plane ranges
        ranges = {}

        # Hold sequential indices (avoid catching return wires)
        seq_idxs = {}

        for plane in ["x", "y", "u"]:
            # Get range methods e.g. x_range()
            method_name = f"{plane}_range"
            ranges[plane] = getattr(self.my_wire, method_name)

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
            seq_idxs = {k: v for k, v in seq_idxs.items()}

        return seq_idxs

    def split_data_by_plane(self, seq_idxs):
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
        self.bsa_data_by_plane = {plane: {} for plane in planes}
        devices = list(self.data.keys())

        for device in devices:
            # TMIT Loss returns as a pd.Series, so convert to numpy first
            if isinstance(self.data[device], pd.Series):
                self.data[device] = self.data[device].to_numpy()
            device_data = self.data[device]
            for plane in planes:
                # Separate out device data by plane
                idx = seq_idxs.get(plane)
                device_plane_data = device_data[idx]
                # Flatten data so it is guaranteed to be 1D
                self.bsa_data_by_plane[plane][device] = device_plane_data.flatten()

    def fit_data_by_plane(self):
        """
        Fits detector data for each plane and device.

        Applies beam fitting to x, y, and u projections
        for all devices in the detector data.

        Returns:
            dict: Fit results organized by plane and device.
        """
        # Get list of planes from data set
        planes = list(self.bsa_data_by_plane.keys())
        fit_result = {plane: {} for plane in planes}

        for plane in planes:
            # Get list of devices (LBLMs)
            devices = list(self.bsa_data_by_plane[plane].keys())

            for device in devices:
                # Don't do fit on wire position!
                if device == self.my_wire.name:
                    pass
                else:
                    # Instantiate beam_fit
                    proj_fit = self.beam_fit()
                    proj_data = self.bsa_data_by_plane[plane][device]
                    fit_result[plane][device] = proj_fit.fit_projection(proj_data)

        return fit_result

    def convert_fit_to_physical(self, fit_result):
        """
        Convert Gaussian fit results from index space to physical position.

        Updates the 'mean' and 'sigma' of each fit using the average spacing
        between position values and the starting position of the scan.
        """
        # Loop over each scan plane (e.g., 'x', 'y', 'u')
        planes = list(self.bsa_data_by_plane.keys())
        for plane in planes:
            devices = list(self.bsa_data_by_plane[plane].keys())
            # Loop over each device in the current plane
            for device in devices:
                if device == self.my_wire.name:
                    pass
                else:
                    # Get the starting physical position of the wire scan
                    posn_start = self.bsa_data_by_plane[plane][self.my_wire.name][0]

                    # Estimate the spacing between position samples
                    posn_diff = np.mean(
                        np.diff(self.bsa_data_by_plane[plane][self.my_wire.name])
                    )

                    # Convert the fitted mean from index to physical position
                    mean_phys = (
                        fit_result[plane][device]["mean"] * posn_diff + posn_start
                    )

                    # Convert the fitted sigma (standard deviation) to physical units
                    sigma_phys = fit_result[plane][device]["sigma"] * posn_diff

                    # Update the fit result with physical values
                    fit_result[plane][device]["mean"] = mean_phys
                    fit_result[plane][device]["sigma"] = sigma_phys

        return fit_result

    def get_rms_sizes(fit_result_phys):
        """
        Extract RMS beam sizes ('sigma') from nested fit results.

        Args:
            fit_result_phys (dict): Nested dictionary of the format
                fit_result[plane][device]['sigma'], containing Gaussian fit data.

        Returns:
            dict: Dictionary where the keys are devices (detectors) and the values
            are lists of the form [x_rms, y_rms].
        """
        rms_sizes = {}

        for plane in fit_result_phys:
            for device in fit_result_phys[plane]:
                sigma = fit_result_phys[plane][device]["sigma"]
                if device not in rms_sizes:
                    rms_sizes[device] = [None, None]
                if plane == "x":
                    rms_sizes[device][0] = sigma
                if plane == "y":
                    rms_sizes[device][1] = sigma
        return rms_sizes
