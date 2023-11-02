from pydantic import (
    BaseModel,
    PositiveFloat,
    SerializeAsAny,
    ConfigDict,
    PrivateAttr,
)
from typing import Dict, Optional, Union
from lcls_tools.common.devices.model import (
    Device,
    ControlInformation,
    Metadata,
    PVSet,
)
from epics import PV


class MagnetPVSet(PVSet):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="forbid",
    )
    bctrl: str
    bact: str
    bdes: str
    bcon: str
    ctrl: str
    _bctrl: PrivateAttr(PV)
    _bact: PrivateAttr(PV)
    _bdes: PrivateAttr(PV)
    _bcon: PrivateAttr(PV)
    _ctrl: PrivateAttr(PV)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._bctrl = PV(self.bctrl)
        self._bact = PV(self.bact)
        self._bdes = PV(self.bdes)
        self._bcon = PV(self.bcon)
        self._ctrl = PV(self.ctrl)

    # @field_validator("*", mode="before")
    # def validate_pv_fields(cls, v: str):
    #     return PV(v)


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


class MagnetMetadata(Metadata):
    length: Optional[PositiveFloat] = None
    b_tolerance: Optional[PositiveFloat] = None


class Magnet(Device):
    controls_information: SerializeAsAny[MagnetControlInformation]
    metadata: SerializeAsAny[MagnetMetadata]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def ctrl_options(self):
        return self.controls_information.ctrl_options

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
    def b_tolerance(self):
        return self.metadata.b_tolerance

    @b_tolerance.setter
    def b_tolerance(self, value):
        if not isinstance(value, float):
            return
        self.metadata.b_tolerance = value

    @property
    def length(self):
        return self.metadata.length

    @length.setter
    def length(self, value):
        if not isinstance(value, float):
            return
        self.metadata.length = value

    @property
    def bctrl(self) -> Union[float, int]:
        return self.controls_information.PVs._bact.get()

    @bctrl.setter
    @check_state
    def bctrl(self, val: Union[float, int]) -> None:
        """Set bctrl value"""
        if not (isinstance(val, float) or isinstance(val, int)):
            print("you need to provide an int or float")
            return
        self.controls_information.PVs._bctrl.put(val)

    @property
    def bact(self) -> float:
        """Get the BACT value"""
        return self.controls_information.PVs._bact.get()

    @property
    def bdes(self) -> float:
        """Get BDES value"""
        return self.controls_information.PVs._bdes.get()

    @property
    def ctrl(self) -> str:
        """Get the current action on magnet"""
        return self.controls_information.PVs._ctrl.get(as_string=True)

    @property
    def bcon(self) -> float:
        """Get the configuration strength of magnet"""
        return self.controls_information.PVs._bcon.get()

    @check_state
    def trim(self) -> None:
        """Issue trim command"""
        self.controls_information.PVs._ctrl.put(self.ctrl_options["TRIM"])

    @check_state
    def perturb(self) -> None:
        """Issue perturb command"""
        self.controls_information.PVs._ctrl.put(self.ctrl_options["PERTURB"])

    def con_to_des(self) -> None:
        """Issue con to des commands"""
        self.controls_information.PVs._ctrl.put(self.ctrl_options["BCON_TO_BDES"])

    def save_bdes(self) -> None:
        """Save BDES"""
        self.controls_information.PVs._ctrl.put(self.ctrl_options["SAVE_BDES"])

    def load_bdes(self) -> None:
        """Load BtolDES"""
        self.controls_information.PVs._ctrl.put(self.ctrl_options["LOAD_BDES"])

    def undo_bdes(self) -> None:
        """Save BDES"""
        self.controls_information.PVs._ctrl.put(self.ctrl_options["UNDO_BDES"])

    @check_state
    def dac_zero(self) -> None:
        """DAC zero magnet"""
        self.controls_information.PVs._ctrl.put(self.ctrl_options["DAC_ZERO"])

    @check_state
    def calibrate(self) -> None:
        """Calibrate magnet"""
        self.controls_information.PVs._ctrl.put(self.ctrl_options["CALIB"])

    @check_state
    def standardize(self) -> None:
        """Standardize magnet"""
        self.controls_information.PVs._ctrl.put(self.ctrl_options["STDZ"])

    def reset(self) -> None:
        """Reset magnet"""
        self.controls_information.PVs._ctrl.put(self.ctrl_options["RESET"])


class MagnetCollection(BaseModel):
    magnets: Dict[str, SerializeAsAny[Magnet]]
