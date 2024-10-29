import numpy as np

from lcls_tools.common.devices.magnet import MagnetCollection
from lcls_tools.common.measurements.measurement import Measurement
from lcls_tools.common.data.model_general_calcs import bdes_to_kmod, get_optics

from typing import Optional


class QuadScanEmittance(Measurement):
    beamline: str
    energy: float
    magnet_collection: MagnetCollection
    magnet_name: str
    scan_values: list[float]
    device_measurement: Measurement
    rmats: Optional[np.ndarray]
    twiss: Optional[np.ndarray]
    beam_sizes: Optional[dict]

    def __init__(self):
        super().__init__()

    @property
    def magnet_settings(self) -> list[dict]:
        return [{self.magnet_name: value} for value in self.scan_values]

    def measure(self):
        """Returns the emittance and BMAG
        Get the rmats and twiss parameters
        Perform the scan, measuring beam sizes at each scan value
        Compute the emittance and BMAG using the geometric focusing strengths, 
        beam sizes squared, magnet length, rmats, and twiss betas and alphas"""
        self.rmats, self.twiss = get_optics(self.magnet_name, self.device_measurement.device.name, self.beamline)
        self.magnet_collection.scan(scan_settings=self.magnet_settings, function=self.measure_beamsize)
        beamsize_squared = np.vstack((self.beam_sizes["x_rms"], self.beam_sizes["y_rms"]))**2
        magnet_length = self.magnet_collection.magnets[self.magnet_name].length
        twiss_betas_alphas = np.array([[self.twiss["beta_x"], self.twiss["alpha_x"]], 
                                       [self.twiss["beta_y"], self.twiss["alpha_y"]]])
        kmod = bdes_to_kmod(self.energy, magnet_length, self.scan_values)
        emittance, bmag, _, _ = compute_emit_bmag(
            k = kmod,
            beamsize_squared = beamsize_squared,
            q_len = magnet_length,
            rmat = self.rmats,
            twiss_design = twiss_betas_alphas
        )

        results = {
            "emittance": emittance,
            "BMAG": bmag
        }

        return results
    
    def measure_beamsize(self):
        """Take measurement from measurement device, store beam sizes in self.beam_sizes"""
        results = self.device_measurement.measure()
        if "x_rms" not in self.beam_sizes:
            self.beam_sizes["x_rms"] = []
        if "y_rms" not in self.beam_sizes:
            self.beam_sizes["y_rms"] = []
        self.beam_sizes["x_rms"].append(results["Sx"])
        self.beam_sizes["y_rms"].append(results["Sy"])
    
class MultiDeviceEmittance(Measurement):
    pass

def compute_emit_bmag(self, k, beamsize_squared, q_len, rmat, twiss_design, thin_lens, maxiter):
    pass
