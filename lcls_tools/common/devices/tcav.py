from datetime import datetime
from functools import wraps
from pydantic import (
    Field,
    NonNegativeFloat,
    SerializeAsAny,
    field_validator,
)
from typing import (
    Dict,
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
    amp_fbenb: PV
    phase_fbenb: PV
    amp_fbst: PV
    phase_fbst: PV
    mode_config: PV

    def __init__(self, *args, **kwargs):
        super(TCAVPVSet, self).__init__(*args, **kwargs)

    @field_validator("*", mode="before")
    def validate_pv_fields(cls, v: str) -> PV:
        return PV(v)


class TCAVControlInformation(ControlInformation):
    PVs: SerializeAsAny[TCAVPVSet]
    _mode_config_options: SerializeAsAny[Optional[Dict[str, int]]] = dict()

    def __init__(self, *args, **kwargs):
        super(TCAVControlInformation, self).__init__(*args, **kwargs)

    def set_mode_config_option(self):
        mode_config_options = self.PVs.mode_configs.get_ctrlvars(timeout=1)
        if mode_config_options:
            [
                self._mode_config_options.update({option: i})
                for i, option in enumerate(mode_config_options["enum_strs"])
            ]

    @property
    def mode_config_options(self):
        return self._mode_config_options
    

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
    """
    def check_options(self, options_to_check: Union[str,List]):
        def decorator(function):
            @wraps(function)
            def decorated(function, *args, **kwargs):
                if isinstance(options_to_check, str):
                    options = [options_to_check]
                for option in options:
                    if option not in self.controls_information.mode_config_options:
                        print(
                            f"unable to perform process {option} with this TCAV {self.name}"
                        )
                        return
                return function(self, *args, **kwargs)
            return decorated

        return decorator
    """
    def check_state(f):
        """Decorator to only allow transitions in 'Ready' state"""

        def decorated(self, *args, **kwargs):
            if self.mode_config == "Disable":
                print("Unable to perform action, TCAV is in Disabled state")
                return
            return f(self, *args, **kwargs)

        return decorated


    @property
    def amp_set(self):
        return self.controls_information.PVs.amp_set.get()
    
    @amp_set.setter
    @check_state
    def amp_set(self, amplitude):
        if not isinstance(amplitude, float):
            return
        self.controls_information.PVs.amp_set = amplitude

    @property
    def phase_set(self):
        return self.controls_information.PVs.phase_set.get()
    
    @phase_set.setter
    @check_state
    def phase_set(self, phase):
        if not isinstance([phase], float):
            return
        self.controls_information.PVs.phase = phase
    
    @property
    def amp_fbenb(self):
        return self.controls_information.PVs.amp_fbenb.get()
    
    @amp_fbenb.setter
    @check_state
    def amp_fbenb(self, state: Union[str, int]):
        if not isinstance(state, str) or not isinstance(state, int):
            return
        self.controls_information.PVs.amp_fbenb = state

    @property
    def phase_fbenb(self):
        return self.controls_information.PVs.phase_fbenb.get()
    
    @phase_fbenb.setter
    @check_state
    def phase_fbenb(self, state: Union[str, int]):
        if not isinstance(state, str) or not isinstance(state, int):
            return
        self.controls_information.PVs.phase_fbenb = state

    @property
    def amp_fbst(self):
        return self.controls_information.PVs.amp_fbst.get()
    
    @amp_fbst.setter
    @check_state
    def amp_fbst(self, state: Union[str, int]):
        if not isinstance(state, str) or not isinstance(state, int):
            return
        self.controls_information.PVs.amp_fbst = state

    @property
    def phase_fbst(self):
        return self.controls_information.PVs.phase_fbst.get()
    
    @phase_fbst.setter
    @check_state
    def phase_fbst(self, state: Union[str, int]):
        if not isinstance(state, str) or not isinstance(state, int):
            return
        self.controls_information.PVs.phase_fbst = state    

    @property
    def mode_config(self):
        return self.controls_information.PVs.mode_config.get()
    
    @mode_config.setter
    def mode_config(self, enum_string):
        #TODO: wrap this in check configs decorator
        pass
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