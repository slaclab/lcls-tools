from typing import Optional

import numpy as np
from numpy import ndarray
from pydantic import ConfigDict, PositiveInt, field_validator

from lcls_tools.common.data.emittance import compute_emit_bmag
from lcls_tools.common.data.model_general_calcs import bdes_to_kmod, get_optics
from lcls_tools.common.devices.magnet import Magnet
from lcls_tools.common.measurements.measurement import Measurement


class QuadScanEmittance(Measurement):
    """Use a quad and profile monitor/wire scanner to perform an emittance measurement
    ------------------------
    Arguments:
    energy: beam energy
    magnet_collection: MagnetCollection object of magnets for an area of the beamline (use create_magnet())
    magnet_name: name of magnet
    magnet_length: length of magnet
    scan_values: BDES values of magnet to scan over
    device_measurement: Measurement object of profile monitor/wire scanner
    ------------------------
    Methods:
    measure: does the quad scan, getting the beam sizes at each scan value,
    gets the rmat and twiss parameters, then computes and returns the emittance and BMAG
    measure_beamsize: take measurement from measurement device, store beam sizes
    """
    energy: float
    scan_values: list[float]
    magnet: Magnet
    beamsize_measurement: Measurement
    n_measurement_shots: PositiveInt = 1

    rmat: Optional[ndarray] = None  # 4 x 4 beam transport matrix
    design_twiss: Optional[dict] = None  # design twiss values
    beam_sizes: Optional[dict] = {}

    name: str = "quad_scan_emittance"
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("rmat")
    def validate_rmat(cls, v, info):
        assert v.shape == (4, 4)

    def measure(self):
        """Returns the emittance, BMAG, x_rms and y_rms
        Get the rmat, twiss parameters, and measured beam sizes
        Perform the scan, measuring beam sizes at each scan value
        Compute the emittance and BMAG using the geometric focusing strengths,
        beam sizes squared, magnet length, rmat, and twiss betas and alphas"""

        # scan magnet strength and measure beamsize
        self.magnet.scan(
            scan_settings=self.scan_values,
            function=self.measure_beamsize
        )

        # get transport matrix and design twiss values from meme
        # TODO: get settings from arbitrary methods (ie. not meme)
        if self.rmat is None and self.twiss is None:
            optics = get_optics(
                self.magnet_name,
                self.device_measurement.device.name,
            )

            self.rmat = optics["rmat"]
            self.design_twiss = optics["design_twiss"]

        beamsize_squared = np.vstack((
            self.beam_sizes["x_rms"], self.beam_sizes["y_rms"]
        )) ** 2

        magnet_length = self.magnet.metadata.length
        if magnet_length is None:
            raise ValueError("magnet length needs to be specified for magnet "
                             f"{self.magnet.name} to be used in emittance measurement")

        # organize data into arrays for use in `compute_emit_bmag`
        rmat = np.stack([self.rmat[0:2, 0:2], self.rmat[2:4, 2:4]])
        twiss_betas_alphas = np.array(
            [[self.design_twiss["beta_x"], self.design_twiss["alpha_x"]],
             [self.design_twiss["beta_y"], self.design_twiss["alpha_y"]]]
        )
        kmod = bdes_to_kmod(self.energy, magnet_length, np.array(self.scan_values))

        # compute emittance and bmag
        emittance, bmag, _, _ = compute_emit_bmag(
            k=kmod,
            beamsize_squared=beamsize_squared,
            q_len=magnet_length,
            rmat=rmat,
            twiss_design=twiss_betas_alphas,
        )

        results = {
            "emittance": emittance,
            "BMAG": bmag,
            "x_rms": self.beam_sizes["x_rms"],
            "y_rms": self.beam_sizes["y_rms"]
        }

        return results

    def measure_beamsize(self):
        """Take measurement from measurement device,
        store beam sizes in self.beam_sizes"""
        results = self.beamsize_measurement.measure(self.n_measurement_shots)
        if "x_rms" not in self.beam_sizes:
            self.beam_sizes["x_rms"] = []
        if "y_rms" not in self.beam_sizes:
            self.beam_sizes["y_rms"] = []
        self.beam_sizes["x_rms"].append(np.mean(results["Sx"]))
        self.beam_sizes["y_rms"].append(np.mean(results["Sy"]))


class MultiDeviceEmittance(Measurement):
    name: str = "multi_device_emittance"

    def measure(self):
        raise NotImplementedError("Multi-device emittance not yet implemented")
