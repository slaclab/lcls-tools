from typing import Callable

from lcls_tools.common.devices.reader import create_magnet, create_screen, create_wire
from lcls_tools.common.devices.magnet import MagnetCollection
from lcls_tools.common.devices.screen import Screen
from lcls_tools.common.devices.wire import Wire
from lcls_tools.common.measurements.measurement import Measurement
from meme.model import Model

class QuadScanEmittance(Measurement):
    model: Model
    magnet_collection: MagnetCollection
    magnet_settings: dict
    rmats: list
    acquire_data: Callable[..., None]

    screen: Screen
    image_file_locations: list

    wire: Wire

    def __init__(self, model_beamline: str, magnet_area: str, magnet_settings: dict, 
                 to_device_area: str, to_device_name: str):
        self.model = Model(model_beamline)
        self.magnet_collection = create_magnet(area=magnet_area)
        self.magnet_settings = magnet_settings
        if to_device_name.startswith(('YAG','OTR')):
            self.screen = create_screen(area=to_device_area, name=to_device_name)
            self.acquire_data = self.acquire_profmon
        else:
            self.wire = create_wire(area=to_device_area, name=to_device_name)
            self.acquire_data = self.acquire_wire


    def measure(self):
        self.magnet_collection.scan(scan_settings=self.settings, function=self.acquire_data)
        beam_sizes = self.get_beamsize(image_file = self.image_file_locations)  # x_rms, y_rms, x_stdz, y_stdz

        emittance, bmag, sig, is_valid = self.compute_emit_bmag(k = [-6,-3,0],
                                              beamsize_squared = [beam_sizes['x_rms'],beam_sizes['y_rms']],
                                              q_len = 0.221,
                                              rmat = self.rmats,
                                              beta0 = 0.0001,
                                              alpha0 = 0.0002,
                                              get_bmag = True)

        results = {
            "emittance": emittance,
            "BMAG": bmag
        }

        return results
    
    def acquire_profmon(self, magnet_name, to_device_name, num_to_capture=10):
        latest_image_filepath = self.screen.save_images(num_to_capture=num_to_capture)
        self.rmats.append(self.model.get_rmat(from_device=magnet_name, to_device=to_device_name))
        self.image_file_locations.append(latest_image_filepath)
    
    def acquire_wire(self, magnet_name, to_device_name):
        pass

    def get_beamsize(self, image_file):
        pass

    def compute_emit_bmag(self, k, beamsize_squared, q_len, rmat, beta0, alpha0, get_bmag):
        pass                                      