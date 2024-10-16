import numpy as np

from pydantic import Field
from lcls_tools.common.devices.reader import create_magnet, create_screen, create_wire
from lcls_tools.common.devices.magnet import MagnetCollection
from lcls_tools.common.devices.device import Device
from lcls_tools.common.measurements.measurement import Measurement

from meme.model import Model

class QuadScanEmittance(Measurement):
    model: Model
    magnet_collection: MagnetCollection
    magnet_name: str
    scan_values: list[float]
    _magnet_settings: list[dict] # example: [{"QE04": -6}, {"QE04": -3}, {"QE04": 0}]
    device_measurement: Measurement
    _rmats: list
    _beam_sizes: dict

    def __init__(self):
        super().__init__()

    @property
    def magnet_settings(self) -> list[dict]:
        if self._magnet_settings is None:
            self._magnet_settings = [{self.magnet_name:value} for value in self.scan_values]
        return self._magnet_settings

    def measure(self):
        self._rmats.append(self.model.get_rmat(from_device=self.magnet_name, to_device=self.device_measurement.device.name))
        self.magnet_collection.scan(scan_settings=self.magnet_settings, function=self.measure_beamsize)
        beamsize_squared = np.vstack((self._beam_sizes["x_rms"], self._beam_sizes["y_rms"]))**2
        magnet_length = self.magnet_collection.magnets[self.magnet_name].length
        twiss = self.model.get_twiss(self.magnet_name)
        twiss_betas_alphas = np.array([[twiss["beta_x"],twiss["alpha_x"]],[twiss["beta_y"],twiss["alpha_y"]]])


        emittance, bmag, _, _ = compute_emit_bmag(
            k = self.scan_values,
            beamsize_squared = beamsize_squared,
            q_len = magnet_length,
            rmat = self._rmats,
            twiss_design = twiss_betas_alphas,
            # thin_lens = ,
            # maxiter = 
        )

        results = {
            "emittance": emittance,
            "BMAG": bmag
        }

        return results
    
    def measure_beamsize(self):
        results = self.device_measurement.measure()
        if "x_rms" not in self._beam_sizes:
            self._beam_sizes["x_rms"] = []
        if "y_rms" not in self._beam_sizes:
            self._beam_sizes["y_rms"] = []
        self._beam_sizes["x_rms"].append(results["Sx"])
        self._beam_sizes["y_rms"].append(results["Sy"])
    
class MultiDeviceEmittance(Measurement):
    pass

def compute_emit_bmag(self, k, beamsize_squared, q_len, rmat, twiss_design, thin_lens, maxiter):
    pass                                      