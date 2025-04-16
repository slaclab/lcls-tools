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
    bctrl: PV
    bact: PV
    bdes: PV
    bcon: PV
    ctrl: PV
    bmin: PV
    bmax: PV

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
        options = self.PVs.ctrl.get_ctrlvars(timeout=1)
        if options:
            [
                self._ctrl_options.update({option: i})
                for i, option in enumerate(options["enum_strs"])
            ]

    @property
    def ctrl_options(self):
        return self._ctrl_options


class TCAVMetadata(Metadata):
    def __init__(self, *args, **kwargs):
        super(TCAVMetadata, self).__init__(*args, **kwargs)


class TCAV(Device):
    controls_information: SerializeAsAny[TCAVControlInformation]
    metadata: SerializeAsAny[TCAVMetadata]

    def __init__(self, *args, **kwargs):
        super(TCAV, self).__init__(*args, **kwargs)
