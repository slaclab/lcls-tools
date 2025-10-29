from pydantic import (
    BaseModel,
    SerializeAsAny,
    field_validator,
    conint,
    ValidationError,
)
from typing import (
    Dict,
    List,
    Optional,
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

    @field_validator("value")
    def scan_range_validator(cls, v):
        if len(v) != 2:
            raise ValueError("List has length greater than 2")
        elif v[0] >= v[1]:
            raise ValueError(
                "First element of list must be smaller than second element of list"
            )
        else:
            return v


class BooleanModel(BaseModel):
    value: bool


class IntegerModel(BaseModel):
    value: conint(strict=True)


class PlaneModel(BaseModel):
    plane: str

    @field_validator("plane")
    def x_y_u_plane(cls, v):
        if v.lower() in ["x", "y", "u"]:
            return v
        else:
            raise ValueError("basePlane must be X, Y, or U")


class WirePVSet(PVSet):
    abort_scan: PV
    beam_rate: Optional[PV] = None
    enabled: Optional[PV] = None
    homed: Optional[PV] = None
    initialize: Optional[PV] = None
    initialize_status: Optional[PV] = None
    motor: PV
    motor_rbv: PV
    retract: Optional[PV] = None
    scan_pulses: PV
    speed: PV
    speed_max: PV
    speed_min: PV
    start_scan: PV
    temperature: Optional[PV] = None
    timeout: Optional[PV] = None
    use_u_wire: PV
    use_x_wire: PV
    use_y_wire: PV
    u_size: PV
    u_wire_inner: PV
    u_wire_outer: PV
    x_size: PV
    x_wire_inner: PV
    x_wire_outer: PV
    y_size: PV
    y_wire_inner: PV
    y_wire_outer: PV

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class WireControlInformation(ControlInformation):
    PVs: SerializeAsAny[WirePVSet]

    def __init__(self, *args, **kwargs):
        super(WireControlInformation, self).__init__(*args, **kwargs)


class WireMetadata(Metadata):
    detectors: List[str]
    bpms_before_wire: Optional[List[str]] = None
    bpms_after_wire: Optional[List[str]] = None


class Wire(Device):
    controls_information: SerializeAsAny[WireControlInformation]
    metadata: SerializeAsAny[WireMetadata]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    """ Decorators """

    def check_state(f):
        """Decorator to only allow transitions in 'Initialized' state"""

        def decorated(self, *args, **kwargs):
            if self.initialize_status is not True:
                print(f"Unable to perform action, {self} not in Initialized state")
                return
            return f(self, *args, **kwargs)

        return decorated

    def check_speed(f):
        """Check that wire speed is sufficient for beam rate and sample size"""

        def decorated(self, *args, **kwargs):
            wire_range = self.wire.x_range[1] - self.wire.x_range[0]
            speed_calc = int(self.wire.beam_rate * (wire_range / self.wire.scan_pulses))
            speed_check = (
                int(self.wire.speed_min) < speed_calc < int(self.wire.speed_max)
            )
            if speed_check is not True:
                print(f"Unable to perform action. {self} failed speed check")
                return
            return f(self, *args, **kwargs)

        return decorated

    def abort_scan(self):
        """Aborts active wire scan"""
        self.controls_information.PVs.abort_scan.put(value=1)

    @property
    def enabled(self):
        """Returns the enabled state of the wire sacnner"""
        return self.controls_information.PVs.enabled.get()

    @property
    def beam_rate(self):
        """Returns current beam rate"""
        # Some wires do not have dedicated beam rate PVs.
        # See CATER 180392 for more details
        nc_areas = ["LI20", "LI24", "LI28", "LTUH", "DL1", "BC1", "BC2", "LTU"]
        if self.area in nc_areas and self.controls_information.PVs.beam_rate is None:
            nc_beam_rate = PV("EVNT:SYS0:1:LCLSBEAMRATE")
            return nc_beam_rate.get()
        elif self.area in ["DIAG0"] and self.controls_information.PVs.beam_rate is None:
            diag0_beam_rate = PV("TPG:SYS0:1:DST01:RATE")
            return diag0_beam_rate.get()
        else:
            return self.controls_information.PVs.beam_rate.get()

    @property
    def homed(self):
        """Checks if the wire is in the home position."""
        return self.controls_information.PVs.homed.get()

    @property
    def initialize_status(self):
        """
        Checks if the wire scanner device has been intialized..
        """
        return self.controls_information.PVs.initialize_status.get()

    def initialize(self) -> None:
        self.controls_information.PVs.initialize.put(value=1)

    @property
    def motor(self):
        """Returns the readback from the MOTR PV"""
        return self.controls_information.PVs.motor.get()

    @motor.setter
    def motor(self, val: int) -> None:
        try:
            IntegerModel(value=val)
            self.controls_information.PVs.motor.put(value=val)
        except ValidationError as e:
            print("Motor input must be an integer:", e)

    @property
    def motor_rbv(self):
        """Returns the .RBV from the MOTR PV"""
        return self.controls_information.PVs.motor_rbv.get()

    def position_buffer(self, buffer):
        return buffer.get_data_buffer(f"{self.controls_information.control_name}:POSN")

    def retract(self):
        """Retracts the wire scanner"""
        self.controls_information.PVs.retract.put(value=1)

    @property
    def scan_pulses(self):
        """Returns the number of scan pulses requested"""
        return self.controls_information.PVs.scan_pulses.get()

    @scan_pulses.setter
    def scan_pulses(self, val: int) -> None:
        try:
            IntegerModel(value=val)
            self.controls_information.PVs.scan_pulses.put(value=val)
        except ValidationError as e:
            print("Scan pulses value must be an integer:", e)

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
    def speed(self):
        """Returns the current calculated speed of the wire scanner."""
        return self.controls_information.PVs.speed.get()

    @property
    def speed_max(self):
        """Returns the wire scanner maximum speed in um/s"""
        return self.controls_information.PVs.speed_max.get()

    @property
    def speed_min(self):
        """Returns the wire scanner minimum speed in um/s"""
        return self.controls_information.PVs.speed_min.get()

    def start_scan(self):
        """Starts a wire scan using current parameters"""
        self.controls_information.PVs.start_scan.put(value=1)

    @property
    def temperature(self):
        """Returns RTD temperature"""
        return self.controls_information.PVs.temperature.get()

    @property
    def timeout(self):
        """Returns enabled status of device timeout"""
        return self.controls_information.PVs.timeout.get()

    @timeout.setter
    def timeout(self, val: bool) -> None:
        try:
            BooleanModel(value=val)
            self.controls_information.PVs.timeout.put(value=val)
        except ValidationError as e:
            print("Input must be 1 or 0:", e)

    @property
    def x_size(self):
        """Returns the x wire thickness in um."""
        return self.controls_information.PVs.x_size.get()

    @property
    def y_size(self):
        """Returns the y wire thickness in um."""
        return self.controls_information.PVs.y_size.get()

    @property
    def u_size(self):
        """Returns the u wire thickness in um."""
        return self.controls_information.PVs.u_size.get()

    def use(self, plane: str, val: bool) -> None:
        try:
            PlaneModel(value=plane)
            BooleanModel(value=val)
        except ValidationError as e:
            print("Plane must be X, Y, or U:", e)
            return
        property_name = "use_" + plane.lower() + "_wire"
        setattr(self, property_name, val)

    @property
    def use_x_wire(self):
        """Checks if the X plane will be scanned."""
        return self.controls_information.PVs.use_x_wire.get()

    @use_x_wire.setter
    def use_x_wire(self, val: bool) -> None:
        try:
            BooleanModel(value=val)
            int_val = int(val)
            self.controls_information.PVs.use_x_wire.put(value=int_val)
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
        return self.controls_information.PVs.x_wire_inner.get()

    @x_wire_inner.setter
    def x_wire_inner(self, val: int) -> None:
        try:
            IntegerModel(value=val)
            self.controls_information.PVs.x_wire_inner.put(value=val)
        except ValidationError as e:
            print("Range value must be an int:", e)

    @property
    def x_wire_outer(self):
        """Returns the outer point of the X plane scan range."""
        return self.controls_information.PVs.x_wire_outer.get()

    @x_wire_outer.setter
    def x_wire_outer(self, val: int) -> None:
        try:
            IntegerModel(value=val)
            self.controls_information.PVs.x_wire_outer.put(value=val)
        except ValidationError as e:
            print("Range value must be an int:", e)

    @property
    def use_y_wire(self):
        """Checks if the Y plane will be scanned."""
        return self.controls_information.PVs.use_y_wire.get()

    @use_y_wire.setter
    def use_y_wire(self, val: bool) -> None:
        try:
            BooleanModel(value=val)
            int_val = int(val)
            self.controls_information.PVs.use_y_wire.put(value=int_val)
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
        return self.controls_information.PVs.y_wire_inner.get()

    @y_wire_inner.setter
    def y_wire_inner(self, val: int) -> None:
        try:
            IntegerModel(value=val)
            self.controls_information.PVs.y_wire_inner.put(value=val)
        except ValidationError as e:
            print("Range value must be an int:", e)

    @property
    def y_wire_outer(self):
        """Returns the outer point of the Y plane scan range."""
        return self.controls_information.PVs.y_wire_outer.get()

    @y_wire_outer.setter
    def y_wire_outer(self, val: int) -> None:
        try:
            IntegerModel(value=val)
            self.controls_information.PVs.y_wire_outer.put(value=val)
        except ValidationError as e:
            print("Range value must be an int:", e)

    @property
    def use_u_wire(self):
        """Checks if the U plane will be scanned."""
        return self.controls_information.PVs.use_u_wire.get()

    @use_u_wire.setter
    def use_u_wire(self, val: bool) -> None:
        try:
            BooleanModel(value=val)
            int_val = int(val)
            self.controls_information.PVs.use_u_wire.put(value=int_val)
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
        return self.controls_information.PVs.u_wire_inner.get()

    @u_wire_inner.setter
    def u_wire_inner(self, val: int) -> None:
        try:
            IntegerModel(value=val)
            self.controls_information.PVs.u_wire_inner.put(value=val)
        except ValidationError as e:
            print("Range value must be an int:", e)

    @property
    def u_wire_outer(self):
        """Returns the outer point of the U plane scan range."""
        return self.controls_information.PVs.u_wire_outer.get()

    @u_wire_outer.setter
    def u_wire_outer(self, val: int) -> None:
        try:
            IntegerModel(value=val)
            self.controls_information.PVs.u_wire_outer.put(value=val)
        except ValidationError as e:
            print("Range value must be an int:", e)

    @property
    def type(self) -> str:
        return self.metadata.type

    @property
    def safe_level(self) -> float:
        return self.metadata.safe_level

    @property
    def read_tolerance(self) -> float:
        return self.metadata.read_tolerance


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
