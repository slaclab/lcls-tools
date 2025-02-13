import time
from typing import Any, Optional

import numpy as np
from numpy import ndarray
from pydantic import BaseModel, ConfigDict, PositiveInt, field_validator, PositiveFloat

from lcls_tools.common.data.emittance import compute_emit_bmag
from lcls_tools.common.data.model_general_calcs import bdes_to_kmod, get_optics
from lcls_tools.common.devices.magnet import Magnet
from lcls_tools.common.measurements.measurement import Measurement


class EmittanceMeasurementResult(BaseModel):
    """
    EmittanceMeasurementResult stores the results of an emittance measurement.

    Attributes
    ----------
    quadrupole_strengths : np.ndarray, shape (n,)
        Geometric focusing strength (k1) settings of the quadrupole used in the scan in m^{-2}.
    emittance : np.ndarray, shape (2,)
        The geometric emittance values for x/y in mm-mrad.
    BMAG : np.ndarray, shape (2,n)
        The BMAG values for x/y for each quadrupole strength.
    twiss_at_screen : np.ndarray, shape (n,2,3)
        Twiss parameters (beta, alpha, gamma) calculated at the screen for each quadrupole strength in each plane.
    x_rms : np.ndarray, shape (n,)
        The RMS values in the x direction for each quadrupole strength.
    y_rms : np.ndarray, shape (n,)
        The RMS values in the y direction for each quadrupole strength.
    beam_matrix : np.ndarray, shape (2,3)
        Reconstructed beam matrix at the entrance of the quadrupole for
        both x/y directions. Elements correspond to (s11,s12,s22) of the beam matrix.
    info : Any
        Metadata information related to the measurement.

    """

    quadrupole_strengths: np.ndarray
    emittance: np.ndarray
    BMAG: Optional[np.ndarray] = None
    twiss_at_screen: np.ndarray
    x_rms: np.ndarray
    y_rms: np.ndarray
    beam_matrix: np.ndarray
    info: Any

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def get_best_bmag(self, mode="geometric_mean") -> float:
        """
        Get the best BMAG value for a given mode (x, y, geometric mean).

        Parameters
        ----------
        mode : str, optional
            The mode to get the best BMAG value for, default is "geometric_mean".
            Mode can be one of the following: "x", "y", "geometric_mean".
            - "x": get the best BMAG value for the x plane.
            - "y": get the best BMAG value for the y plane.
            - "geometric_mean": get the best BMAG value for the geometric mean of the x and y planes.

        Returns
        -------
        tuple
            The best quadrupole strength and BMAG value.

        """
        if self.BMAG is None:
            raise ValueError("BMAG values are not available for this measurement")

        if mode == "x":
            best_index = np.argmin(self.BMAG[0])
            bmag_value = self.BMAG[0][best_index]
        elif mode == "y":
            best_index = np.argmin(self.BMAG[1])
            bmag_value = self.BMAG[1][best_index]
        elif mode == "geometric_mean":
            best_index = np.argmin(np.sqrt(self.BMAG[0] * self.BMAG[1]))
            bmag_value = np.sqrt(self.BMAG[0][best_index] * self.BMAG[1][best_index])
        else:
            raise ValueError("mode must be either 'x', 'y', or 'geometric_mean'")

        return self.quadrupole_strengths[best_index], bmag_value


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

    def measure(self) -> EmittanceMeasurementResult:
        """
        Conduct quadrupole scan to measure the beam phase space.

        Returns:
        -------
        result : EmittanceMeasurementResult
            Object containing the results of the emittance measurement
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
        beamsize_squared = (
            np.vstack(
                (
                    np.array(self.beam_sizes["x_rms"]) * 1e3,
                    np.array(self.beam_sizes["y_rms"]) * 1e3,
                )
            )
            ** 2
        )

        magnet_length = self.magnet.metadata.l_eff
        if magnet_length is None:
            raise ValueError(
                "magnet length needs to be specified for magnet "
                f"{self.magnet.name} to be used in emittance measurement"
            )

        # organize data into arrays for use in `compute_emit_bmag`
        # rmat = np.stack([self.rmat[0:2, 0:2], self.rmat[2:4, 2:4]])
        if self.design_twiss:
            twiss_betas_alphas = np.array(
                [
                    [self.design_twiss["beta_x"], self.design_twiss["alpha_x"]],
                    [self.design_twiss["beta_y"], self.design_twiss["alpha_y"]],
                ]
            )
        else:
            twiss_betas_alphas = None

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

        results.update(
            {
                "x_rms": np.array(self.beam_sizes["x_rms"]),
                "y_rms": np.array(self.beam_sizes["y_rms"]),
            }
        )
        results.update({"info": self._info})
        results.update({"quadrupole_strengths": np.array(self.scan_values)})

        # collect information into EmittanceMeasurementResult object
        return EmittanceMeasurementResult(**results)

    def perform_beamsize_measurements(self):
        self.magnet.scan(scan_settings=self.scan_values, function=self.measure_beamsize)

    def measure_beamsize(self):
        """Take measurement from measurement device,
        store beam sizes in self.beam_sizes"""
        time.sleep(self.wait_time)

        result = self.beamsize_measurement.measure(self.n_measurement_shots)
        if "x_rms" not in self.beam_sizes:
            self.beam_sizes["x_rms"] = []
        if "y_rms" not in self.beam_sizes:
            self.beam_sizes["y_rms"] = []

        # note beamsizes here are in m
        self.beam_sizes["x_rms"].append(
            np.mean(result.rms_sizes[:, 0])
            * self.beamsize_measurement.device.resolution
            * 1e-6
        )
        self.beam_sizes["y_rms"].append(
            np.mean(result.rms_sizes[:, 1])
            * self.beamsize_measurement.device.resolution
            * 1e-6
        )

        self._info += [result]


class MultiDeviceEmittance(Measurement):
    name: str = "multi_device_emittance"

    def measure(self):
        raise NotImplementedError("Multi-device emittance not yet implemented")
