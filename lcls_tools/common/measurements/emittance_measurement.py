import time
from typing import Optional

import numpy as np
from numpy import ndarray
from pydantic import ConfigDict, PositiveInt, field_validator, PositiveFloat

from lcls_tools.common.data.emittance import compute_emit_bmag
from lcls_tools.common.data.model_general_calcs import bdes_to_kmod, get_optics
from lcls_tools.common.devices.magnet import Magnet
from lcls_tools.common.measurements.measurement import Measurement


class QuadScanEmittance(Measurement):
    """Use a quad and profile monitor/wire scanner to perform an emittance measurement

    Arguments:
    ------------------------
    energy: float
        Beam energy in GeV

    scan_values: List[float]
        BDES values of magnet to scan over

    magnet: Magnet
        Magnet object used to conduct scan

    beamsize_measurement: BeamsizeMeasurement
        Beamsize measurement object from profile monitor/wire scanner

    n_measurement_shots: int
        number of beamsize measurements to make per individual quad strength

    rmat: ndarray, optional
        Transport matricies for the horizontal and vertical phase space from
        the end of the scanning magnet to the screen, array shape should be 2 x 2 x 2 (
        first element is the horizontal transport matrix, second is the vertical),
        if not provided meme is used to calculate the transport matricies

    design_twiss: dict[str, float], optional
        Dictionary containing design twiss values with the following keys (`beta_x`,
        `beta_y`, `alpha_x`, `alpha_y`) where the beta/alpha values are in units of [m]/[]
        respectively

    beam_sizes, dict[str, list[float]], optional
        Dictionary contraining X-rms and Y-rms beam sizes (keys:`x_rms`,`y_rms`)
        measured during the quadrupole scan in units of [m].

    wait_time, float, optional
        Wait time in seconds between changing quadrupole settings and making beamsize
        measurements.

    Methods:
    ------------------------
    measure: does the quad scan, getting the beam sizes at each scan value,
    gets the rmat and twiss parameters, then computes and returns the emittance and BMAG

    measure_beamsize: take measurement from measurement device, store beam sizes
    """
    energy: float
    scan_values: list[float]
    magnet: Magnet
    beamsize_measurement: Measurement
    n_measurement_shots: PositiveInt = 1

    rmat: Optional[ndarray] = None
    design_twiss: Optional[dict] = None  # design twiss values
    beam_sizes: Optional[dict] = {}

    wait_time: PositiveFloat = 5.0

    name: str = "quad_scan_emittance"
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("rmat")
    def validate_rmat(cls, v, info):
        assert v.shape == (2, 2, 2)
        return v

    def measure(self):
        """
        Conduct quadrupole scan to measure the beam phase space.

        Returns:
        -------
        result : dict
            Dictonary containing the following keys
            - `emittance`: geometric emittance in x/y in units of [mm.mrad]
            - `BMAG`: Twiss mismatch parameter for each quadrupole strength (unitless)
            - `twiss_parameters`: Twiss parameters (beta, alpha, gamma) calculated at
                the screen for each quadrupole strength in each plane
            - `x_rms`: Measured beam sizes in horizontal direction in [m]
            - `y_rms`: Measured beam sizes in vertical direction in [m]
            - `info`: Measurement information for each beamsize measurement
            """

        self._info = []
        # scan magnet strength and measure beamsize
        self.perform_beamsize_measurements()

        # get transport matrix and design twiss values from meme
        # TODO: get settings from arbitrary methods (ie. not meme)
        if self.rmat is None and self.design_twiss is None:
            optics = get_optics(
                self.magnet_name,
                self.device_measurement.device.name,
            )

            self.rmat = optics["rmat"]
            self.design_twiss = optics["design_twiss"]

        # calculate beam size squared in units of mm
        beamsize_squared = np.vstack((
            np.array(self.beam_sizes["x_rms"]) * 1e3,
            np.array(self.beam_sizes["y_rms"]) * 1e3
        )) ** 2

        magnet_length = self.magnet.metadata.l_eff
        if magnet_length is None:
            raise ValueError("magnet length needs to be specified for magnet "
                             f"{self.magnet.name} to be used in emittance measurement")

        # organize data into arrays for use in `compute_emit_bmag`
        # rmat = np.stack([self.rmat[0:2, 0:2], self.rmat[2:4, 2:4]])
        twiss_betas_alphas = np.array(
            [[self.design_twiss["beta_x"], self.design_twiss["alpha_x"]],
             [self.design_twiss["beta_y"], self.design_twiss["alpha_y"]]]
        )

        # compute quadrupole focusing strengths
        # note: need to create negative k values for vertical dimension
        kmod = bdes_to_kmod(self.energy, magnet_length, np.array(self.scan_values))
        kmod = np.stack((kmod, -kmod))

        # compute emittance and bmag
        results = compute_emit_bmag(
            k=kmod,
            beamsize_squared=beamsize_squared,
            q_len=magnet_length,
            rmat=self.rmat,
            twiss_design=twiss_betas_alphas,
        )

        results.update({
            "x_rms": self.beam_sizes["x_rms"],
            "y_rms": self.beam_sizes["y_rms"]
        })
        results.update({"info": self._info})

        return results

    def perform_beamsize_measurements(self):
        self.magnet.scan(
            scan_settings=self.scan_values,
            function=self.measure_beamsize
        )

    def measure_beamsize(self):
        """Take measurement from measurement device,
        store beam sizes in self.beam_sizes"""
        time.sleep(self.wait_time)

        results = self.beamsize_measurement.measure(self.n_measurement_shots)
        if "x_rms" not in self.beam_sizes:
            self.beam_sizes["x_rms"] = []
        if "y_rms" not in self.beam_sizes:
            self.beam_sizes["y_rms"] = []

        sigmas = []
        for ele in results["fit_results"]:
            sigmas += [ele.rms_size]
        sigmas = np.array(sigmas)

        # note beamsizes here are in m
        self.beam_sizes["x_rms"].append(
            np.mean(sigmas[:, 0]) * self.beamsize_measurement.device.resolution * 1e-6)
        self.beam_sizes["y_rms"].append(
            np.mean(sigmas[:, 1]) * self.beamsize_measurement.device.resolution * 1e-6)

        self._info += [results]


class MultiDeviceEmittance(Measurement):
    name: str = "multi_device_emittance"

    def measure(self):
        raise NotImplementedError("Multi-device emittance not yet implemented")
