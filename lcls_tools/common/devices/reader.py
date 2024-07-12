import os
import yaml
from typing import Union, Optional, Any, Dict
from pydantic import ValidationError
from lcls_tools.common.devices.screen import Screen, ScreenCollection
from lcls_tools.common.devices.magnet import Magnet, MagnetCollection
from lcls_tools.common.devices.area import Area
from lcls_tools.common.devices.beampath import Beampath

DEFAULT_YAML_LOCATION = "./lcls_tools/common/devices/yaml/"


def _find_yaml_file(
    area: str = None,
    beampath: Optional[str] = None,
) -> str:
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
    device_type: str = None,
    name: str = None,
) -> Union[None, Dict[str, Any]]:
    if area:
        try:
            location = _find_yaml_file(
                area=area,
            )
            with open(location, "r") as device_file:
                device_data = yaml.safe_load(device_file)
                if device_type:
                    if name:
                        return device_data[device_type][name]
                    return {device_type: device_data[device_type]}
                return device_data
        except FileNotFoundError:
            print(f"Could not find yaml file for area: {area}")
            return None
        except KeyError as ke:
            if ke.args[0] == device_type:
                print("Device type ", device_type, " not supported.")
                return None
            if ke.args[0] == name:
                print(
                    "No device of type: ",
                    device_type,
                    " with name ",
                    name,
                    " not in definition for ",
                    area,
                )
                return None

    else:
        print("Please provide a machine area to create a ", device_type, " from.")
        return None


def create_magnet(
    area: str = None, name: str = None
) -> Union[None, Magnet, MagnetCollection]:
    device_data = _device_data(area=area, device_type="magnets", name=name)
    if not device_data:
        return None
    if name:
        try:
            # this data is not available from YAML directly in this form, so we add it here.
            device_data.update({"name": name})
            return Magnet(**device_data)
        except ValidationError as field_error:
            print(field_error)
            return None
    else:
        return MagnetCollection(**device_data)


def create_screen(
    area: str = None, name: str = None
) -> Union[None, Screen, ScreenCollection]:
    device_data = _device_data(area=area, device_type="screens", name=name)
    if not device_data:
        return None
    if name:
        try:
            # this data is not available from YAML directly in this form, so we add it here.
            device_data.update({"name": name})
            return Screen(**device_data)
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
        return Area(name=area, **yaml_data)
    except ValidationError as field_error:
        print("Error trying to create area", area, " : ", field_error)
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
        return None
    try:
        for area in areas_to_create:
            created_area = create_area(area=area)
            if created_area:
                areas[area] = created_area
        return Beampath(name=beampath, **{"areas": areas})
    except KeyError as ke:
        print(
            "Area: ",
            ke.args[0],
            " does not exist in ",
            beampath,
            ". Please try a different beampath.",
        )
        return None
