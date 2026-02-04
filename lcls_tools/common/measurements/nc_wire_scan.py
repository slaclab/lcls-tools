from lcls_tools.common.measurements.wire_scan import WireBeamProfileMeasurement
from lcls_tools.common.measurements.wire_scan_results import (
    WireBeamProfileMeasurementResult,
)
import time


class NCWireBeamProfileMeasurement(WireBeamProfileMeasurement):
    name: str = "NC Wire Beam Profile Measurement"

    def scan_with_wire(self):
        # Reserve buffer if needed
        self._reserve_buffer()

        # Initialize wire scan
        max_attempts = 3

        for attempt in range(1, max_attempts + 1):
            self.logger.info(
                f"Initializing {self.my_wire.name}: (Attempt {attempt}/{max_attempts})..."
            )
            self.my_wire.initialize()

            if self._wait_until(lambda: self.my_wire.enabled, timeout=10):
                break
            else:
                self.logger.warning(
                    f"{self.my_wire.name} did not enable after 10s - retrying..."
                )
        else:
            raise RuntimeError(
                f"Failed to initialize {self.my_wire.name} after {max_attempts} attempts."
            )

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
        for i in range(len(posns)):
            self.logger.info(f"Moving wire to {posns[i]}...")
            if i in [0, 2, 4]:  # If moving to profile inner position, set speed to max
                self.my_wire.speed = int(self.my_wire.speed_max)

            elif i in [
                1,
                3,
                5,
            ]:  # If moving to profile outer position, set calculated speed
                profile_range = posns[i] - posns[i - 1]
                speed = (
                    profile_range / self.my_wire.scan_pulses
                ) * self.my_wire.beam_rate
                self.my_wire.speed = int(speed)

            self.my_wire.motor = posns[i]

            # If position (within 250 um) not reached within 15s, raise error
            if not self._wait_until(
                lambda: abs(self.my_wire.motor_rbv - posns[i]) < 250, timeout=15
            ):
                raise RuntimeError(
                    f"{self.my_wire.name} did not reach position {posns[i]} after 15s."
                )

        # Retract wire at end of scan
        self.my_wire.speed = self.my_wire.speed_max
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
        # Reserve a new buffer if necessary
        self._reserve_buffer()

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
