from typing import List


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


def get_wire_metadata(wire_names: List[str] = []):
    # return a data structure of the form:
    # {
    #  scr-name-1 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  scr-name-2 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  ...
    # }
    htr_lblms = ["LBLM01A", "LBLM01B"]
    diag0_lblms = ["SBLM01A"]
    col1_lblms = ["LBLM03A", "LBLM04A", "TMITLOSS"]
    emit2_lblms = ["LBLM04A", "LBLM07A", "TMITLOSS"]
    byp_lblms = ["LBLM13A", "LBLM11A", "LBLM12A", "LBLM22A", "LBLM11A_3", "TMITLOSS"]
    spd_lblms = ["LBLM22A"]
    ltus_lblms = [
        "PMT122",
        "PMT246",
        "PMT430",
        "PMT431",
        "PMT550",
        "PMT755",
        "PMT756",
        "PMT820",
        "PMT850",
        "LBLM32A",
        "TMITLOSS",
    ]

    wire_metadata = {
        "WS0H04": {"lblms": htr_lblms},
        "WSDG0": {"lblms": diag0_lblms},
        "WSC104": {"lblms": col1_lblms.copy()},
        "WSC106": {"lblms": col1_lblms.copy()},
        "WSC108": {"lblms": col1_lblms.copy()},
        "WSC110": {"lblms": col1_lblms.copy()},
        "WSEMIT2": {"lblms": emit2_lblms},
        "WSBP1": {"lblms": byp_lblms.copy()},
        "WSBP2": {"lblms": byp_lblms.copy()},
        "WSBP3": {"lblms": byp_lblms.copy()},
        "WSBP4": {"lblms": byp_lblms.copy()},
        "WSSP1D": {"lblms": spd_lblms},
        "WS31B": {"lblms": ltus_lblms.copy()},
        "WS32B": {"lblms": ltus_lblms.copy()},
        "WS33B": {"lblms": ltus_lblms.copy()},
        "WS34B": {"lblms": ltus_lblms.copy()},
    }
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
