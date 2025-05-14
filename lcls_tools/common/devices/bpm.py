from pydantic import (
    BaseModel,
    SerializeAsAny,
    field_validator,
)
from typing import (
    Dict,
    List,
    Optional,
    Union,
)
from lcls_tools.common.devices.device import (
    Device,
    ControlInformation,
    Metadata,
    PVSet,
)
from epics import PV

EPICS_ERROR_MESSAGE = "Unable to connect to EPICS."


class BPMPVSet(PVSet):
    x: Optional[PV] = None
    y: Optional[PV] = None
    tmit: Optional[PV] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @field_validator("*", mode="before")
    def validate_pv_fields(cls, v: str) -> PV:
        return PV(v)


# TODO
class BPMControlInformation(ControlInformation):
    PVs: SerializeAsAny[BPMPVSet]
    _ctrl_options: SerializeAsAny[Optional[Dict[str, int]]] = dict()

    def __init__(self, *args, **kwargs):
        super(BPMControlInformation, self).__init__(*args, **kwargs)


# TODO
class BPMMetadata(Metadata):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class BPM(Device):
    controls_information: SerializeAsAny[BPMControlInformation]
    metadata: SerializeAsAny[BPMMetadata]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def x(self):
        """Get X value"""
        pv = self.controls_information.PVs.x
        if pv is None:
            raise AttributeError("X PV is not defined for this device")
        return pv.get()

    def x_buffer(self, buffer):
        """Retrieve X signal data from timing buffer"""
        pv = self.controls_information.PVs.x
        if pv is None:
            raise AttributeError("X PV is not defined for this device")
        # get_data_buffer requires PV name as string, not EPICS PV object
        data = buffer.get_data_buffer(self.controls_information.PVs.x.pvname)
        if data is None:
            raise BufferError("No data found in buffer for X PV")
        return data

    @property
    def y(self):
        """Get Y value"""
        pv = self.controls_information.PVs.y
        if pv is None:
            raise AttributeError("Y PV is not defined for this device")
        return pv.get()

    def y_buffer(self, buffer):
        """Retrieve Y signal data from timing buffer"""
        pv = self.controls_information.PVs.y
        if pv is None:
            raise AttributeError("Y PV is not defined for this device")
        # get_data_buffer requires PV name as string, not EPICS PV object
        data = buffer.get_data_buffer(self.controls_information.PVs.y.pvname)
        if data is None:
            raise BufferError("No data found in buffer for Y PV")
        return data

    @property
    def tmit(self):
        """Get TMIT value"""
        pv = self.controls_information.PVs.tmit
        if pv is None:
            raise AttributeError("TMIT PV is not defined for this device")
        return pv.get()

    def tmit_buffer(self, buffer):
        """Retrieve TMIT signal data from timing buffer"""
        pv = self.controls_information.PVs.tmit
        if pv is None:
            raise AttributeError("TMIT PV is not defined for this device")
        # get_data_buffer requires PV name as string, not EPICS PV object
        data = buffer.get_data_buffer(self.controls_information.PVs.tmit.pvname)
        if data is None:
            raise BufferError("No data found in buffer for TMIT PV")
        return data


class BPMCollection(BaseModel):
    bpms: Dict[str, SerializeAsAny[BPM]]

    @field_validator("bpms", mode="before")
    def validate_bpms(cls, v) -> Dict[str, BPM]:
        for name, bpm in v.items():
            bpm = dict(bpm)
            # Set name field for BPM
            bpm.update({"name": name})
            v.update({name: bpm})
        return v

    def _make_bpm_names_list_from_args(
        self, args: Union[str, List[str], None]
    ) -> List[str]:
        bpm_names = args
        if bpm_names:
            if isinstance(bpm_names, str):
                bpm_names = [args]
        else:
            bpm_names = list(self.bpms.keys())
        return bpm_names
