from pydantic import (
    BaseModel,
    SerializeAsAny,
    field_validator,
)
from typing import (
    Dict,
    Optional,
)
from lcls_tools.common.devices.device import (
    Device,
    ControlInformation,
    Metadata,
    PVSet,
)
from epics import PV

EPICS_ERROR_MESSAGE = "Unable to connect to EPICS."


class PMTPVSet(PVSet):
    qdcraw: PV

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class PMTControlInformation(ControlInformation):
    PVs: SerializeAsAny[PMTPVSet]
    _ctrl_options: SerializeAsAny[Optional[Dict[str, int]]] = dict()

    def __init__(self, *args, **kwargs):
        super(PMTControlInformation, self).__init__(*args, **kwargs)


class PMTMetadata(Metadata):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class PMT(Device):
    controls_information: SerializeAsAny[PMTControlInformation]
    metadata: SerializeAsAny[PMTMetadata]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def qdcraw_buffer(self, buffer):
        """Retrieve QDCRAW signal data from timing buffer"""
        data = buffer.get_data_buffer(
            f"{self.controls_information.control_name}:QDCRAW"
        )
        if data is None:
            raise BufferError("No data in buffer or PV not found")
        return data

    @property
    def qdcraw(self):
        """Get QDCRAW value"""
        return self.controls_information.PVs.qdcraw.get()


class PMTCollection(BaseModel):
    pmts: Dict[str, SerializeAsAny[PMT]]

    @field_validator("pmts", mode="before")
    def validate_pmts(cls, v) -> Dict[str, PMT]:
        for name, pmt in v.items():
            pmt = dict(pmt)
            # Set name field for PMT
            pmt.update({"name": name})
            v.update({name: pmt})
        return v
