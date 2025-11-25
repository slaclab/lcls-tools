from lcls_tools.common.measurements.wire_scan import WireBeamProfileMeasurement
from lcls_tools.common.measurements.wire_scan_results import (
    WireBeamProfileMeasurementResult,
)
import time
from lcls_tools.common.measurements.buffer_reservation import reserve_buffer


class NCWireBeamProfileMeasurement(WireBeamProfileMeasurement):
    name: str = "NC Wire Beam Profile Measurement"

    def scan_with_wire(self):
        # Reserve buffer if needed
        if self.my_buffer is None:
            self.my_buffer = reserve_buffer(
                beampath=self.beampath,
                name="LCLS Tools NC Wire Scan",
                n_measurements=self._calc_buffer_points(),
                destination_mode="Inclusion",
                logger=self.logger,
            )

        # Initialize wire scan
        self.logger.info("Starting wire motion sequence...")
        self.my_wire.initialize()

        # Wait for hardware to be ready
        if not self._wait_until(lambda: self.my_wire.enabled, timeout=10):
            raise RuntimeError(f"{self.my_wire.name} did not initialize after 10s.")

        # Build ordered profile positions
        posns = []
        for p in self._active_profiles():
            for m in ["inner", "outer"]:
                method_name = f"{p}_wire_{m}"
                posns.append(getattr(self.my_wire, method_name))
        posns = sorted(posns)

        # Start buffer acquisition
        self.logger.info("Starting buffer acquisition...")
        self.my_buffer.start()

        # Move to each position
        for target in posns:
            self.logger.info(f"Moving wire to {target}...")
            self.my_wire.motor = target

            if not self._wait_until(
                lambda: abs(self.my_wire.motor_rbv - target) < 25, timeout=5
            ):
                raise RuntimeError(
                    f"{self.my_wire.name} did not reach position {target} after 5s."
                )

        # Retract wire at end of scan
        self.my_wire.motor = 100

        # Wait for buffer acquisition to complete
        while not self.my_buffer.is_acquisition_complete():
            # Check for completion every 0.1 s
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

    def _wait_until(self, condition, timeout=5, period=0.1):
        start = time.time()
        while time.time() - start < timeout:
            if condition():
                return True
            time.sleep(period)
        return False
