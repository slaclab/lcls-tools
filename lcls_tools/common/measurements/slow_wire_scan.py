from lcls_tools.common.measurements.wire_scan import WireBeamProfileMeasurement
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
