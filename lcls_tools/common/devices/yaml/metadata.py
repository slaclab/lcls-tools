import re
from typing import List
from epics import caget
import os
import yaml


def get_magnet_metadata(
    magnet_names: List[str] = [], method: callable = None, **kwargs
):
    # return a data structure of the form:
    # {
    #  mag-name-1 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  mag-name-2 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  ...
    # }
    if magnet_names and method:
        # Add any additional metadata fields here
        additional_fields = ["Element", "Effective Length (m)"]
        device_elements = method(magnet_names, additional_fields)
        # change field names and values to be in different format
        # if needed
        for magnet in device_elements:
            if "Effective Length (m)" in device_elements[magnet]:
                if device_elements[magnet]["Effective Length (m)"] == "":
                    device_elements[magnet]["Effective Length (m)"] = 0.0
                device_elements[magnet]["l_eff"] = round(
                    float(device_elements[magnet]["Effective Length (m)"]), 3
                )
                del device_elements[magnet]["Effective Length (m)"]
        return device_elements
    else:
        return {}


def get_screen_metadata(basic_screen_data: dict):
    # return a data structure of the form:
    # {
    #  scr-name-1 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  scr-name-2 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  ...
    # }
    from meme.names import list_pvs

    metadata = {}
    for mad_name, info in basic_screen_data.items():
        metadata[mad_name] = {}
        ctrl_name = info["controls_information"]["control_name"]
        flags = list_pvs(ctrl_name + "%INSTALLED")
        hardware = {}
        for i in flags:
            name = re.search("(?<=^" + ctrl_name + ":).*(?=INSTALLED)", i)
            if name is None:
                continue
            name = name.group(0)
            status = caget(i)
            if status is not None:
                hardware[name] = status

        metadata[mad_name]["hardware"] = hardware

    return metadata


def get_wire_metadata(wire_names: List[str] = []):
    # return a data structure of the form:
    # {
    #  wire-name-1 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  wire-name-2 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  ...
    # }
    wire_metadata = {}

    here = os.path.dirname(__file__)
    yaml_path = os.path.join(here, "wire_metadata.yaml")

    with open(yaml_path, "r") as f:
        wire_metadata = yaml.safe_load(f)

    return wire_metadata


def get_lblm_metadata(lblm_names: List[str] = []):
    # return a data structure of the form:
    # {
    #  lblm-name-1 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  lblm-name-2 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  ...
    # }
    if lblm_names:
        raise NotImplementedError("No method of getting additional metadata for lblms.")
    return {}


def get_bpm_metadata(bpm_names: List[str] = []):
    # return a data structure of the form:
    # {
    #  bpm-name-1 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  bpm-name-2 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  ...
    # }
    if bpm_names:
        raise NotImplementedError("No method of getting additional metadata for bpms.")
    return {}


def get_tcav_metadata(tcav_names: List[str] = [], method: callable = None, **kwargs):
    # return a data structure of the form:
    # {
    #  tcav-name-1 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  tcav-name-2 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  ...
    # }
    if tcav_names and method:
        # Add any additional metadata fields here
        additional_fields = [
            "Element",
            "Effective Length (m)",
            "Rf Frequency (MHz)",
        ]
        device_elements = method(tcav_names, additional_fields)
        # change field names and values to be in different format
        # if needed
        for tcav in device_elements:
            if "Effective Length (m)" in device_elements[tcav]:
                if device_elements[tcav]["Effective Length (m)"] == "":
                    device_elements[tcav]["Effective Length (m)"] = 0.0
                device_elements[tcav]["l_eff"] = round(
                    float(device_elements[tcav]["Effective Length (m)"]), 3
                )
                del device_elements[tcav]["Effective Length (m)"]

            if "Rf Frequency (MHz)" in device_elements[tcav]:
                if device_elements[tcav]["Rf Frequency (MHz)"] == "":
                    device_elements[tcav]["Rf Frequency (MHz)"] = 0.0
                device_elements[tcav]["rf_freq"] = float(
                    device_elements[tcav]["Rf Frequency (MHz)"]
                )
                del device_elements[tcav]["Rf Frequency (MHz)"]

        return device_elements
    else:
        return {}


def get_pmt_metadata(pmt_names: List[str] = []):
    # return a data structure of the form:
    # {
    #  bpm-name-1 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  bpm-name-2 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  ...
    # }
    if pmt_names:
        raise NotImplementedError("No method of getting additional metadata for pmts.")
    return {}
