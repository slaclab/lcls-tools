from datetime import datetime
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


class RangeModel(BaseModel):
    value: list

    @field_validator('value')
    def scan_range_validator(cls, v):
        if len(v) != 2:
            raise ValueError("List has length greater than 2")
        elif v[0] >= v[1]:
            raise ValueError("First element of list must be smaller than second element of list")
        else:
            return v


class BooleanModel(BaseModel):
    value: bool


class IntegerModel(BaseModel):
    value: conint(strict=True)


class PlaneModel(BaseModel):
    plane: str

    @field_validator('plane')
    def x_y_u_plane(cls, v):
        if v.lower() in ['x', 'y', 'u']:
            return v
        else:
            raise ValueError("basePlane must be X, Y, or U")


class WirePVSet(PVSet):
    motr: PV
    velo: PV
    rbv: PV
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
    abort: PV

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
        # Get possible options for wire motr PV, empty dict by default.
        options = self.PVs.motr.get_ctrlvars(timeout=1)
        if "enum_strs" in options:
            [
                self._ctrl_options.update({option: i})
                for i, option in enumerate(options["enum_strs"])
            ]

    @property
    def ctrl_options(self):
        return self._ctrl_options


class WireMetadata(Metadata):
    material: Optional[str] = None
    sum_l: Optional[PositiveFloat] = None
    # TODO: Add LBLM and BPM infomration here?
    # TODO: Add info on locations for X, Y, U wires

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Wire(Device):
    controls_information: SerializeAsAny[WireControlInformation]
    metadata: SerializeAsAny[WireMetadata]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

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

    def use(self, plane: str, val: bool) -> None:
        try:
            PlaneModel(value=plane)
            BooleanModel(value=val)
        except ValidationError as e:
            print("Plane must be X, Y, or U:", e)
            return
        property_name = "use_" + plane.lower() + "_wire"
        setattr(self, property_name, val)

    def set_range(self, plane: str, val: list) -> None:
        try:
            PlaneModel(value=plane)
            RangeModel(value=val)
            property_name = plane.lower() + "_range"
            setattr(self, property_name, val)
        except ValidationError as e:
            print("Plane must be X, Y, or U:", e)

    def set_inner_range(self, plane: str, val: int) -> None:
        try:
            PlaneModel(value=plane)
            IntegerModel(value=val)
            property_name = plane.lower() + "_wire_inner"
            outer_property = plane.lower() + "_wire_outer"
            outer_range = getattr(self, outer_property)
            if val < outer_range:
                setattr(self, property_name, val)
            else:
                print("Scan range value failed validation")
                raise ValidationError
        except ValidationError as e:
            print("Plane must be X, Y, or U:", e)

    def set_outer_range(self, plane: str, val: int) -> None:
        try:
            PlaneModel(value=plane)
            IntegerModel(value=val)
            property_name = plane.lower() + "_wire_outer"
            inner_property = plane.lower() + "_wire_inner"
            inner_range = getattr(self, inner_property)
            if val > inner_range:
                setattr(self, property_name, val)
            else:
                print("Scan range value failed validation")
                raise ValidationError
        except ValidationError as e:
            print("Plane must be X, Y, or U:", e)

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
            print("Input value must be a bool:", e)

    @property
    def x_range(self):
        """
        Returns the X plane scan range.
        Sets both inner and outer points.
        """
        return [self.x_wire_inner, self.x_wire_outer]

    @x_range.setter
    def x_range(self, val: list) -> None:
        try:
            RangeModel(value=val)
            self.x_wire_inner(val[0])
            self.x_wire_outer(val[1])
        except ValidationError as e:
            print("Scan range values failed validation:", e)

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
            print("Range value must be an int:", e)

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
            print("Range value must be an int:", e)

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
            print("Input value must be a bool:", e)

    @property
    def y_range(self):
        """
        Returns the Y plane scan range.
        Sets both inner and outer points.
        """
        return [self.y_wire_inner, self.y_wire_outer]

    @y_range.setter
    def y_range(self, val: list) -> None:
        try:
            RangeModel(value=val)
            self.y_wire_inner(val[0])
            self.y_wire_outer(val[1])
        except ValidationError as e:
            print("Scan range values failed validation:", e)

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
            print("Range value must be an int:", e)

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
            print("Range value must be an int:", e)

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
            print("Input value must be a bool:", e)

    @property
    def u_range(self):
        """
        Returns the U plane scan range.
        Sets both inner and outer points.
        """
        return [self.u_wire_inner, self.u_wire_outer]

    @u_range.setter
    def u_range(self, val: list) -> None:
        try:
            RangeModel(value=val)
            self.u_wire_inner(val[0])
            self.u_wire_outer(val[1])
        except ValidationError as e:
            print("Scan range values failed validation:", e)

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
            print("Range value must be an int:", e)

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
            print("Range value must be an int:", e)

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

    def start_scan(self):
        """Starts a wire scan using current parameters"""
        self.controls_information.PVs.startscan.put(value=1)

    def abort_scan(self):
        """Aborts active wire scan"""
        self.controls_information.PVs.abort.put(value=1)


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
