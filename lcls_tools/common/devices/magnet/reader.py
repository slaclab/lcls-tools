import os
import yaml
from typing import Union
from pydantic import ValidationError
from lcls_tools.common.devices.magnet.magnet import Magnet, MagnetCollection

DEFAULT_YAML_LOCATION = "./lcls_tools/common/devices/yaml/"


def _find_yaml_file(area: str) -> str:
    filename = area + ".yaml"
    path = os.path.join(DEFAULT_YAML_LOCATION, filename)
    if os.path.isfile(path):
        return os.path.abspath(path)
    else:
        raise FileNotFoundError(
            f"No such file {path}, please choose another area.",
        )


def create_magnet(
    area: str = None, name: str = None
) -> Union[None, Magnet, MagnetCollection]:
    if area:
        try:
            location = _find_yaml_file(
                area=area,
            )
            with open(location, "r") as device_file:
                config_data = yaml.safe_load(device_file)
                if name:
                    magnet_data = config_data["magnets"][name]
                    magnet_data.update({"name": name})
                    return Magnet(**magnet_data)
                else:
                    return MagnetCollection(**config_data)
        except FileNotFoundError:
            print(f"Could not find yaml file for area: {area}")
            return None
        except KeyError:
            print(f"Could not find name {name} in file for area: {area}")
            return None
        except ValidationError as field_error:
            print(field_error)
            return None
    else:
        print("Please provide a machine area to create a magnet from.")
        return None
