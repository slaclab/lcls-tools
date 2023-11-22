import os
import yaml
import numpy as np
from typing import Union, Optional, Any, Dict
from pydantic import ValidationError
from lcls_tools.common.devices.screen import Screen, ScreenCollection
from lcls_tools.common.devices.magnet import Magnet, MagnetCollection

DEFAULT_YAML_LOCATION = "./lcls_tools/common/devices/yaml/"


def _find_yaml_file(area: str = None, beampath: Optional[str] = None) -> str:
    if area:
        filename = area + ".yaml"
    if beampath:
        filename = "beam_paths.yaml"

    path = os.path.join(DEFAULT_YAML_LOCATION, filename)
    if os.path.isfile(path):
        return os.path.abspath(path)
    else:
        raise FileNotFoundError(
            f"No such file {path}, please choose another area.",
        )


def _device_data(
    area: str = None,
) -> Union[None, Dict[str, Any]]:
    if area:
        try:
            location = _find_yaml_file(
                area=area,
            )
            with open(location, "r") as device_file:
                device_data = yaml.safe_load(device_file)
                return device_data
       
        except FileNotFoundError:
            print(f"Could not find yaml file for area: {area}")
            return None

    else:
        print("Please provide a machine area to create a magnet from.")
        return None
    
def create_beampath():
    raise NotImplementedError

def create_magnet(
    area: str = None, name: str = None
) -> Union[None, Magnet, MagnetCollection]:
    device_data = _device_data(area=area)
    if not device_data: 
        return None

    if name:
        try:
            magnet_data = device_data["magnets"][name]
            # this data is not available from YAML directly in this form, so we add it here.
            magnet_data.update({"name": name})
            return Magnet(**magnet_data)
        except KeyError:
            print(f'Magnet {name} does not exist in {area}.')
        except ValidationError as field_error:
            print(field_error)
            return None
    else:
        return MagnetCollection(**device_data)


def create_screen(
    area: str = None, name: str = None
) -> Union[None, Screen, ScreenCollection]:
    device_data = _device_data(area=area)
    if not device_data: 
       return None

    if name:
        try:
            screen_data = device_data["screens"][name]
            # this data is not available from YAML directly in this form, so we add it here.
            screen_data.update({"name": name})
            return Screen(**screen_data)
        except KeyError:
            print(f'Screen {name} does not exist in {area}.')
        except ValidationError as field_error:
            print(field_error)
            return None
    else:
        return ScreenCollection(**device_data)


