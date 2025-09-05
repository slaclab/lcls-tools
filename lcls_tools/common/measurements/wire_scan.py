from typing import Optional
from lcls_tools.common.devices.wire import Wire
from lcls_tools.common.devices.reader import create_lblm, create_pmt
import lcls_tools.common.model.gaussian as gaussian
from lcls_tools.common.measurements.measurement import Measurement
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
)
import numpy as np
from typing_extensions import Self
import logging
from lcls_tools.common.logger.file_logger import custom_logger
from lcls_tools.common.measurements.buffer_reservation import reserve_buffer


class WireBeamProfileMeasurement(Measurement):
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
    my_wire: Wire
    beampath: str

    # Extra fields to be set after validation
    # Must be optional to start
    my_buffer: Optional[edef.BSABuffer] = None
    devices: Optional[dict] = None
    data: Optional[dict] = None
    profile_measurements: Optional[dict] = None
    logger: Optional[logging.Logger] = None

    @model_validator(mode="after")
    def run_setup(self) -> Self:
        # Configure custom logger
        date_str = datetime.now().strftime("%Y%m%d")
        log_filename = f"ws_log_{date_str}.txt"
        self.logger = custom_logger(
            log_file=log_filename,
            name="wire_scan_logger",
        )

        # Reserve BSA buffer
        if self.my_buffer is None:
            self.my_buffer = reserve_buffer(
                beampath=self.beampath,
                name="LCLS Tools Wire Scan",
                n_measurements=self.calc_buffer_points(),
                destination_mode="Inclusion",
                logger=self.logger,
            )

        # Generate dictionary of all requried devices
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
        self.profiles = self.organize_data_by_profile(profile_idxs)

        # Fit detector data by profile
        fit_result, rms_sizes = self.fit_data_by_profile()

        # Create measurement metadata object
        metadata = self.create_metadata()

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

        Includes the wire device and any associated LBLM devices
        based on metadata.

        Parameters:
            my_wire (Wire): An lcls-tools Wire object.
        Returns:
            dict: A mapping of device names to device objects.
        """
        self.logger.info("Creating device dictionary...")

        # Instantiate device dictionary with wire device
        devices = {self.my_wire.name: self.my_wire}

        def _log_validation_error(logger, name: str, e: ValidationError) -> None:
            logger.warning("Validation error creating %s. Continuing...", name)
            for err in e.errors():
                loc = " -> ".join(str(i) for i in err["loc"])
                logger.warning("%s: %s (%s)", loc, err["msg"], err["type"])

        create_by_prefix = {
            "LBLM": create_lblm,
            "PMT": create_pmt,
        }

        for d_str in self.my_wire.metadata.detectors:
            # Detectors are stored in YAML file as a string like {NAME}:{AREA}
            name, area = d_str.split(":")

            if name == "TMITLOSS":
                devices["TMITLOSS"] = TMITLoss(
                    my_buffer=self.my_buffer,
                    my_wire=self.my_wire,
                    beampath=self.beampath,
                    region=self.my_wire.area,
                )

            creator = next(
                (
                    f
                    for prefix, f in create_by_prefix.items()
                    if name.startswith(prefix)
                ),
                None,
            )
            if creator is None:
                self.logger.warning(
                    "Unknown detector type '%s'in '%s'. Skipping.", name, d_str
                )

            try:
                devices[name] = creator(area=area, name=name)
            except ValidationError as e:
                _log_validation_error(self.logger, name, e)

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
                n_measurements=self.calc_buffer_points(),
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

            if elapsed_time >= 30:
                msg = (
                    f"{self.my_wire.name} failed to initialize"
                    "after {int(elapsed_time)} seconds"
                )

                self.logger.error(msg)
                raise TimeoutError(msg)

            if current_time - last_print_time >= 5:
                self.logger.info("Waited %0.f seconds", elapsed_time)
                last_print_time = current_time

            if current_time - last_trigger_time >= 10:
                attempt_count += 1
                self.logger.info("Scan sequence attempt #%s", attempt_count)
                self.my_wire.start_scan()
                last_trigger_time = current_time

            time.sleep(0.1)

        self.logger.info(
            "%s initialized after %s seconds", self.my_wire.name, elapsed_time
        )

        # Start buffer
        self.logger.info("Starting BSA buffer...")
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

        self.logger.info("Getting data from BSA buffer...")

        # Get device data from buffer
        for d in self.devices:
            # Get position data if wire device
            if d == self.my_wire.name:
                data[d] = self.my_wire.position_buffer(self.my_buffer)

            # Get TMITLoss data
            elif d == "TMITLOSS":
                data[d] = self.devices[d].measure()

            elif d.starswith("LBLM"):
                data[d] = self.devices[d].fast_buffer(self.my_buffer)

            elif d.startswith("PMT"):
                data[d] = self.devices[d].qdcraw_buffer(self.my_buffer)

        self.logger.info("Data retrieved from BSA buffer.  Scan complete.")

        # Release EDEF/BSA
        self.logger.info("Releasing BSA buffer.")
        self.my_buffer.release()
        self.my_buffer = None

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

        ap = self.active_profiles()

        for p in ap:
            # Get range methods e.g. x_range()
            method_name = f"{p}_range"
            ranges[p] = getattr(self.my_wire, method_name)

            if position_data.min() == position_data.max():  # No change in data
                msg = "Data did not collect properly in BSA buffer. Exiting scan."
                self.logger.error(msg)
                raise RuntimeError(msg)
            elif (
                position_data.max() < ranges[p][0]
            ):  # Max position less than lower scan bound
                msg = f"Scan did not reach expected {p} profile range.  Exiting scan."
                self.logger.error(msg)
                raise RuntimeError(msg)

            # Get indices of  position when within a
            # selected wire scan profile range
            idx = np.where(
                (position_data >= ranges[p][0]) & (position_data <= ranges[p][1])
            )[0]

            # Data slice representing wire positions
            # for a given profile measurement
            pos = position_data[idx]

            # Boolean mask of monotonically non-decreasing data points
            # Mask of values where difference between neighbors is > 0
            def mono_array(pos):
                mono = True
                mono_mask = np.array(
                    # Data point [i-1] is less than subsequent data point [i]
                    # and that relationship was True for the previous pair
                    # for all points
                    [
                        mono := (pos[i - 1] <= pos[i] and mono)
                        for i in range(1, len(pos))
                    ]
                )
                mono_mask = np.concatenate(([True], mono_mask))
                return mono_mask

            # Boolean mask of indices in a given profile measurement
            mono_mask = mono_array(pos)
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
        devices = list(self.data.keys())

        for p in profiles:
            for d in devices:
                if d == self.my_wire.name:
                    continue

                fit_params = gaussian.fit(
                    pos=self.profiles[p].positions,
                    data=self.profiles[p].detectors[d].values,
                )

                fit_curve = gaussian.curve(
                    x=self.profiles[p].positions,
                    mean=fit_params["mean"],
                    sigma=fit_params["sigma"],
                    amp=fit_params["amp"],
                    off=fit_params["off"],
                )
                fit_result[p][d] = FitResult(
                    mean=fit_params["mean"],
                    sigma=fit_params["sigma"],
                    amplitude=fit_params["amp"],
                    offset=fit_params["off"],
                    curve=fit_curve,
                )

                x_fits = fit_result["x"]
                y_fits = fit_result["y"]

        rms_sizes = {
            d: (x_fits[d]["sigma"], y_fits[d]["sigma"])
            for d in devices
            if d != self.my_wire.name
        }

        self.logger.info("Profile data fit.")
        return fit_result, rms_sizes

    def create_metadata(self):
        """
        Make additional metadata
        """
        sample_profile = next(iter(self.profiles.values()))
        detectors = list(sample_profile.detectors.keys())

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

    def active_profiles(self):
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

    def calc_buffer_points(self):
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

        # 16000 max rate, 120 min rate
        log_range = np.log10(16000) - np.log10(120)
        rate_factor = (np.log10(rate) - np.log10(120)) / log_range
        fudge = 1.5 - 0.4 * rate_factor  # Fudge the calculation by 1.1 to 1.5

        buffer_points = pulses * 3 * fudge + rate / 6
        return int(buffer_points)
