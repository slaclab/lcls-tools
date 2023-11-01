from pydantic import BaseModel, PositiveFloat, field_validator, SerializeAsAny
from typing import Dict, List, Optional, Union
from epics import PV


class MagnetPVSet(BaseModel):
    bctrl: str
    bact: str
    bdes: str
    bcon: str
    ctrl: str

    @field_validator("*", mode="before")
    def validate_pv_fields(cls, v: str):
        if v:
            return v


class ControlInformation(BaseModel):
    control_name: str
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


class Metadata(BaseModel):
    area: str
    beam_path: List[str]
    sum_l_meters: float
    length: Optional[PositiveFloat] = None
    b_tolerance: Optional[PositiveFloat] = None


class Magnet(BaseModel):
    controls_information: SerializeAsAny[ControlInformation]
    metadata: SerializeAsAny[Metadata]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._make_pv_attributes()

    @property
    def ctrl_options(self):
        return self.controls_information.ctrl_options

    def _make_pv_attributes(self):
        # setup PVs and private attributes
        [
            setattr(self, "_" + handle, PV(pv))
            for handle, pv in self.controls_information.PVs
        ]

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

    @property
    def length(self):
        return self.metadata.length

    @property
    def bctrl(self) -> Union[float, int]:
        return self._bctrl.get()

    @bctrl.setter
    @check_state
    def bctrl(self, val: Union[float, int]) -> None:
        """Set bctrl value"""
        if not (isinstance(val, float) or isinstance(val, int)):
            print("you need to provide an int or float")
            return
        self._bctrl.put(val)

    @property
    def bact(self) -> float:
        """Get the BACT value"""
        return self._bact.get()

    @property
    def bdes(self) -> float:
        """Get BDES value"""
        return self._bdes.get()

    @property
    def ctrl(self) -> str:
        """Get the current action on magnet"""
        return self._ctrl.get(as_string=True)

    @check_state
    def trim(self) -> None:
        """Issue trim command"""
        self._ctrl.put(self._ctrl_options["TRIM"])

    @check_state
    def perturb(self) -> None:
        """Issue perturb command"""
        self._ctrl.put(self._ctrl_options["PERTURB"])

    def con_to_des(self) -> None:
        """Issue con to des commands"""
        self._ctrl.put(self._ctrl_options["BCON_TO_BDES"])

    def save_bdes(self) -> None:
        """Save BDES"""
        self._ctrl.put(self._ctrl_options["SAVE_BDES"])

    def load_bdes(self) -> None:
        """Load BtolDES"""
        self._ctrl.put(self._ctrl_options["LOAD_BDES"])

    def undo_bdes(self) -> None:
        """Save BDES"""
        self._ctrl.put(self._ctrl_options["UNDO_BDES"])

    @check_state
    def dac_zero(self) -> None:
        """DAC zero magnet"""
        self._ctrl.put(self._ctrl_options["DAC_ZERO"])

    @check_state
    def calibrate(self) -> None:
        """Calibrate magnet"""
        self._ctrl.put(self._ctrl_options["CALIB"])

    @check_state
    def standardize(self) -> None:
        """Standardize magnet"""
        self._ctrl.put(self._ctrl_options["STDZ"])

    def reset(self) -> None:
        """Reset magnet"""
        self._ctrl.put(self._ctrl_options["RESET"])


class MagnetCollection(BaseModel):
    magnets: Dict[str, SerializeAsAny[Magnet]]
