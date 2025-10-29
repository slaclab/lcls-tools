from pathlib import Path
from typing import Optional
from lcls_tools.common.devices.wire import Wire
from lcls_tools.common.devices.reader import create_lblm, create_pmt
import lcls_tools.common.model.gaussian as gaussian
import time
from datetime import datetime
import edef
from pydantic import ValidationError, model_validator
from lcls_tools.common.measurements.tmit_loss import TMITLoss
from lcls_tools.common.measurements.wire_scan_results import (
    WireBeamProfileMeasurementResult,
    ProfileMeasurement,
    DetectorMeasurement,
    MeasurementMetadata,
    FitResult,
    DetectorFit,
)
import yaml
import numpy as np
from typing_extensions import Self
import logging
from lcls_tools.common.logger.file_logger import custom_logger
from lcls_tools.common.measurements.buffer_reservation import reserve_buffer
from lcls_tools.common.measurements.utils import collect_with_size_check

from lcls_tools.common.measurements.beam_profile import BeamProfileMeasurement


class WireBeamProfileMeasurement(BeamProfileMeasurement):
    """
    Performs a wire scan measurement and fits beam profiles.

    Attributes:
        name (str): Scan object name required by Measurement class.
        my_wire (Wire): Wire device used to perform the scan.
        beampath (str): Beamline path identifier for buffer and device
                        selection.
        my_buffer (edef.BSABuffer): edef buffer object to manage data
                                    acquisition.
        devices (dict): Holds all slac-tools device objects associated
                        with this measurement (wires, detectors, bpms, etc).
        data (dict): Raw data object for all devices defined above.
        profile_measurements (dict): Collected data organized by profile.
        logger (logging.Logger): Object for log file management.
    """

    name: str = "Wire Beam Profile Measurement"
    beam_profile_device: Wire
    beampath: str

    # Extra fields to be set after validation
    # Must be optional to start
    my_buffer: Optional[edef.BSABuffer] = None
    devices: Optional[dict] = None
    detectors: Optional[list] = None
    data: Optional[dict] = None
    profiles: Optional[dict] = None
    logger: Optional[logging.Logger] = None

    # alias so beam_profile_device can also be accessed with name my_wire
    @property
    def my_wire(self) -> Wire:
        return self.beam_profile_device

    @my_wire.setter
    def my_wire(self, value):
        self.beam_profile_device = value

    @model_validator(mode="after")
    def run_setup(self) -> Self:
        # Configure custom logger
        date_str = datetime.now().strftime("%Y%m%d")
        log_filename = f"ws_log_{date_str}.txt"
        self.logger = custom_logger(
            log_file=log_filename,
            name="wire_scan_logger",
        )
        self.logger.propagate = False

        # Reserve BSA buffer
        if self.my_buffer is None:
            self.my_buffer = reserve_buffer(
                beampath=self.beampath,
                name="LCLS Tools Wire Scan",
                n_measurements=self._calc_buffer_points(),
                destination_mode="Inclusion",
                logger=self.logger,
            )
        self.detectors = [d.split(":")[0] for d in self.my_wire.metadata.detectors]

        # Generate dictionary of all requried lcls-tools device objects
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
        # Create measurement metadata object
        metadata = self.create_metadata()

        # Send command to start wire motion sequence and wait for initialization
        self.scan_with_wire()

        # Start BSA buffer and wait for acquisition to complete
        self.start_timing_buffer()

        # Get position and detector data from the buffer
        self.data = self.get_data_from_buffer()

        # Determine the profile range indices
        # e.g., u range = (13000, 18000) -> position_data[100:450]
        profile_idxs = self.get_profile_range_indices()

        # Separate detector data by profile
        self.profiles = self.organize_data_by_profile(profile_idxs)

        # Fit detector data by profile
        fit_result = self.fit_data_by_profile()

        # Get RMS beam sizes if both x and y profiles are present
        rms_sizes = self.get_rms_sizes(fit_result, metadata.default_detector)

        # Release EDEF/BSA
        self.logger.info("Releasing BSA buffer.")
        self.my_buffer.release()
        self.my_buffer = None

        return WireBeamProfileMeasurementResult(
            profiles=self.profiles,
            raw_data=self.data,
            fit_result=fit_result,
            rms_sizes=rms_sizes,
            metadata=metadata,
        )

    def create_device_dictionary(self):
        """
        Creates a device dictionary for a wire scan setup.

        Includes the wire device and any associated detectors
        from metadata.

        Parameters:
            my_wire (Wire): An lcls-tools Wire object.
        Returns:
            dict: A mapping of device names to device objects.
        """

        self.logger.info("Creating device dictionary...")

        # Instantiate device dictionary with wire device
        devices = {self.my_wire.name: self.my_wire}

        create_by_prefix = {
            "LBLM": create_lblm,
            "PMT": create_pmt,
        }

        for ds in self.my_wire.metadata.detectors:
            name, area = ds.split(":")
            if name != "TMITLOSS":
                c = next(
                    (
                        f
                        for prefix, f in create_by_prefix.items()
                        if name.startswith(prefix)
                    ),
                    None,
                )
                if c is None:
                    self.logger.warning("Unknown detector type '%s'. Skipping.", name)
                else:
                    device = c(area=area, name=name)
                    if device is not None:
                        devices[name] = device
                    else:
                        self.logger.warning(
                            "%s device creation returned None. Skipping.", name
                        )
            else:
                devices["TMITLOSS"] = TMITLoss(
                    my_buffer=self.my_buffer,
                    my_wire=self.my_wire,
                    beampath=self.beampath,
                    region=self.my_wire.area,
                )

        self.logger.info("Device dictionary built.")
        return devices

    def scan_with_wire(self):
        """
        Starts the buffer and wire scan with brief delays.

        Delays ensure the buffer is active before the scan begins
        and allows time for the buffer to update its state.
        """
        # Reserve a new buffer if necessary
        if self.my_buffer is None:
            self.my_buffer = reserve_buffer(
                beampath=self.beampath,
                name="LCLS Tools Wire Scan",
                n_measurements=self._calc_buffer_points(),
                destination_mode="Inclusion",
                logger=self.logger,
            )

        # Start wire scan
        self.logger.info("Starting wire motion sequence...")
        self.my_wire.start_scan()

        # Give wire time to initialize
        self.logger.info("Waiting for wire initialization...")

        start_time = time.monotonic()
        last_print_time = start_time
        last_trigger_time = start_time
        attempt_count = 0
        elapsed_time = 0

        while not self.my_wire.enabled:
            current_time = time.monotonic()
            elapsed_time = current_time - start_time

            # Fail after 30 seconds
            if elapsed_time >= 30:
                msg = (
                    f"{self.my_wire.name} failed to initialize"
                    "after {int(elapsed_time)} seconds"
                )

                self.logger.error(msg)
                raise TimeoutError(msg)

            # Print every 5 seconds
            if current_time - last_print_time >= 5:
                self.logger.info("Waited %0.f seconds", elapsed_time)
                last_print_time = current_time

            # Retrigger every 10 seconds
            if current_time - last_trigger_time >= 10:
                attempt_count += 1
                self.logger.info("Scan sequence attempt #%s", attempt_count)
                self.my_wire.start_scan()
                last_trigger_time = current_time

            # Check enabled state every 0.1 seconds
            time.sleep(0.1)

        self.logger.info(
            "%s initialized after %s seconds", self.my_wire.name, elapsed_time
        )

    def start_timing_buffer(self):
        """
        Start a BSA buffer and wait for it to complete.  Post wire position to
        the log every second.
        """
        # Start buffer
        self.logger.info("Starting BSA buffer...")
        self.my_buffer.start()

        # Wait briefly before checking buffer 'ready'
        # Wire is already moving, data is already collecting...
        time.sleep(0.5)

        # Wait for buffer 'ready'
        i = 0
        while not self.my_buffer.is_acquisition_complete():
            # Check for completion every 0.1 s, post position 1s
            time.sleep(0.1)
            if i % 10 == 0:
                self.logger.info("Wire position: %s", self.my_wire.motor_rbv)
            i += 1

        self.logger.info(
            "BSA buffer %s acquisition complete after %s seconds",
            self.my_buffer.number,
            i / 10,
        )

    def get_data_from_buffer(self):
        """
        Collects wire scan and detector data after buffer completes.

        Checks data size against expected points and retries if needed.

        Returns:
            dict: Collected data keyed by device name.
        """
        data = {}

        self.logger.info("Getting data from BSA buffer...")

        for d in self.devices:
            if d == self.my_wire.name:
                wire_data = collect_with_size_check(
                    self.devices[d].position_buffer,
                    self.my_buffer.n_measurements,
                    self.logger,
                    self.my_buffer,
                )
                data[d] = wire_data
            elif d == "TMITLOSS":
                tmit_data = collect_with_size_check(
                    self.devices[d].measure,
                    self.my_buffer.n_measurements,
                    self.logger,
                )
                data["TMITLOSS"] = tmit_data
            elif d.startswith("LBLM"):
                lblm_data = collect_with_size_check(
                    self.devices[d].fast_buffer,
                    self.my_buffer.n_measurements,
                    self.logger,
                    self.my_buffer,
                )
                data[d] = lblm_data
            elif d.startswith("PMT"):
                pmt_data = collect_with_size_check(
                    self.devices[d].qdcraw_buffer,
                    self.my_buffer.n_measurements,
                    self.logger,
                    self.my_buffer,
                )
                data[d] = pmt_data

        self.logger.info("Data retrieved from BSA buffer.  Scan complete.")
        return data

    def get_profile_range_indices(self):
        """
        Finds sequential scan indices within each profile's position range.

        Filters wire position data to identify index ranges for x, y, and u
        profiles, excluding non-continuous points like wire retractions.

        Returns:
            dict: Profile keys ('x', 'y', 'u') with lists of index arrays.
        """
        self.logger.info("Getting profile range indices...")
        # Get wire data to detemine profile indices
        position_data = self.data[self.my_wire.name]

        # Hold profile ranges
        ranges = {}

        # Hold sequential indices (avoid catching return wires)
        profile_idxs = {}

        ap = self._active_profiles()

        for p in ap:
            # Get range methods e.g. x_range()
            method_name = f"{p}_range"
            ranges[p] = getattr(self.my_wire, method_name)

            # No motion in selected profile
            if position_data.min() == position_data.max():
                msg = "Data did not collect properly in timing buffer. Exiting scan."
                self.logger.error(msg)
                raise RuntimeError(msg)

            # Max position less than lower scan bound
            elif position_data.max() < ranges[p][0]:
                msg = f"Scan did not reach expected {p} profile range.  Exiting scan."
                self.logger.error(msg)
                raise RuntimeError(msg)

            # Get indices of position in a selected wire scan profile range
            idx = np.where(
                (position_data >= ranges[p][0]) & (position_data <= ranges[p][1])
            )[0]

            # Data slice representing wire positions
            pos = position_data[idx]

            # Boolean mask of indices in a given profile measurement
            mono_mask = self._mono_array(pos)
            mono_idx = np.array(idx)[mono_mask]
            profile_idxs[p] = mono_idx

        self.logger.info("Profile range information collected.")
        return profile_idxs

    def organize_data_by_profile(self, profile_idxs):
        """
        Organizes detector data by scan profile for each device.

        Uses sequential indices to separate full device data into
        x, y, and u profile datasets.

        Returns:
            dict: Nested dict with profiles as keys and device
                  data per profile.
        """
        self.logger.info("Creating profile data objects...")
        profiles = list(profile_idxs.keys())
        devices = list(self.devices.keys())

        profile_measurements = {}

        for p in profiles:
            idx = profile_idxs.get(p)
            detectors = {}

            for d in devices:
                data_slice = self.data[d][idx]
                if d == self.my_wire.name:
                    positions = data_slice
                else:
                    units = "%% beam loss" if d == "TMITLOSS" else "counts"
                    detectors[d] = DetectorMeasurement(
                        values=data_slice, units=units, label=d
                    )

            profile_measurements[p] = ProfileMeasurement(
                positions=positions, detectors=detectors, profile_idxs=idx
            )

        self.logger.info("Profile data objects created.")
        return profile_measurements

    def fit_data_by_profile(self):
        """
        Fits detector data for each profile and device.

        Applies beam fitting to x, y, and u projections
        for all devices in the detector data.

        Returns:
            dict: Fit results organized by profile and device.
        """
        self.logger.info("Fitting profile data...")

        # Get list of profiles from data set
        profiles = list(self.profiles.keys())
        fit_result = {profile: {} for profile in profiles}

        for p in profiles:
            detector_fit = {d: {} for d in self.detectors}
            for d in self.detectors:
                # Get fit parameters
                fp = gaussian.fit(
                    pos=self.profiles[p].positions,
                    data=self.profiles[p].detectors[d].values,
                )

                fit_curve = gaussian.curve(
                    x=self.profiles[p].positions,
                    mean=fp["mean"],
                    sigma=fp["sigma"],
                    amp=fp["amp"],
                    off=fp["off"],
                )
                detector_fit[d] = DetectorFit(
                    mean=fp["mean"],
                    sigma=fp["sigma"],
                    amplitude=fp["amp"],
                    offset=fp["off"],
                    curve=fit_curve,
                )
            fit_result[p] = FitResult(detectors=detector_fit)

        self.logger.info("Profile data fit.")
        return fit_result

    def get_rms_sizes(self, fit_result, default_detector):
        if "x" in fit_result and "y" in fit_result:
            x_fit = fit_result["x"].detectors[default_detector]
            y_fit = fit_result["y"].detectors[default_detector]

            self.logger.info("Getting RMS beam size...")
            rms_sizes = (x_fit.sigma, y_fit.sigma)
        else:
            self.logger.warning(
                "Both x and y profiles not found. Skipping RMS size return."
            )
            rms_sizes = None
        return rms_sizes

    def create_metadata(self):
        """
        Make additional metadata
        """
        scan_ranges = {
            "x": self.my_wire.x_range,
            "y": self.my_wire.y_range,
            "u": self.my_wire.u_range,
        }

        lblm_config = self._load_yaml_config()
        default_detector = lblm_config[self.my_wire.name]

        metadata = MeasurementMetadata(
            wire_name=self.my_wire.name,
            area=self.my_wire.area,
            beampath=self.beampath,
            detectors=self.detectors,
            default_detector=default_detector,
            scan_ranges=scan_ranges,
            timestamp=datetime.now(),
            notes=None,
        )

        return metadata

    def _active_profiles(self):
        """
        Returns a list of active scan profiles based on wire settings.
        """
        return [
            axis
            for axis, use in zip(
                "xyu",
                [
                    self.my_wire.use_x_wire,
                    self.my_wire.use_y_wire,
                    self.my_wire.use_u_wire,
                ],
            )
            if use
        ]

    def _calc_buffer_points(self):
        """
        Determine the number of buffer points for a wire scan.

        The beam rate and pulses per profile are used here to calculate the
        wire speed, which in turn defines how many BSA buffer points are needed
        to capture the full scan. The minimum safe wire speed is calculated
        separately and enforced by the motion IOC. The buffer size must be
        sufficient for data collection while staying under the 20,000-point
        operational limit.

        In the historical mode (120 Hz, 350 pulses), ~1,600 points are
        required; this function returns 1,595. In the expected high-rate mode
        (16 kHz, 5,000 pulses), the function estimates ~19,166 points, still
        within the system limit.

        Returns
        -------
        int
            Estimated number of buffer points to allocate for the scan.
        """

        rate = self.my_wire.beam_rate
        pulses = self.my_wire.scan_pulses

        # 16000 max rate, 10 min rate
        log_range = np.log10(16000) - np.log10(10)
        rate_factor = (np.log10(rate) - np.log10(10)) / log_range
        fudge = 1.5 - 0.4 * rate_factor  # Fudge the calculation by 1.1 to 1.5

        buffer_points = pulses * 3 * fudge + rate / 6
        return int(buffer_points)

    def _log_validation_error(self, logger, name: str, e: ValidationError) -> None:
        """
        Logs details of a Pydantic ValidationError during device creation.
        """
        logger.warning("Validation error creating %s. Continuing...", name)
        for err in e.errors():
            loc = " -> ".join(str(i) for i in err["loc"])
            logger.warning("%s: %s (%s)", loc, err["msg"], err["type"])

    def _mono_array(self, pos):
        """
        Boolean mask of monotonically non-decreasing data points
        Mask of values where difference between neighbors is > 0.
        """
        mono = True
        mono_mask = np.array(
            # Data point [i-1] is less than subsequent data point [i]
            # and that relationship was True for the previous pair
            # for all points
            [mono := (pos[i - 1] <= pos[i] and mono) for i in range(1, len(pos))]
        )
        mono_mask = np.concatenate(([True], mono_mask))
        return mono_mask

    def _load_yaml_config(self):
        file_to_open = (
            Path(__file__).resolve().parent.parent
            / "devices"
            / "yaml"
            / "wire_lblms.yaml"
        )

        if file_to_open.exists() is False:
            msg = f"YAML config file {file_to_open} not found."
            self.logger.error(msg)
            return None

        with open(file_to_open, "r") as f:
            wire_lblms = yaml.safe_load(f)
            return wire_lblms

    def _get_default_detector(self):
        lblm_config = self._load_yaml_config()
        if lblm_config is None:
            return self.detectors[0]
        else:
            default_detector = lblm_config[self.my_wire.name]
            return default_detector
