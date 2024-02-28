from lcls_tools.common.devices.reader import create_beampath


def CU_SXR():
    return create_beampath(beampath="CU_SXR")


def CU_HXR():
    return create_beampath(beampath="CU_HXR")


def CU_ALINE():
    return create_beampath(beampath="CU_ALINE")
