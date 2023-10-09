import os
import yaml
import pprint
from typing import Union
from lcls_tools.common.devices.magnet.magnet import YAMLMagnet


def _find_yaml_file(yaml_filename: str) -> str:
    if os.path.isfile(yaml_filename):
        return os.path.abspath(yaml_filename)
    else:
        raise FileNotFoundError(
            f"No such file {yaml_filename}",
        )


def create_magnet(
    yaml_filename: str = None, magnet_name: str = None
) -> Union[None, YAMLMagnet]:
    if yaml_filename:
        try:
            location = _find_yaml_file(
                yaml_filename=yaml_filename,
            )
            with open(location, "r") as file:
                magnet_config_data = yaml.safe_load(file)[magnet_name]
                pprint.pprint(magnet_config_data)
                return YAMLMagnet(name=magnet_name, **magnet_config_data)
        except FileNotFoundError:
            print(f"Could not find yaml file: {yaml_filename}")
            return None
        except KeyError:
            print(f"Could not find name {magnet_name} in {yaml_filename}")
            return None
    else:
        print("Please provide a yaml file location to create a magnet.")
        return None
