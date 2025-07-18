from pathlib import Path
from typing import Optional
from lcls_tools.common.devices.wire import Wire
from lcls_tools.common.devices.reader import create_lblm
from lcls_tools.common.data.fit.projection import ProjectionFit
from lcls_tools.common.measurements.tmit_loss import TMITLoss
from lcls_tools.common.measurements.buffer_reservation import reserve_buffer
from lcls_tools.common.measurements.wire_scan_results import (
    WireBeamProfileMeasurementResult,
    ProfileMeasurement,
    DetectorMeasurement,
    MeasurementMetadata,
)
import time
from datetime import datetime

import yaml
import edef
from pydantic import BaseModel, model_validator
import numpy as np
from typing_extensions import Self

from lcls_tools.common.measurements.beam_profile import BeamProfileMeasurement


class WireBeamProfileMeasurement(BeamProfileMeasurement):
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
    beam_profile_device: Wire
    beampath: str
    beam_fit: BaseModel = ProjectionFit
    fit_profile: bool = True

    # Extra fields to be set after validation
    my_buffer: Optional[edef.BSABuffer] = None
    devices: Optional[dict] = None
    data: Optional[dict] = None
    profile_measurements: Optional[dict] = None

    # alias so beam_profile_device can also be accessed with name my_wire
    @property
    def my_wire(self) -> Wire:
        return self.beam_profile_device

    @my_wire.setter
    def my_wire(self, value):
        self.beam_profile_device = value

    @model_validator(mode="after")
    def run_setup(self) -> Self:
        self.buffer_setup()
        print("Creating device dictionary...")
        self.devices = self.create_device_dictionary()
        return self

    def buffer_setup(self):
        if self.my_buffer is None:
            self.my_buffer = reserve_buffer(
                beampath=self.beampath,
                name="LCLS Tools Wire Scan",
                n_measurements=1600,  # Determined via empirical testing at 120 Hz
                destination_mode="Inclusion",
                logger=None,
            )

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
        self.profile = self.organize_data_by_profile(profile_idxs)

        # Fit detector data by profile
        fit_result, rms_sizes, centroids, total_intensities = self.fit_data_by_profile()

        # Create measurement metadata object
        metadata = self.create_metadata()

        return WireBeamProfileMeasurementResult(
            profiles=self.profile_measurements,
            raw_data=self.data,
            fit_result=fit_result,
            rms_sizes=rms_sizes,
            centroids=centroids,
            total_intensities=total_intensities,
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
        # Check for reserved buffer
        self.buffer_setup()

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
        # Get wire data to detemine profile indices
        position_data = self.data[self.my_wire.name]

        # Hold profile ranges
        ranges = {}

        # Hold sequential indices (avoid catching return wires)
        profile_idxs = {}

        active_profiles = []
        if self.my_wire.use_x_wire:
            active_profiles.append("x")
        if self.my_wire.use_y_wire:
            active_profiles.append("y")
        if self.my_wire.use_u_wire:
            active_profiles.append("u")

        for profile in active_profiles:
            # Get range methods e.g. x_range()
            method_name = f"{profile}_range"
            ranges[profile] = getattr(self.my_wire, method_name)

            # Get indices of when position is within a range
            idx = np.where(
                (position_data >= ranges[profile][0])
                & (position_data <= ranges[profile][1])
            )[0]

            pos = position_data[idx]
            mono_mask = np.diff(pos) >= 0
            mono_mask = np.concatenate(([True], mono_mask))

            mono_idx = idx[mono_mask]

            profile_idxs[profile] = mono_idx

        return profile_idxs

    def organize_data_by_profile(self, profile_idxs):
        """
        Organizes detector data by scan profile for each device.

        Uses sequential indices to separate full device data into
        x, y, and u profile datasets.

        Returns:
            dict: Nested dict with profiles as keys and device data per profile.
        """

        profiles = list(profile_idxs.keys())
        devices = list(self.devices.keys())

        profile_measurements = {}

        for profile in profiles:
            idx = profile_idxs.get(profile)
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

            profile_measurements[profile] = ProfileMeasurement(
                positions=positions, detectors=detectors, profile_idxs=idx
            )

        return profile_measurements

    def fit_data_by_profile(self):
        """
        Fits detector data for each profile and device.

        Applies beam fitting to x, y, and u projections
        for all devices in the detector data.

        Returns:
            dict: Fit results organized by profile and device.
        """
        # Get list of profiles from data set
        profiles = list(self.profile_measurements.keys())
        fit_result = {profile: {} for profile in profiles}
        devices = list(self.data.keys())

        for profile in profiles:
            wire_posn = self.profile_measurements[profile].positions
            posn_start = wire_posn[0]
            posn_diff = np.mean(np.diff(wire_posn))

            for device in devices:
                if device == self.my_wire.name:
                    continue
                proj_fit = self.beam_fit()
                proj_data = self.profile_measurements[profile].detectors[device].values
                fit_result[profile][device] = proj_fit.fit_projection(proj_data)

                mean_idx = fit_result[profile][device]["mean"]
                fit_result[profile][device]["mean"] = mean_idx * posn_diff + posn_start

                sigma_idx = fit_result[profile][device]["sigma"]
                fit_result[profile][device]["sigma"] = sigma_idx * posn_diff

                fit_result[profile][device]["total_intensity"] = np.sum(proj_data)

                x_fits = fit_result["x"]
                y_fits = fit_result["y"]

        rms_sizes_all = {}
        centroids_all = {}
        total_intensities_all = {}
        for device in devices:
            if device != self.my_wire.name:
                rms_sizes_all[device] = (
                    x_fits[device]["sigma"],
                    y_fits[device]["sigma"],
                )
                centroids_all[device] = (x_fits[device]["mean"], y_fits[device]["mean"])
                total_intensities_all[device] = (
                    x_fits[device]["total_intensity"],
                    y_fits[device]["total_intensity"],
                )

        current_file = Path(__file__).resolve()
        devices_root = current_file.parent.parent
        file_to_open = devices_root / "devices" / "yaml" / "wire_lblms.yaml"
        with open(file_to_open, "r") as wire_lblms_yaml:
            wire_lblms = yaml.safe_load(wire_lblms_yaml)
        lblm = wire_lblms[self.my_wire.name]
        rms_sizes = rms_sizes_all[lblm]
        centroids = centroids_all[lblm]
        total_intensities = total_intensities_all[lblm]

        return fit_result, rms_sizes, centroids, total_intensities

    def create_metadata(self):
        # Make additional metadata
        sample_profile = next(iter(self.profile_measurements.values()))
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
