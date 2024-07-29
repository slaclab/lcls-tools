from datetime import datetime
from functools import wraps

from pydantic import (
    BaseModel,
    PositiveFloat,
    SerializeAsAny,
    field_validator,
    conint,
    ValidationError,
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


class BooleanModel(BaseModel):
    value: bool


class IntegerModel(BaseModel):
    value: conint(strict=True)


class WirePVSet(PVSet):
    motr: PV  # the rest of the PVs are all related to the motor
    cnen: PV
    velo: PV  # velocity
    rbv: PV
    rmp: PV  # retracted motor position?
    initialize: PV
    initialized: PV
    retract: PV
    startscan: PV
    xsize: PV
    ysize: PV
    usize: PV
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

    def __init__(self, *args, **kwargs):
        super(WireControlInformation, self).__init__(*args, **kwargs)
        # Get possible options for magnet ctrl PV, empty dict by default.
        options = self.PVs.ctrl.get_ctrlvars(timeout=1)
        if options:
            [
                self._ctrl_options.update({option: i})
                for i, option in enumerate(options["enum_strs"])
            ]

    @property
    def ctrl_options(self):
        return self._ctrl_options


class WireMetadata(Metadata):
    thickness: Optional[PositiveFloat] = None
    speed: Optional[PositiveFloat] = None
    xsize: Optional[PositiveFloat] = None
    ysize: Optional[PositiveFloat] = None
    usize: Optional[PositiveFloat] = None
    # TODO: Add wire material and sum_l here?
    # TODO: Add LBLM and BPM infomration here?
    # TODO: Add info on locations for X, Y, U wires

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Wire(Device):
    controls_information: SerializeAsAny[WireControlInformation]
    metadata: SerializeAsAny[WireMetadata]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    """ Decorators """

    def check_state(f):
        """Decorator to only allow transitions in 'Ready' state."""

        def decorated(self, *args, **kwargs):
            # TODO: Find out right check for this spot/wires
            if self.motr != "Ready":
                print("Unable to perform action, wire not in Ready state")
                return
            return f(self, *args, **kwargs)

        return decorated

    def check_options(options_to_check: Union[str, List]):
        """Decorator to only allow motor to move if wire is in the retracted position."""
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
    def xsize(self):
        """Returns the x wire thickness in um."""
        # Try to grab from PV first, then if fails, get from yaml
        # Make sure to print statement saying if yaml values used
        try:
            return self.metadata.PVs.xsize.get()
        except Exception:
            print(EPICS_ERROR_MESSAGE)
            # TODO: Returning wire size from yaml file instead
            return

    @property
    def ysize(self):
        """Returns the y wire thickness in um."""
        try:
            return self.metadata.PVs.ysize.get()
        except Exception:
            print(EPICS_ERROR_MESSAGE)
            # TODO: Returning wire size from yaml file instead

    @property
    def usize(self):
        """Returns the u wire thickness in um."""
        try:
            return self.metadata.PVs.usize.get()
        except Exception:
            print(EPICS_ERROR_MESSAGE)
            # TODO: Returning wire size from yaml file instead

    @property
    def use_x_wire(self):
        """Checks if the X plane will be scanned."""
        return self.controls_information.PVs.usexwire.get()

    @use_x_wire.setter
    def use_x_wire(self, val: bool) -> None:
        try:
            BooleanModel(value=val)
            int_val = int(val)
            self.controls_information.PVs.usexwire.put(value=int_val)
        except ValidationError as e:
            print("Value must be a bool:", e)

    @property
    def x_range(self):
        """
        Returns the X plane scan range.
        Sets both inner and outer points.
        """
        x_inner = self.x_wire_inner
        x_outer = self.x_wire_outer
        x_range = [x_inner, x_outer]
        return x_range

    @x_range.setter
    def x_range(self, val: list) -> None:
        self.x_wire_inner(val[0])
        self.x_wire_outer(val[1])

    @property
    def x_wire_inner(self):
        """Returns the inner point of the X plane scan range."""
        return self.controls_information.PVs.xwireinner.get()

    @x_wire_inner.setter
    def x_wire_inner(self, val: int) -> None:
        try:
            IntegerModel(value=val)
            self.controls_information.PVs.xwireinner.put(value=val)
        except ValidationError as e:
            print("Value must be an int:", e)

    @property
    def x_wire_outer(self):
        """Returns the outer point of the X plane scan range."""
        return self.controls_information.PVs.xwireouter.get()

    @x_wire_outer.setter
    def x_wire_outer(self, val: int) -> None:
        try:
            IntegerModel(value=val)
            self.controls_information.PVs.xwireouter.put(value=val)
        except ValidationError as e:
            print("Value must be an int:", e)

    @property
    def use_y_wire(self):
        """Checks if the Y plane will be scanned."""
        return self.metadata.PVs.useywire.get()

    @use_y_wire.setter
    def use_y_wire(self, val: bool) -> None:
        try:
            BooleanModel(value=val)
            int_val = int(val)
            self.controls_information.PVs.useywire.put(value=int_val)
        except ValidationError as e:
            print("Value must be a bool:", e)

    @property
    def y_range(self):
        """
        Returns the Y plane scan range.
        Sets both inner and outer points.
        """
        y_inner = self.y_wire_inner
        y_outer = self.y_wire_outer
        y_range = [y_inner, y_outer]
        return y_range

    @y_range.setter
    def y_range(self, val: list) -> None:
        self.y_wire_inner(val[0])
        self.y_wire_outer(val[1])

    @property
    def y_wire_inner(self):
        """Returns the inner point of the Y plane scan range."""
        return self.controls_information.PVs.ywireinner.get()

    @y_wire_inner.setter
    def y_wire_inner(self, val: int) -> None:
        try:
            IntegerModel(value=val)
            self.controls_information.PVs.ywireinner.put(value=val)
        except ValidationError as e:
            print("Value must be an int:", e)

    @property
    def y_wire_outer(self):
        """Returns the outer point of the Y plane scan range."""
        return self.controls_information.PVs.ywireouter.get()

    @y_wire_outer.setter
    def y_wire_outer(self, val: int) -> None:
        try:
            IntegerModel(value=val)
            self.controls_information.PVs.ywireouter.put(value=val)
        except ValidationError as e:
            print("Value must be an int:", e)

    @property
    def use_u_wire(self):
        """Checks if the U plane will be scanned."""
        return self.metadata.PVs.useuwire.get()

    @use_u_wire.setter
    def use_u_wire(self, val: bool) -> None:
        try:
            BooleanModel(value=val)
            int_val = int(val)
            self.controls_information.PVs.useuwire.put(value=int_val)
        except ValidationError as e:
            print("Value must be a bool:", e)

    @property
    def u_range(self):
        """
        Returns the U plane scan range.
        Sets both inner and outer points.
        """
        u_inner = self.u_wire_inner
        u_outer = self.u_wire_outer
        u_range = [u_inner, u_outer]
        return u_range

    @u_range.setter
    def u_range(self, val: list) -> None:
        self.u_wire_inner(val[0])
        self.u_wire_outer(val[1])

    @property
    def u_wire_inner(self):
        """Returns the inner point of the U plane scan range."""
        return self.controls_information.PVs.uwireinner.get()

    @u_wire_inner.setter
    def u_wire_inner(self, val: int) -> None:
        try:
            IntegerModel(value=val)
            self.controls_information.PVs.uwireinner.put(value=val)
        except ValidationError as e:
            print("Value must be an int:", e)

    @property
    def u_wire_outer(self):
        """Returns the outer point of the U plane scan range."""
        return self.controls_information.PVs.uwireouter.get()

    @u_wire_outer.setter
    def u_wire_outer(self, val: int) -> None:
        try:
            IntegerModel(value=val)
            self.controls_information.PVs.uwireouter.put(value=val)
        except ValidationError as e:
            print("Value must be an int:", e)

    @property
    def initialized(self):
        """
        Checks if the wire scanner device has been intialized..
        """
        return self.controls_information.PVs.initialized.get()

    def initalize(self) -> None:
        self.controls_information.PVs.initialize.put(value=1)

    @property
    def homed(self):
        """Checks if the wire is in the home position."""
        return self.controls_information.PVs.homed.get()

    @property
    def position(self):
        """Returns the readback value from the MOTR PV."""
        return self.controls_information.PVs.rbv.get()

    @position.setter
    def position(self, val: int) -> None:
        self.controls_information.PVs.motr.put(value=val)

    @property
    def speed(self):
        """Returns the current calculated speed of the wire scanner."""
        return self.controls_information.PVs.velo.get()

    def retract(self):
        """Retracts the wire scanner"""
        self.controls_information.PVs.retract.put(value=1)


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

    # TODO: can the next two functions get moved out?
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
