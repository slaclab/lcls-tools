from typing import Optional
from lcls_tools.common.devices.wire import Wire
from lcls_tools.common.measurements.wire_scan import WireBeamProfileMeasurement
import time
from datetime import datetime
import edef
from pydantic import model_validator
from typing_extensions import Self
import logging
from lcls_tools.common.logger.file_logger import custom_logger
from lcls_tools.common.measurements.buffer_reservation import reserve_buffer


class SlowWireBeamProfileMeasurement(WireBeamProfileMeasurement):
    name: str = "Slow Wire Beam Profile Measurement"
    beam_profile_device: Wire
    beampath: str
    my_buffer: Optional[edef.BSABuffer] = None
    devices: Optional[dict] = None
    detectors: Optional[list] = None
    data: Optional[dict] = None
    profiles: Optional[dict] = None
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
        self.logger.propagate = False

        # Reserve BSA buffer
        if self.my_buffer is None:
            self.my_buffer = reserve_buffer(
                beampath=self.beampath,
                name="LCLS Tools Slow Wire Scan",
                n_measurements=self._calc_buffer_points(),
                destination_mode="Inclusion",
                logger=self.logger,
            )
        self.detectors = [d.split(":")[0] for d in self.my_wire.metadata.detectors]

        # Generate dictionary of all requried lcls-tools device objects
        self.devices = self.create_device_dictionary()
        return self

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

        while self.my_wire.motor < min(inners.values()):
            time.sleep(0.1)
