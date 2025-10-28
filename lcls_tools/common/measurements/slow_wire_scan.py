from lcls_tools.common.measurements.wire_scan import WireBeamProfileMeasurement
from lcls_tools.common.measurements.wire_scan_results import (
    WireBeamProfileMeasurementResult,
)
import time
from lcls_tools.common.measurements.buffer_reservation import reserve_buffer


class SlowWireBeamProfileMeasurement(WireBeamProfileMeasurement):
    name: str = "Slow Wire Beam Profile Measurement"

    def scan_with_wire(self):
        if self.my_buffer is None:
            self.my_buffer = reserve_buffer(
                beampath=self.beampath,
                name="LCLS Tools Slow Wire Scan",
                n_measurements=self._calc_buffer_points(),
                destination_mode="Inclusion",
                logger=self.logger,
            )

        # Start wire scan
        self.logger.info("Starting wire motion sequence...")
        self.my_wire.start_scan()

        # Give wire time to initialize
        self.logger.info("Waiting for wire to reach inner position...")

        ap = self._active_profiles()
        inners = {}
        for p in ap:
            method_name = f"{p}_wire_inner"
            inners[p] = getattr(self.my_wire, method_name)

        while self.my_wire.motor_rbv < min(inners.values()):
            time.sleep(0.1)

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

        # Retract wire after scan completion
        self.logger.info("Retracting wire...")
        self.beam_profile_device.motor = 100

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
