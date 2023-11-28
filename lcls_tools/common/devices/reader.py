import os
import yaml
from typing import Union, Optional, Any, Dict
from pydantic import ValidationError
from lcls_tools.common.devices.screen import Screen, ScreenCollection
from lcls_tools.common.devices.magnet import Magnet, MagnetCollection
from lcls_tools.common.devices.area import Area
from lcls_tools.common.devices.beampath import Beampath

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


def create_magnet(
    area: str = None, name: str = None
) -> Union[None, Magnet, MagnetCollection]:
    device_data = _device_data(area=area)
    if not device_data:
        return None
    device_data.update({"devices": device_data["magnets"]})
    device_data.pop("magnets")
    if name:
        try:
            magnet_data = device_data["devices"][name]
            # this data is not available from YAML directly in this form, so we add it here.
            magnet_data.update({"name": name})
            return Magnet(**magnet_data)
        except KeyError:
            print(f"Magnet {name} does not exist in {area}.")
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
    device_data.update({"devices": device_data["screens"]})
    device_data.pop("screens")
    if name:
        try:
            screen_data = device_data["devices"][name]
            # this data is not available from YAML directly in this form, so we add it here.
            screen_data.update({"name": name})
            return Screen(**screen_data)
        except KeyError:
            print(f"Screen {name} does not exist in {area}.")
        except ValidationError as field_error:
            print(field_error)
            return None
    else:
        return ScreenCollection(**device_data)


def create_area(area: str = None) -> Union[None, Area]:
    yaml_data = _device_data(area=area)
    if not yaml_data:
        return None
    try:
        return Area(**yaml_data)
    except ValidationError as field_error:
        print(field_error)
        return None


def _flatten(nested_list):
    if nested_list == []:
        # empty list, no need to flatten
        return nested_list
    if isinstance(nested_list[0], list):
        # first element is a list, so call flatten again
        # and append the result to the result of flatten for the rest of the list
        return _flatten(nested_list[0]) + _flatten(nested_list[1:])
    # we know 0-1 is flattened, flatten 1 -> -1
    return nested_list[:1] + _flatten(nested_list[1:])


def create_beampath(beampath: str = None) -> Union[None, Beampath]:
    # load beampath yaml file to get all areas in beampath
    # create Area class for each area
    # add them to dict with key as Area name and value as Area object.
    beampath_definition_file = os.path.join(DEFAULT_YAML_LOCATION, "beampaths.yaml")
    beampath_definitions = {}
    areas = {}
    with open(beampath_definition_file, "r") as file:
        beampath_definitions = yaml.safe_load(file)
    try:
        areas_to_create = _flatten(beampath_definitions[beampath])
    except KeyError:
        print(
            "Beampath: ", beampath, " does not exist. Please try a different beampath."
        )
    try:
        for area in areas_to_create:
            created_area = create_area(area=area)
            if created_area:
                areas[area] = created_area
        print(areas)
        return Beampath(**{"areas": areas})
    except KeyError as ke:
        print(
            "Area: ",
            ke.args[0],
            " does not exist in ",
            beampath,
            ". Please try a different beampath.",
        )

    pass
