import re
from typing import List
from epics import caget


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
    #  scr-name-1 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  scr-name-2 : {metadata-field-1 : value-1, metadata-field-2 : value-2},
    #  ...
    # }
    htr_lblms = ["LBLM01A:HTR", "LBLM01B:HTR"]
    htr_tmit_before = ["BPMS:GUNB:925", "BPMS:HTR:120", "BPMS:HTR:320"]
    htr_tmit_after = [
        "BPMS:HTR:760",
        "BPMS:HTR:830",
        "BPMS:HTR:860",
        "BPMS:HTR:960",
    ]
    diag0_lblms = ["SBLM01A:DIAG0"]
    diag0_tmit_before = [
        "BPMS:DIAG0:190",
        "BPMS:DIAG0:210",
        "BPMS:DIAG0:230",
        "BPMS:DIAG0:270",
        "BPMS:DIAG0:285",
        "BPMS:DIAG0:330",
        "BPMS:DIAG0:370",
        "BPMS:DIAG0:390",
    ]
    diag0_tmit_after = ["BPMS:DIAG0:470", "BPMS:DIAG0:520"]
    col1_lblms = ["LBLM03A:L1B", "LBLM04A:L2B", "TMITLOSS:COL1"]
    col1_tmit_before = [
        "BPMS:BC1B:125",
        "BPMS:BC1B:440",
        "BPMS:COL1:120",
        "BPMS:COL1:260",
        "BPMS:COL1:280",
        "BPMS:COL1:320",
    ]
    col1_tmit_after = [
        "BPMS:BPN27:400",
        "BPMS:BPN28:200",
        "BPMS:BPN28:400",
        "BPMS:SPD:135",
        "BPMS:SPD:255",
        "BPMS:SPD:340",
        "BPMS:SPD:420",
        "BPMS:SPD:525",
    ]
    emit2_lblms = ["LBLM04A:L2B", "LBLM07A:L3B", "TMITLOSS:EMIT2"]
    emit2_tmit_before = [
        "BPMS:BC2B:150",
        "BPMS:BC2B:530",
        "BPMS:EMIT2:150",
        "BPMS:EMIT2:300",
    ]
    emit2_tmit_after = [
        "BPMS:SPS:780",
        "BPMS:SPS:830",
        "BPMS:SPS:840",
        "BPMS:SLTS:150",
        "BPMS:SLTS:430",
        "BPMS:SLTS:460",
    ]
    byp_lblms = ["LBLM11A_1:BYP", "LBLM11A_2:BYP", "LBLM11A_3:BYP", "TMITLOSS:BYP"]
    byp_tmit_before = [
        "BPMS:L3B:3583",
        "BPMS:EXT:351",
        "BPMS:EXT:748",
        "BPMS:DOG:120",
        "BPMS:DOG:135",
        "BPMS:DOG:150",
        "BPMS:DOG:200",
        "BPMS:DOG:215",
        "BPMS:DOG:230",
        "BPMS:DOG:280",
        "BPMS:DOG:335",
        "BPMS:DOG:355",
        "BPMS:DOG:405",
    ]
    byp_tmit_after = [
        "BPMS:BPN23:400",
        "BPMS:BPN24:400",
        "BPMS:BPN25:400",
        "BPMS:BPN26:400",
        "BPMS:BPN27:400",
        "BPMS:BPN28:200",
        "BPMS:BPN28:400",
        "BPMS:SPD:135",
        "BPMS:SPD:255",
        "BPMS:SPD:340",
        "BPMS:SPD:420",
        "BPMS:SPD:525",
        "BPMS:SPD:570",
        "BPMS:SPD:700",
        "BPMS:SPD:955",
    ]
    spd_lblms = ["LBLM22A:SPS"]
    spd_tmit_before = [
        "BPMS:SPD:135",
        "BPMS:SPD:255",
        "BPMS:SPD:340",
        "BPMS:SPD:420",
        "BPMS:SPD:525",
        "BPMS:SPD:570",
    ]
    spd_tmit_after = ["BPMS:SPD:700", "BPMS:SPD:955", "BPMS:SLTD:625"]
    ltus_lblms = [
        "LBLMS32A:LTUS",
        "TMITLOSS:LTUS",
    ]
    ltus_tmit_before = [
        "BPMS:BPN27:400",
        "BPMS:BPN28:200",
        "BPMS:BPN28:400",
        "BPMS:SPD:135",
        "BPMS:SPD:255",
        "BPMS:SPD:340",
        "BPMS:SPS:572",
        "BPMS:SPS:580",
        "BPMS:SPS:640",
        "BPMS:SPS:710",
        "BPMS:SPS:770",
        "BPMS:SPS:780",
        "BPMS:SPS:830",
        "BPMS:SPS:840",
        "BPMS:SLTS:150",
    ]
    ltus_tmit_after = ["BPMS:DMPS:381", "BPMS:DMPS:502", "BPMS:DMPS:693"]

    wire_metadata = {
        "WS0H04": {
            "lblms": htr_lblms,
            "bpms_before_wire": htr_tmit_before,
            "bpms_after_wire": htr_tmit_after,
        },
        "WSDG0": {
            "lblms": diag0_lblms,
            "bpms_before_wire": diag0_tmit_before,
            "bpms_after_wire": diag0_tmit_after,
        },
        "WSC104": {
            "lblms": col1_lblms.copy(),
            "bpms_before_wire": col1_tmit_before.copy(),
            "bpms_after_wire": col1_tmit_after.copy(),
        },
        "WSC106": {
            "lblms": col1_lblms.copy(),
            "bpms_before_wire": col1_tmit_before.copy(),
            "bpms_after_wire": col1_tmit_after.copy(),
        },
        "WSC108": {
            "lblms": col1_lblms.copy(),
            "bpms_before_wire": col1_tmit_before.copy(),
            "bpms_after_wire": col1_tmit_after.copy(),
        },
        "WSC110": {
            "lblms": col1_lblms.copy(),
            "bpms_before_wire": col1_tmit_before.copy(),
            "bpms_after_wire": col1_tmit_after.copy(),
        },
        "WSEMIT2": {
            "lblms": emit2_lblms,
            "bpms_before_wire": emit2_tmit_before,
            "bpms_after_wire": emit2_tmit_after,
        },
        "WSBP1": {
            "lblms": byp_lblms.copy(),
            "bpms_before_wire": byp_tmit_before.copy(),
            "bpms_after_wire": byp_tmit_after.copy(),
        },
        "WSBP2": {
            "lblms": byp_lblms.copy(),
            "bpms_before_wire": byp_tmit_before.copy(),
            "bpms_after_wire": byp_tmit_after.copy(),
        },
        "WSBP3": {
            "lblms": byp_lblms.copy(),
            "bpms_before_wire": byp_tmit_before.copy(),
            "bpms_after_wire": byp_tmit_after.copy(),
        },
        "WSBP4": {
            "lblms": byp_lblms.copy(),
            "bpms_before_wire": byp_tmit_before.copy(),
            "bpms_after_wire": byp_tmit_after.copy(),
        },
        "WSSP1D": {
            "lblms": spd_lblms,
            "bpms_before_wire": spd_tmit_before,
            "bpms_after_wire": spd_tmit_after,
        },
        "WS31B": {
            "lblms": ltus_lblms.copy(),
            "bpms_before_wire": ltus_tmit_before.copy(),
            "bpms_after_wire": ltus_tmit_after.copy(),
        },
        "WS32B": {
            "lblms": ltus_lblms.copy(),
            "bpms_before_wire": ltus_tmit_before.copy(),
            "bpms_after_wire": ltus_tmit_after.copy(),
        },
        "WS33B": {
            "lblms": ltus_lblms.copy(),
            "bpms_before_wire": ltus_tmit_before.copy(),
            "bpms_after_wire": ltus_tmit_after.copy(),
        },
        "WS34B": {
            "lblms": ltus_lblms.copy(),
            "bpms_before_wire": ltus_tmit_before.copy(),
            "bpms_after_wire": ltus_tmit_after.copy(),
        },
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
