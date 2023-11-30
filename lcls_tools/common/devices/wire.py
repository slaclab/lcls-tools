from datetime import datetime
from functools import wraps
from pydantic import (
    BaseModel,
    PositiveFloat,
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

EPICS_ERROR_MESSAGE = "Not able to connect to the control system."

class WirePVSet(PVSet):
    motr: PV # the rest of the PVs are all related to the motor
    cnen: PV
    velo: PV # velocity
    rbv: PV
    rmp: PV  # retracted motor position?
    xsize: PV
    ysize: PV
    zsize: PV

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @field_validator("*", mode="before")
    def validate_pv_fields(cls, v: str) -> PV:
        return PV(v)


class WireControlInformation(ControlInformation):
    PVs: SerializeAsAny[WirePVSet]
    _ctrl_options: SerializeAsAny[Optional[Dict[str, int]]] = dict()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        #TODO: Get possible options for wire ctrl PV
        options = self.PVs.motr.get_ctrlvars()["enum_strs"]
        [self._ctrl_options.update({option: i}) for i, option in enumerate(options)]

    @property
    def ctrl_options(self):
        return self._ctrl_options


class WireMetadata(Metadata):
    thickness: Optional[PositiveFloat] = None
    speed: Optional[PositiveFloat] = None
    xsize: Optional[PositiveFloat] = None
    ysize: Optional[PositiveFloat] = None
    usize: Optional[PositiveFloat] = None
    #TODO: Add wire material and sum_l here?
    #TODO: Add LBLM and BPM infomration here? 
    #TODO: Add info on locations for X, Y, U wires

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Wire(Device):
    controls_information: SerializeAsAny[WireControlInformation]
    metadata: SerializeAsAny[WireMetadata]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    """ Decorators """

    def check_state(f):
        """Decorator to only allow transitions in 'Ready' state"""

        def decorated(self, *args, **kwargs):
            #TODO: Find out right check for this spot/wires
            if self.motr != "Ready":
                print("Unable to perform action, wire not in Ready state")
                return
            return f(self, *args, **kwargs)

        return decorated

    def check_options(options_to_check: Union[str, List]):
        """Decorator to only allow motor to move if wire is in the retracted position"""
        # Maybe this comment should be updated? Would we move from non retracted position?
        def decorator(function):
            @wraps(function)
            def decorated(self, *args, **kwargs):
                # convert single value to list.
                if isinstance(options_to_check, str):
                    options = [options_to_check]
                for option in options:
                    if option not in self.controls_information.ctrl_options:
                        print(
                            f"unable to perform process {option} with this wire {self.name}"
                        )
                        return
                return function(self, *args, **kwargs)

            return decorated

        return decorator

    @property
    def ctrl_options(self):
        return self.controls_information.ctrl_options

    @property
    def xsize(self):
        """Returns the x wire thickenss in um"""
        #Try to grab from PV first, then if fails, get from yaml
        #Make sure to print statement saying if yaml values used
        try:
            return self.metadata.PVs.xsize.get()
        except:
            print(EPICS_ERROR_MESSAGE)
            #TODO: Returning wire size from yaml file instead
            return 

    @property    
    def ysize(self):
        """Returns the y wire thickness in um"""
        try:
            return self.metadata.PVs.ysize.get()
        except:
            print(EPICS_ERROR_MESSAGE)
            return

    @property
    def usize(self):
        """Returns the u wire thickness in um"""
        try:
            return self.metadata.PVs.usize.get()
        except:
            print(EPICS_ERROR_MESSAGE)
            return

    #TODO: Initialize should happen before wire moves
    #but that doesn't need to be available to users

    #TODO: use this to set x/y/u wires positions?
    #Something like xpos.setter??
    @length.setter
    def length(self, value):
        if not isinstance(value, float):
            return
        self.metadata.length = value

    @property 
    def motr(self) -> Union[float, int]:
        return self.controls_information.PVs.motr.get()

    #TODO: make a motr setter?
    @motr.setter
    @check_state
    def bctrl(self, val: Union[float, int]) -> None:
        """Set bctrl value"""
        if not (isinstance(val, float) or isinstance(val, int)):
            print("you need to provide an int or float")
            return
        self.controls_information.PVs.bctrl.put(value=val)

    @property
    def rbv(self) -> float:
        """Get the position readback of the motor"""
        return self.controls_information.PVs.motr.rbv.get()

    #TODO: double check retracted motor tolerance
    def is_motor_retracted(self, tolerance: Optional[float] = 0.0) -> bool:
        return abs(self.rbv) - abs(self.rmp) < tolerance


    #TODO: find out retraction command
    @check_options("RMP")
    @check_state
    def retract(self) -> None:
        """Issue retract command"""
        self.controls_information.PVs.ctrl.put(self.ctrl_options[""])

    #@check_options("SAVE_BDES")
    #def save_bdes(self) -> None:
    #    """Save BDES"""
    #    self.controls_information.PVs.ctrl.put(self.ctrl_options["SAVE_BDES"])

    #@check_options("RESET")
    #def reset(self) -> None:
    #    """Reset wire"""
    #    self.controls_information.PVs.ctrl.put(self.ctrl_options["RESET"])


class WireCollection(BaseModel):
    wires: Dict[str, SerializeAsAny[Wire]]

    @field_validator("wires", mode="before")
    def validate_wires(cls, v) -> Dict[str, Wire]:
        for name, wire in v.items():
            wire = dict(wire)
            # Set name field for wire
            wire.update({"name": name})
            v.update({name: wire})
        return v
    
    #TODO: can the next two functions get moved out?
    def seconds_since(self, time_to_check: datetime) -> int:
        if not isinstance(time_to_check, datetime):
            raise TypeError("Please provide a datetime object for comparison.")
        return (datetime.now() - time_to_check).seconds

    def _make_wire_names_list_from_args(
        self, args: Union[str, List[str], None]
    ) -> List[str]:
        wire_names = args
        if wire_names:
            if isinstance(wire_names, str):
                wire_names = [args]
        else:
            wire_names = list(self.wires.keys())
        return wire_names

    def _scan_wire(
        self, wire_positions: Dict[str, float], 
        #TODO: scan one wire x/y/u
        return RaiseNotImplementedError

    def scan_xwire(
        self,
        wire_dict: Dict[str, float],
        settle_timeout_in_seconds: int = 5,
    ) -> None:
        if not wire_dict:
            return

        for wire in wire_dict.items():
            try:
                #TODO: Scan only x wire? call _scan_wire()
                pass 
            except KeyError:
                print(
                    "You tried to set a wire that does not exist.",
                    f"{wire} was not set to {bval}.",
                )

    def scan_all_wires(
        self,
        scan_settings: List[Dict[str, float]],
        function: Optional[callable] = None,
    ) -> None:
        return RaiseNotImplementedError
