from lcls_tools.common.devices.reader import create_magnet, create_screen, create_wire
from lcls_tools.common.devices.magnet import MagnetCollection
from lcls_tools.common.devices.device import Device
from lcls_tools.common.measurements.measurement import Measurement

from meme.model import Model

class QuadScanEmittance(Measurement):
    model_beamline: str
    magnet_area: str
    magnet_name: str
    scan_values: list[float]
    rmats: list
    _model: Model = None
    _magnet_collection: MagnetCollection = None
    _magnet_settings: list[dict] = None

    to_device_area: str
    to_device_name: str
    beam_sizes: list
    _to_device: Device = None

    def __init__(self):
        super().__init__()

    @property
    def model(self) -> Model:
        if self._model is None:
            self._model = Model(self.model_beamline)
        return self._model
    
    @property
    def magnet_collection(self) -> MagnetCollection:
        if self._magnet_collection is None:
            self._magnet_collection = create_magnet(area=self.magnet_area)
        return self._magnet_collection
    
    @property
    def magnet_settings(self) -> list[dict]:
        if self._magnet_settings is None:
            self._magnet_settings = [{self.magnet_name:value} for value in self.scan_values]
        return self._magnet_settings
    
    @property
    def to_device(self) -> Device:
        if self._to_device is None:
            if self.to_device_name.startswith('OTR','YAG'):
                self.to_device = create_screen(area=self.to_device_area, name=self.to_device_name)
            else:
                self.to_device = create_wire(area=self.to_device_area, name=self.to_device_name)

    def measure(self):
        self.magnet_collection.scan(scan_settings=self.magnet_settings, function=self.measure_beamsize)

        emittance, bmag, sig, is_valid = compute_emit_bmag(
                                            k = self.scan_values,
                                            beamsize_squared = self.beam_sizes, # [beam_sizes['x_rms'],beam_sizes['y_rms']],
                                            q_len = 0.221, # self.to_device magnet length?
                                            rmat = self.rmats,
                                            beta0 = 0.0001, # ?
                                            alpha0 = 0.0002, # ?
                                            get_bmag = True)

        results = {
            "emittance": emittance,
            "BMAG": bmag
        }

        return results
    
    def measure_beamsize(self):
        self.beam_sizes.append(self.to_device.get_beamsize())
        self.rmats.append(self.model.get_rmat(from_device=self.magnet_collection.name, to_device=self.to_device.name))
    
class MultiDeviceEmittance(Measurement):
    pass

def compute_emit_bmag(self, k, beamsize_squared, q_len, rmat, beta0, alpha0, get_bmag):
    pass                                      