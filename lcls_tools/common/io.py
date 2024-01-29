from typing import Optional

from lcls_tools.common.measurement.measurement import Measurement


class HDF5Dumper:
    def __init__(self):
        pass

    def dump_data_to_file(
            self,
            measurement_data: dict,
            measurement_obj: Measurement,
            filename: Optional[str] = None
    ):
        """
        Dump data to h5file
        """
        pass
