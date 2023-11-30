from typing import List


def get_magnet_controls_information(magnet_names: List[str] = []):
    # return a data structure of the form:
    # {
    #  mag-name-1 : {controls-information-field-1 : value-1, controls-information-field-2 : value-2, ...},
    #  mag-name-2 : {controls-information-field-1 : value-1, controls-information-field-2 : value-2, ...},
    #  ...
    # }
    raise NotImplementedError


def get_screen_controls_information(screen_names: List[str] = []):
    # return a data structure of the form:
    # {
    #  scr-name-1 : {controls-information-field-1 : value-1, controls-information-field-2 : value-2, ...},
    #  scr-name-2 : {controls-information-field-1 : value-1, controls-information-field-2 : value-2, ...},
    #  ...
    # }

    # Stuff like Device-Position mappings for motor/ladder-based screens
    raise NotImplementedError
