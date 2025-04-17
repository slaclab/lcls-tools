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
    #add af state and pf state
    #TODO: change amp_fb to amp_fbenb 

    def __init__(self, *args, **kwargs):
        super(TCAVPVSet, self).__init__(*args, **kwargs)

    @field_validator("*", mode="before")
    def validate_pv_fields(cls, v: str) -> PV:
        return PV(v)


class TCAVControlInformation(ControlInformation):
    PVs: SerializeAsAny[TCAVPVSet]

    def __init__(self, *args, **kwargs):
        super(TCAVControlInformation, self).__init__(*args, **kwargs)
        # Get possible options for TCAV ctrl PV, empty dict by default.


class TCAVMetadata(Metadata):
    l_eff: Optional[NonNegativeFloat] = None
    rf_freq: Optional[NonNegativeFloat] = None
    def __init__(self, *args, **kwargs):
        super(TCAVMetadata, self).__init__(*args, **kwargs)


class TCAV(Device):
    controls_information: SerializeAsAny[TCAVControlInformation]
    metadata: SerializeAsAny[TCAVMetadata]

    def __init__(self, *args, **kwargs):
        super(TCAV, self).__init__(*args, **kwargs)

    @property
    def amp_set(self):
        return self.controls_information.PVs.amp_set.get()
    
    @amp_set.setter
    def amp_set(self, amplitude):
        if not isinstance(amplitude, float):
            return
        self.controls_information.PVs.amp_set = amplitude

    @property
    def phase_set(self):
        return self.controls_information.PVs.phase_set.get()
    
    @phase_set.setter
    def phase_set(self, phase):
        if not isinstance([phase], float):
            return
        self.controls_information.PVs.phase = phase
    
    @property
    def amp_fb(self):
        return self.controls_information.PVs.amp_fb.get()
    
    @amp_fb.setter
    def amp_fb(self, state: Union[str,int]):
        if not isinstance(state, str) or not isinstance(state, int):
            return
        self.controls_information.PVs.amp_fb = state

    @property
    def phase_fb(self):
        return self.controls_information.PVs.phase_fb.get()
    
    @phase_fb.setter
    def phase_set(self, state: Union[str,int]):
        if not isinstance(state, str) or not isinstance(state, int):
            return
        self.controls_information.PVs.phase_fb = state
    #TODO: add other pvs
    #TODO: mode config needs some type of enum thing check what was done for magnet enum pvs

    @property
    def l_eff(self):
        """Returns the effective length in meters"""
        return self.metadata.l_eff

    @l_eff.setter
    def l_eff(self,length):
        if not isinstance(length, float):
            return
        self.metadata.l_eff = length

    @property
    def rf_freq(self):
        """Returns the Rf frequency in MHz"""
        return self.metadata.rf_freq




# probably dont need a collection of tcavs, no area will have more than one
class TCAVCollection(DeviceCollection):
    devices: Dict[str, SerializeAsAny[TCAV]] = Field(alias="tcavs")

    def __init__(self, *args, **kwargs):
        super(TCAVCollection, self).__init__(*args, **kwargs)

    @property
    def tcavs(self) -> Dict[str, SerializeAsAny[TCAV]]:
        """A dictionary (key=name, value=tcav) to directly access tcav objects"""
        return self.devices