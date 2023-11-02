import os
import yaml
from typing import Union
from pydantic import ValidationError
from lcls_tools.common.devices.magnet.model import Magnet, MagnetCollection


def _find_yaml_file(yaml_filename: str) -> str:
    if os.path.isfile(yaml_filename):
        return os.path.abspath(yaml_filename)
    else:
        raise FileNotFoundError(
            f"No such file {yaml_filename}",
        )


def create_magnet(
    yaml_filename: str = None, name: str = None
) -> Union[None, Magnet, MagnetCollection]:
    if yaml_filename:
        try:
            location = _find_yaml_file(
                yaml_filename=yaml_filename,
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
            print(f"Could not find yaml file: {yaml_filename}")
            return None
        except KeyError:
            print(f"Could not find name {name} in {yaml_filename}")
            return None
        except ValidationError as field_error:
            print(field_error)
            return None
    else:
        print("Please provide a yaml file location to create a magnet.")
        return None
