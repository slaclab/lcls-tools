from lcls_tools.common.devices.reader import create_beampath


def SC_SXR():
    return create_beampath(beampath="SC_SXR")


def SC_HXR():
    return create_beampath(beampath="SC_HXR")


def SC_DAZEL():
    return create_beampath(beampath="SC_DAZEL")


def SC_DIAG0():
    return create_beampath(beampath="SC_DIAG0")
