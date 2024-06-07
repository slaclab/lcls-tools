from lcls_tools.common.devices.reader import create_beampath
from lcls_tools.common.devices.beampath import Beampath


def SC_SXR() -> Beampath:
    """Creates the LCLS-II Soft X-Ray Beampath"""
    return create_beampath(beampath="SC_SXR")


def SC_HXR() -> Beampath:
    """Creates the LCLS-II Hard X-Ray Beampath"""
    return create_beampath(beampath="SC_HXR")


def SC_DASEL() -> Beampath:
    """Creates the DASEL Beampath"""
    return create_beampath(beampath="SC_DASEL")


def SC_DIAG0() -> Beampath:
    """Creates the DIAG0 Beampath"""
    return create_beampath(beampath="SC_DIAG0")
