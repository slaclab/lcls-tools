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
    init: PV
    retract: PV
    startscan: PV
    usexwire: PV
    useywire: PV
    useuwire: PV
    xwireinner: PV
    xwireouter: PV
    ywireinner: PV
    ywireouter: PV
    uwireinner: PV
    uwireouter: PV
    enabled: PV
    homed: PV
    timeout: PV

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
    def use_x_wire(self):
        return self.controls_information.PVs.usexwire.get()
    @use_x_wire.setter
    def use_x_wire(self, val: int) -> None:
        if not (val == 1 or val == 0):
            print("Value must be 0 or 1")
            return
        self.controls_information.PVs.usexwire.put(value = val)

    @property
    def x_wire_inner(self):
        return self.controls_information.PVs.xwireinner.get()
    @x_wire_inner.setter
    def x_wire_inner(self, val: int) -> None:
        if not isinstance(val, int):
            print("Value must be an int")
            return
        self.controls_information.PVs.xwireinner.put(value = val)

    @property
    def x_wire_outer(self):
        return self.controls_information.PVs.xwireouter.get()
    @x_wire_outer.setter
    def x_wire_outer(self, val: int) -> None:
        if not isinstance(val, int):
            print("Value must be an int")
            return
        self.controls_information.PVs.xwireouter.put(value = val)

    @property
    def use_y_wire(self):
        return self.metadata.PVs.useywire.get()
    @use_y_wire.setter
    def use_y_wire(self, val: int) -> None:
        if not (val == 1 or val == 0):
            print("Value must be 0 or 1")
            return
        self.controls_information.PVs.useywire.put(value = val)

    @property
    def y_wire_inner(self):
        return self.controls_information.PVs.ywireinner.get()
    @y_wire_inner.setter
    def y_wire_inner(self, val: int) -> None:
        if not isinstance(val, int):
            print("Value must be an int")
            return
        self.controls_information.PVs.ywireinner.put(value = val)

    @property
    def y_wire_outer(self):
        return self.controls_information.PVs.ywireouter.get()
    @x_wire_outer.setter
    def y_wire_outer(self, val: int) -> None:
        if not isinstance(val, int):
            print("Value must be an int")
            return
        self.controls_information.PVs.ywireouter.put(value = val)

    @property
    def use_u_wire(self):
        return self.metadata.PVs.useuwire.get()
    @use_u_wire.setter
    def use_u_wire(self, val: int) -> None:
        if not (val == 1 or val == 0):
            print("Value must be 0 or 1")
            return
        self.controls_information.PVs.useuwire.put(value = val)

    @property
    def u_wire_inner(self):
        return self.controls_information.PVs.uwireinner.get()
    @u_wire_inner.setter
    def u_wire_inner(self, val: int) -> None:
        if not isinstance(val, int):
            print("Value must be an int")
            return
        self.controls_information.PVs.uwireinner.put(value = val)

    @property
    def u_wire_outer(self):
        return self.controls_information.PVs.uwireouter.get()
    @u_wire_outer.setter
    def u_wire_outer(self, val: int) -> None:
        if not isinstance(val, int):
            print("Value must be an int")
            return
        self.controls_information.PVs.uwireouter.put(value = val)

    @property
    def initialized(self):
        return self.controls_information.PVs.enabled.get()
    @initialized.setter
    def initalized(self, val) -> None:
        if not val == 1:
            print("Value must be 1")
            return
        self.controls_information.PVs.initialize.put(value = val)

    @property
    def homed(self):
        return self.controls_information.PVs.homed.get()

    @property
    def position(self):
        return self.controls_information.PVs.rbv.get()
    @position.setter
    def position(self, val: int) -> None:
        if not isinstance(val, int):
            print("Value must be an int")
            return
        self.controls_information.PVs.motr.put(value = val)

    @property
    def speed(self):
        return self.controls_information.PVs.velo.get()

    @property
    def retract(self):
        return self.controls_information.PVs.retract.get()
    @retract.setter
    def retract(self, val: int) -> None:
        if not val == 1:
            print("Value must be 1")
            return
        self.controls_information.PVs.retract.put(value = val)

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
