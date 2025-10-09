from pydantic import SerializeAsAny

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


class ICTControlInformation(ControlInformation):
    PVs: SerializeAsAny[ICTPVSet]


class ICT(Device):
    controls_information: SerializeAsAny[ICTControlInformation]
    metadata: SerializeAsAny[Metadata]

    def get_charge(self) -> float:
        return self.controls_information.PVs.charge_nC.get(as_numpy=True)
