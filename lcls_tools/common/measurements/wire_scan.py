from typing import Any, Optional, Dict, Tuple
from lcls_tools.common.devices.wire import Wire
from lcls_tools.common.devices.reader import create_lblm
from lcls_tools.common.data.fit.projection import ProjectionFit
from lcls_tools.common.measurements.measurement import Measurement
import time
from datetime import datetime
import edef
import os
from pydantic import SerializeAsAny, BaseModel, ConfigDict, model_validator
from lcls_tools.common.measurements.utils import NDArrayAnnotatedType
from lcls_tools.common.measurements.tmit_loss import TMITLoss
import numpy as np
from typing_extensions import Self


class MeasurementMetadata(BaseModel):
    wire_name: str
    area: str
    beampath: str
    detectors: list[str]
    default_detector: str
    scan_ranges: Dict[str, Tuple[int, int]]
    timestamp: datetime
    notes: Optional[str] = None


class DetectorMeasurement(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    values: NDArrayAnnotatedType
    units: str | None = None
    label: str | None = None


class PlaneMeasurement(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    positions: NDArrayAnnotatedType
    detectors: dict[str, DetectorMeasurement]
    profile_idxs: NDArrayAnnotatedType


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
    planes: Dict[str, PlaneMeasurement]
    raw_data: Dict[str, Any]
    fit_result: NDArrayAnnotatedType
    rms_sizes: Dict[str, Tuple[float, float]]
    metadata: SerializeAsAny[Any]


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
        self.data = self.get_data_from_bsa()

        # Determine the profile range indices
        # e.g., u range = (13000, 18000) -> position_data[100:250]
        profile_idxs = self.get_profile_range_indices()

        # Separate detector data by profile
        self.plane_measurements = self.organize_data_by_plane(profile_idxs)

        # Fit detector data by profile
        fit_result, rms_sizes = self.fit_data_by_plane()

        # Create measurement metadata object
        metadata = self.create_metadata()

        return WireBeamProfileMeasurementResult(
            planes=self.plane_measurements,
            raw_data=self.data,
            fit_result=fit_result,
            rms_sizes=rms_sizes,
            metadata=metadata,
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
        for lblm_str in self.my_wire.metadata.lblms:
            name, area = lblm_str.split(":")
            if name == "TMITLOSS":
                devices["TMITLOSS"] = TMITLoss(
                    my_buffer=self.my_buffer,
                    my_wire=self.my_wire,
                    beampath=self.beampath,
                    region=self.my_wire.area,
                )
            else:
                devices[name] = create_lblm(area=area, name=name)
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

    def get_data_from_bsa(self):
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
        while not self.my_buffer.is_acquisition_complete():
            time.sleep(0.1)
            print(f"Wire position: {self.my_wire.motor_rbv}")
        print("BSA buffer data acquisition complete!")

        if self.beampath.startswith("SC"):
            for device in self.devices:
                if device == self.my_wire.name:
                    data[device] = self.my_wire.position_buffer(self.my_buffer)
                elif device == "TMITLOSS":
                    data[device] = self.devices[device].measure()
                else:
                    data[device] = self.devices[device].fast_buffer(self.my_buffer)
        elif self.beampath.startswith("CU"):
            # CU LBLMs use "QDCRAW" signal
            data.update(
                {
                    lblm: self.devices[lblm].qdcraw_buffer(self.my_buffer)
                    for lblm in self.my_wire.metadata.lblms
                }
            )

        # Release EDEF/BSA
        print("Releasing BSA buffer")
        self.my_buffer.release()

        return data

    def get_profile_range_indices(self):
        """
        Finds sequential scan indices within each plane's position range.

        Filters wire position data to identify index ranges for x, y, and u
        planes, excluding non-continuous points like wire retractions.

        Returns:
            dict: Plane keys ('x', 'y', 'u') with lists of index arrays.
        """
        # Get wire data to detemine plane indices
        position_data = self.data[self.my_wire.name]

        # Hold plane ranges
        ranges = {}

        # Hold sequential indices (avoid catching return wires)
        profile_idxs = {}

        active_planes = []
        if self.my_wire.use_x_wire:
            active_planes.append("x")
        if self.my_wire.use_y_wire:
            active_planes.append("y")
        if self.my_wire.use_u_wire:
            active_planes.append("u")

        for plane in active_planes:
            # Get range methods e.g. x_range()
            method_name = f"{plane}_range"
            ranges[plane] = getattr(self.my_wire, method_name)

            # Get indices of when position is within a range
            idx = np.where(
                (position_data >= ranges[plane][0])
                & (position_data <= ranges[plane][1])
            )[0]

            pos = position_data[idx]
            mono_mask = np.diff(pos) >= 0
            mono_mask = np.concatenate(([True], mono_mask))

            mono_idx = idx[mono_mask]

            profile_idxs[plane] = mono_idx

        return profile_idxs

    def organize_data_by_plane(self, profile_idxs):
        """
        Organizes detector data by scan plane for each device.

        Uses sequential indices to separate full device data into
        x, y, and u plane datasets.

        Returns:
            dict: Nested dict with planes as keys and device data per plane.
        """

        planes = list(profile_idxs.keys())
        devices = list(self.devices.keys())

        plane_measurements = {}

        for plane in planes:
            idx = profile_idxs.get(plane)
            detectors = {}

            for device in devices:
                data_slice = self.data[device][idx]
                if device == self.my_wire.name:
                    positions = data_slice
                else:
                    units = "%% beam loss" if device == "TMITLOSS" else "counts"
                detectors[device] = DetectorMeasurement(
                    values=data_slice, units=units, label=device
                )

            plane_measurements[plane] = PlaneMeasurement(
                positions=positions, detectors=detectors, profile_idxs=idx
            )

        return plane_measurements

    def fit_data_by_plane(self):
        """
        Fits detector data for each plane and device.

        Applies beam fitting to x, y, and u projections
        for all devices in the detector data.

        Returns:
            dict: Fit results organized by plane and device.
        """
        # Get list of planes from data set
        planes = list(self.plane_measurements.keys())
        fit_result = {plane: {} for plane in planes}
        devices = list(self.data.keys())

        for plane in planes:
            wire_posn = self.plane_measurements[plane].positions
            posn_start = wire_posn[0]
            posn_diff = np.mean(np.diff(wire_posn))

            for device in devices:
                if device == self.my_wire.name:
                    continue
                proj_fit = self.beam_fit()
                proj_data = self.plane_measurements[plane].detectors[device].values
                fit_result[plane][device] = proj_fit.fit_projection(proj_data)

                mean_idx = fit_result[plane][device]["mean"]
                fit_result[plane][device]["mean"] = mean_idx * posn_diff + posn_start

                sigma_idx = fit_result[plane][device]["sigma"]
                fit_result[plane][device]["sigma"] = sigma_idx * posn_diff

                x_fits = fit_result["x"]
                y_fits = fit_result["y"]

        rms_sizes = {
            device: (x_fits[device]["sigma"], y_fits[device]["sigma"])
            for device in devices
        }

        return fit_result, rms_sizes

    def create_metadata(self):
        # Make additional metadata
        sample_plane = next(iter(self.plane_measurements.values()))
        detectors = list(sample_plane.keys())

        scan_ranges = {
            "x": self.my_wire.x_range,
            "y": self.my_wire.y_range,
            "u": self.my_wire.u_range,
        }

        metadata = MeasurementMetadata(
            wire_name=self.my_wire.name,
            area=self.my_wire.area,
            beampath=self.beampath,
            detectors=detectors,
            default_detector=detectors[0],
            scan_ranges=scan_ranges,
            timestamp=datetime.now(),
            notes=None,
        )

        return metadata
