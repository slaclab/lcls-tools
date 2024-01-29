from typing import Union

from lcls_tools.common.devices.device import Device


def dump_data_to_h5py(
        element: Union[Device, Measurement],
        data: dict,
        filename: str = None
):
    """
    Dump data to
    """