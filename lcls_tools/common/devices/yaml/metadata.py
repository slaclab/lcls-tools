from typing import List


def get_magnet_metadata(magnet_names: List[str] = []):
    # return a data structure of the form:
    # {
    #  mag-name-1 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  mag-name-2 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  ...
    # }
    if magnet_names:
        raise NotImplementedError(
            "No method of getting additional metadata for magnets."
        )
    return {}


def get_screen_metadata(screen_names: List[str] = []):
    # return a data structure of the form:
    # {
    #  scr-name-1 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  scr-name-2 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  ...
    # }
    if screen_names:
        raise NotImplementedError(
            "No method of getting additional metadata for screens."
        )
    return {}
