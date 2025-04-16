from datetime import datetime
from functools import wraps
from pydantic import (
    Field,
    PositiveFloat,
    NonNegativeFloat,
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
    DeviceCollection,
    Metadata,
    PVSet,
)
from epics import PV


class TCAVPVSet(PVSet):
    amp_set: PV
    phase_set: PV
    rf_enable: PV
    amp_fb: PV
    phase_fb: PV
    mode_configs: PV

    def __init__(self, *args, **kwargs):
        super(TCAVPVSet, self).__init__(*args, **kwargs)

    @field_validator("*", mode="before")
    def validate_pv_fields(cls, v: str) -> PV:
        return PV(v)


class TCAVControlInformation(ControlInformation):
    PVs: SerializeAsAny[TCAVPVSet]
    _ctrl_options: SerializeAsAny[Optional[Dict[str, int]]] = dict()

    def __init__(self, *args, **kwargs):
        super(TCAVControlInformation, self).__init__(*args, **kwargs)
        # Get possible options for TCAV ctrl PV, empty dict by default.


class TCAVMetadata(Metadata):
    def __init__(self, *args, **kwargs):
        super(TCAVMetadata, self).__init__(*args, **kwargs)


class TCAV(Device):
    controls_information: SerializeAsAny[TCAVControlInformation]
    metadata: SerializeAsAny[TCAVMetadata]

    def __init__(self, *args, **kwargs):
        super(TCAV, self).__init__(*args, **kwargs)


class TCAVCollection(DeviceCollection):
    devices: Dict[str, SerializeAsAny[TCAV]] = Field(alias="tcavs")

    def __init__(self, *args, **kwargs):
        super(TCAVCollection, self).__init__(*args, **kwargs)

    @property
    def tcavs(self) -> Dict[str, SerializeAsAny[TCAV]]:
        """A dictionary (key=name, value=tcav) to directly access tcav objects"""
        return self.devices