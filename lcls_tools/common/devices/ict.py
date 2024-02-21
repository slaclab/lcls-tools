from pydantic import field_validator, SerializeAsAny

from lcls_tools.common.devices.device import Device, PVSet, ControlInformation, Metadata
from epics import PV


class ICTPVSet(PVSet):
    """
    We list the potential PVs below and only
    use the ones that are set to be PV-typed after
    initialisation.
    """

    charge_nC: PV

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @field_validator("*", mode="before")
    def validate_pv_fields(cls, v: str):
        """Convert each PV string from YAML into a PV object"""
        return PV(v)


class ICTControlInformation(ControlInformation):
    PVs: SerializeAsAny[ICTPVSet]


class ICT(Device):
    controls_information: SerializeAsAny[ICTControlInformation]
    metadata: SerializeAsAny[Metadata]

    def get_charge(self) -> float:
        return self.controls_information.PVs.charge_nC.get(as_numpy=True)
