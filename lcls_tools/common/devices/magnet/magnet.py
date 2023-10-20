#!/usr/local/lcls/package/python/current/bin/python
from epics import PV
from typing import Union
from lcls_tools.common.devices.device import Device


class Magnet(Device):
    _bctrl: PV
    _bact: PV
    _bdes: PV
    _bcon: PV
    _ctrl: PV
    _length: float = None
    _b_tolerance: float = None
    _ctrl_options: dict = None
    _mandatory_pvs: list = [
        "bctrl",
        "bact",
        "bdes",
        "bcon",
        "ctrl",
    ]

    def __init__(self, name=None, **kwargs):
        super().__init__(name=name, config=kwargs)
        self._make_pv_attributes()
        self._set_control_options()
        self._make_metadata_attributes()

    def _set_control_options(self):
        self._ctrl_options = self.control_information["ctrl_options"]

    def _make_pv_attributes(self):
        # setup PVs and private attributes
        for alias in self._mandatory_pvs:
            if alias in self.control_information["PVs"]:
                pv = self.control_information["PVs"][alias]
                setattr(self, "_" + alias, PV(pv))
            else:
                raise AttributeError(f"PV for {alias} not defined in .yaml")

    def _make_metadata_attributes(self):
        # setup metadata and private attributes
        [setattr(self, "_" + k, v) for k, v in self.metadata.items()]

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

    @property
    def length(self) -> float:
        """Magnetic Length, should be from model"""
        return self._length

    @length.setter
    def length(self, length: float) -> None:
        """Set the magnetic length for a magnet"""
        if not isinstance(length, float):
            print("You must provide a float for magnet length")
            return

        self._length = length

    @property
    def b_tolerance(self) -> float:
        return self._b_tolerance

    @b_tolerance.setter
    def b_tolerance(self, tol: float) -> None:
        """Set the magnetic length for a magnet"""
        if not isinstance(tol, float):
            print("You must provide a float for magnet tol")
            return False

        self._b_tolerance = tol

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
