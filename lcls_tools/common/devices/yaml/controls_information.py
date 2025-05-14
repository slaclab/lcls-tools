from typing import List


def get_magnet_controls_information(magnet_names: List[str] = None):
    # return a data structure of the form:
    # {
    #  mag-name-1 : {controls-information-field-1 : value-1, controls-information-field-2 : value-2, ...},
    #  mag-name-2 : {controls-information-field-1 : value-1, controls-information-field-2 : value-2, ...},
    #  ...
    # }
    if magnet_names:
        raise NotImplementedError(
            "No method of getting additional controls_information for magnets."
        )
    return {}


def get_screen_controls_information(screen_names: List[str] = None):
    # return a data structure of the form:
    # {
    #  scr-name-1 : {controls-information-field-1 : value-1, controls-information-field-2 : value-2, ...},
    #  scr-name-2 : {controls-information-field-1 : value-1, controls-information-field-2 : value-2, ...},
    #  ...
    # }

    # Stuff like Device-Position mappings for motor/ladder-based screens
    if screen_names:
        raise NotImplementedError(
            "No method of getting additional controls_information for screens."
        )
    return {}


def get_wire_controls_information(wire_names: List[str] = None):
    # return a data structure of the form:
    # {
    #  scr-name-1 : {controls-information-field-1 : value-1, controls-information-field-2 : value-2, ...},
    #  scr-name-2 : {controls-information-field-1 : value-1, controls-information-field-2 : value-2, ...},
    #  ...
    # }

    # Stuff like Device-Position mappings for motor/ladder-based screens
    if wire_names:
        raise NotImplementedError(
            "No method of getting additional controls_information for wires."
        )
    return {}


def get_lblm_controls_information(lblm_names: List[str] = None):
    # return a data structure of the form:
    # {
    #  scr-name-1 : {controls-information-field-1 : value-1, controls-information-field-2 : value-2, ...},
    #  scr-name-2 : {controls-information-field-1 : value-1, controls-information-field-2 : value-2, ...},
    #  ...
    # }

    # Stuff like Device-Position mappings for motor/ladder-based screens
    if lblm_names:
        raise NotImplementedError(
            "No method of getting additional controls_information for LBLMs."
        )
    return {}


def get_bpm_controls_information(bpm_names: List[str] = None):
    # return a data structure of the form:
    # {
    #  bpm-name-1 : {controls-information-field-1 : value-1, controls-information-field-2 : value-2, ...},
    #  bpm-name-2 : {controls-information-field-1 : value-1, controls-information-field-2 : value-2, ...},
    #  ...
    # }

    # Stuff like Device-Position mappings for motor/ladder-based screens
    if bpm_names:
        raise NotImplementedError(
            "No method of getting additional controls_information for bpms."
        )
    return {}


def get_tcav_controls_information(tcav_names: List[str] = []):
    # return a data structure of the form:
    # {
    #  lblm-name-1 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  lblm-name-2 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  ...
    # }
    if tcav_names:
        raise NotImplementedError(
            "No method of getting additional controls_information for TCAVs."
        )
    return {}
