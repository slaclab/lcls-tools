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


class MagnetPVSet(PVSet):
    bctrl: PV
    bact: PV
    bdes: PV
    bcon: PV
    ctrl: PV

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @field_validator("*", mode="before")
    def validate_pv_fields(cls, v: str):
        return PV(v)


class MagnetControlInformation(ControlInformation):
    PVs: SerializeAsAny[MagnetPVSet]
    ctrl_options: SerializeAsAny[Optional[Dict[str, int]]] = {
        "READY": 0,
        "TRIM": 1,
        "PERTURB": 2,
        "BCON_TO_BDES": 3,
        "SAVE_BDES": 4,
        "LOAD_BDES": 5,
        "UNDO_BDES": 6,
        "DAC_ZERO": 7,
        "CALIB": 8,
        "STDZ": 9,
        "RESET": 10,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class MagnetMetadata(Metadata):
    length: Optional[PositiveFloat] = None
    b_tolerance: Optional[PositiveFloat] = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Magnet(Device):
    controls_information: SerializeAsAny[MagnetControlInformation]
    metadata: SerializeAsAny[MagnetMetadata]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    """ Decorators """

    def check_state(f):
        """Decorator to only allow transitions in 'Ready' state"""

        def decorated(self, *args, **kwargs):
            if self.ctrl != "Ready":
                print("Unable to perform action, magnet not in Ready state")
                return
            return f(self, *args, **kwargs)

        return decorated

    @property
    def ctrl_options(self):
        return self.controls_information.ctrl_options

    @property
    def b_tolerance(self):
        """Returns the field tolerance in kG or kGm"""
        return self.metadata.b_tolerance

    @b_tolerance.setter
    def b_tolerance(self, value):
        if not isinstance(value, float):
            return
        self.metadata.b_tolerance = value

    @property
    def length(self):
        """Returns the effective length in meters"""
        return self.metadata.length

    @length.setter
    def length(self, value):
        if not isinstance(value, float):
            return
        self.metadata.length = value

    @property
    def bctrl(self) -> Union[float, int]:
        return self.controls_information.PVs.bact.get()

    @bctrl.setter
    @check_state
    def bctrl(self, val: Union[float, int]) -> None:
        """Set bctrl value"""
        if not (isinstance(val, float) or isinstance(val, int)):
            print("you need to provide an int or float")
            return
        self.controls_information.PVs.bctrl.put(value=val)

    @property
    def bact(self) -> float:
        """Get the BACT value"""
        return self.controls_information.PVs.bact.get()

    @property
    def bdes(self) -> float:
        """Get BDES value"""
        return self.controls_information.PVs.bdes.get()

    @bdes.setter
    def bdes(self, bval) -> None:
        self.controls_information.PVs.bdes.put(value=bval)

    @property
    def ctrl(self) -> str:
        """Get the current action on magnet"""
        return self.controls_information.PVs.ctrl.get(as_string=True)

    @property
    def bcon(self) -> float:
        """Get the configuration strength of magnet"""
        return self.controls_information.PVs.bcon.get()

    def is_bact_settled(self, b_tolerance: Optional[float] = 0.0) -> bool:
        return abs(self.bdes) - abs(self.bact) < b_tolerance

    @check_state
    def trim(self) -> None:
        """Issue trim command"""
        self.controls_information.PVs.ctrl.put(self.ctrl_options["TRIM"])

    @check_state
    def perturb(self) -> None:
        """Issue perturb command"""
        self.controls_information.PVs.ctrl.put(self.ctrl_options["PERTURB"])

    def con_to_des(self) -> None:
        """Issue con to des commands"""
        self.controls_information.PVs.ctrl.put(self.ctrl_options["BCON_TO_BDES"])

    def save_bdes(self) -> None:
        """Save BDES"""
        self.controls_information.PVs.ctrl.put(self.ctrl_options["SAVE_BDES"])

    def load_bdes(self) -> None:
        """Load BtolDES"""
        self.controls_information.PVs.ctrl.put(self.ctrl_options["LOAD_BDES"])

    def undo_bdes(self) -> None:
        """Save BDES"""
        self.controls_information.PVs.ctrl.put(self.ctrl_options["UNDO_BDES"])

    @check_state
    def dac_zero(self) -> None:
        """DAC zero magnet"""
        self.controls_information.PVs.ctrl.put(self.ctrl_options["DAC_ZERO"])

    @check_state
    def calibrate(self) -> None:
        """Calibrate magnet"""
        self.controls_information.PVs.ctrl.put(self.ctrl_options["CALIB"])

    @check_state
    def standardize(self) -> None:
        """Standardize magnet"""
        self.controls_information.PVs.ctrl.put(self.ctrl_options["STDZ"])

    def reset(self) -> None:
        """Reset magnet"""
        self.controls_information.PVs.ctrl.put(self.ctrl_options["RESET"])


class MagnetCollection(BaseModel):
    magnets: Dict[str, SerializeAsAny[Magnet]]

    @field_validator("magnets", mode="before")
    def validate_magnets(cls, v):
        for name, magnet in v.items():
            magnet = dict(magnet)
            magnet.update({"name": name})
            v.update({name: magnet})
        return v

    def set_bdes(self, magnet_dict: Dict[str, float]):
        if not magnet_dict:
            return

        for magnet, bval in magnet_dict.items():
            try:
                self.magnets[magnet].bdes = bval
                self.magnets[magnet].trim()
                while not self.magnets[magnet].is_bact_settled():
                    continue
            except KeyError:
                print(
                    "You tried to set a magnet that does not exist.",
                    f"{magnet} was not set to {bval}.",
                )

    def scan(
        self, scan_settings: List[Dict[str, float]], function: Optional[callable] = None
    ):
        for setting in scan_settings:
            self.set_bdes(setting)
            function() if function else None
