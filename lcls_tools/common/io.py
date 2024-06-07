from typing import Optional

from lcls_tools.common.measurements.measurement import Measurement


class HDF5IO:
    def __init__(self):
        pass

    def write(
        self,
        measurement_data: dict,
        measurement_obj: Measurement,
        filename: Optional[str] = None,
    ):
        """
        Write data to h5file
        """
        raise NotImplementedError

    def read(self, filename: Optional[str] = None):
        """
        Read data from h5file
        """
        raise NotImplementedError
