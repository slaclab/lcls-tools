import os
import yaml
from typing import Union
from lcls_tools.common.devices.device import (
    ControlInformationNotFoundError,
    MetadataNotFoundError,
)
from lcls_tools.common.devices.magnet.magnet import YAMLMagnet


def _find_yaml_file(yaml_filename: str) -> str:
    if os.path.isfile(yaml_filename):
        return os.path.abspath(yaml_filename)
    else:
        raise FileNotFoundError(
            f"No such file {yaml_filename}",
        )


def create_magnet(
    yaml_filename: str = None, name: str = None
) -> Union[None, dict, YAMLMagnet]:
    if yaml_filename:
        try:
            location = _find_yaml_file(
                yaml_filename=yaml_filename,
            )
            with open(location, "r") as device_file:
                if name:
                    config_data = yaml.safe_load(device_file)[name]
                    return YAMLMagnet(name=name, **config_data)
                else:
                    return {
                        name: YAMLMagnet(name=name, **config_data)
                        for name, config_data in yaml.safe_load(device_file).items()
                    }
        except FileNotFoundError:
            print(f"Could not find yaml file: {yaml_filename}")
            return None
        except KeyError:
            print(f"Could not find name {name} in {yaml_filename}")
            return None
        except ControlInformationNotFoundError as cinfe:
            print(cinfe)
            return None
        except MetadataNotFoundError as mnfe:
            print(mnfe)
            return None
    else:
        print("Please provide a yaml file location to create a magnet.")
        return None