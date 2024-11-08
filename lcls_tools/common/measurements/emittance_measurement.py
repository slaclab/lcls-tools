import numpy as np
from pydantic import ConfigDict

from lcls_tools.common.devices.magnet import MagnetCollection
from lcls_tools.common.measurements.measurement import Measurement
from lcls_tools.common.data.model_general_calcs import bdes_to_kmod, get_optics

from typing import Optional


class QuadScanEmittance(Measurement):
    """Use a quad and profile monitor/wire scanner to perform an emittance measurement
    ------------------------
    Arguments:
    beamline: beamline where the devices are located
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
    beamline: str
    energy: float
    magnet_collection: MagnetCollection
    magnet_name: str
    # TODO: remove magnet_length once lengths added to yaml files
    magnet_length: float
    scan_values: list[float]
    device_measurement: Measurement

    rmat: Optional[np.ndarray] = None
    twiss: Optional[np.ndarray] = None
    beam_sizes: Optional[dict] = {}

    name: str = "quad_scan_emittance"
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def magnet_settings(self) -> list[dict]:
        return [{self.magnet_name: value} for value in self.scan_values]

    def measure(self):
        """Returns the emittance, BMAG, x_rms and y_rms
        Get the rmat, twiss parameters, and measured beam sizes
        Perform the scan, measuring beam sizes at each scan value
        Compute the emittance and BMAG using the geometric focusing strengths,
        beam sizes squared, magnet length, rmat, and twiss betas and alphas"""
        self.magnet_collection.scan(scan_settings=self.magnet_settings, function=self.measure_beamsize)
        self.rmat, self.twiss = get_optics(self.magnet_name, self.device_measurement.device.name, self.beamline)
        beamsize_squared = np.vstack((self.beam_sizes["x_rms"], self.beam_sizes["y_rms"]))**2
        # TODO: uncomment once lengths added to yaml files
        # magnet_length = self.magnet_collection.magnets[self.magnet_name].length
        rmat = np.array([self.rmat[0:2, 0:2], self.rmat[2:4, 2:4]])  # x rmat and y rmat
        twiss_betas_alphas = np.array([[self.twiss["beta_x"], self.twiss["alpha_x"]],
                                       [self.twiss["beta_y"], self.twiss["alpha_y"]]])
        kmod = bdes_to_kmod(self.energy, self.magnet_length, np.array(self.scan_values))
        emittance, bmag, _, _ = compute_emit_bmag(
            k=kmod,
            beamsize_squared=beamsize_squared,
            q_len=self.magnet_length,
            rmat=rmat,
            twiss_design=twiss_betas_alphas
        )

        results = {
            "emittance": emittance,
            "BMAG": bmag,
            "x_rms": self.beam_sizes["x_rms"],
            "y_rms": self.beam_sizes["y_rms"]
        }

        return results

    def measure_beamsize(self):
        """Take measurement from measurement device, store beam sizes in self.beam_sizes"""
        results = self.device_measurement.measure()
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


# TODO: delete and import actual compute_emit_bmag
def compute_emit_bmag(self, k, beamsize_squared, q_len, rmat, twiss_design, thin_lens, maxiter):
    raise NotImplementedError("compute_emit_bmag to be implemented elsewhere")
