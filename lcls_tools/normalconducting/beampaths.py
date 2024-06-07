from lcls_tools.common.devices.reader import create_beampath


def CU_SXR():
    """Creates the LCLS Soft X-Ray Beampath"""
    return create_beampath(beampath="CU_SXR")


def CU_HXR():
    """Creates the LCLS Hard X-Ray Beampath"""
    return create_beampath(beampath="CU_HXR")


def CU_ALINE():
    """Creates the LCLS ALINE Beampath"""
    return create_beampath(beampath="CU_ALINE")
