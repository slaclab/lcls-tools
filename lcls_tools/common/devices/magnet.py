from datetime import datetime
from functools import wraps
from pydantic import (
    Field,
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
    DeviceCollection,
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
    bmin: PV
    bmax: PV

    def __init__(self, *args, **kwargs):
        super(MagnetPVSet, self).__init__(*args, **kwargs)

    @field_validator("*", mode="before")
    def validate_pv_fields(cls, v: str) -> PV:
        return PV(v)


class MagnetControlInformation(ControlInformation):
    PVs: SerializeAsAny[MagnetPVSet]
    _ctrl_options: SerializeAsAny[Optional[Dict[str, int]]] = dict()

    def __init__(self, *args, **kwargs):
        super(MagnetControlInformation, self).__init__(*args, **kwargs)
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


class MagnetMetadata(Metadata):
    length: Optional[PositiveFloat] = None
    b_tolerance: Optional[PositiveFloat] = None

    def __init__(self, *args, **kwargs):
        super(MagnetMetadata, self).__init__(*args, **kwargs)


class Magnet(Device):
    controls_information: SerializeAsAny[MagnetControlInformation]
    metadata: SerializeAsAny[MagnetMetadata]

    def __init__(self, *args, **kwargs):
        super(Magnet, self).__init__(*args, **kwargs)

    """ Decorators """

    def check_state(f):
        """Decorator to only allow transitions in 'Ready' state"""

        def decorated(self, *args, **kwargs):
            if self.ctrl != "Ready":
                print("Unable to perform action, magnet not in Ready state")
                return
            return f(self, *args, **kwargs)

        return decorated

    def check_options(options_to_check: Union[str, List]):
        """Decorator to only allow :CTRL to be set if that option exists for the magnet"""

        def decorator(function):
            @wraps(function)
            def decorated(self, *args, **kwargs):
                # convert single value to list.
                if isinstance(options_to_check, str):
                    options = [options_to_check]
                for option in options:
                    if option not in self.controls_information.ctrl_options:
                        print(
                            f"unable to perform process {option} with this magnet {self.name}"
                        )
                        return
                return function(self, *args, **kwargs)

            return decorated

        return decorator

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
        return self.controls_information.PVs.bctrl.get()

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

    @property
    def bmax(self) -> float:
        """Get maximum magnetic field value in KG or KG-m^x."""
        return self.controls_information.PVs.bmax.get()

    @property
    def bmin(self) -> float:
        """Get minimum magnetic field value in kG or kG-m^x."""
        return self.controls_information.PVs.bmin.get()

    def is_bact_settled(self, b_tolerance: Optional[float] = 0.0) -> bool:
        return abs(self.bdes) - abs(self.bact) < b_tolerance

    @check_options("TRIM")
    @check_state
    def trim(self) -> None:
        """Issue trim command"""
        self.controls_information.PVs.ctrl.put(self.ctrl_options["TRIM"])

    @check_options("PERTURB")
    @check_state
    def perturb(self) -> None:
        """Issue perturb command"""
        self.controls_information.PVs.ctrl.put(self.ctrl_options["PERTURB"])

    @check_options("BCON_TO_BDES")
    def con_to_des(self) -> None:
        """Issue con to des commands"""
        self.controls_information.PVs.ctrl.put(self.ctrl_options["BCON_TO_BDES"])

    @check_options("SAVE_BDES")
    def save_bdes(self) -> None:
        """Save BDES"""
        self.controls_information.PVs.ctrl.put(self.ctrl_options["SAVE_BDES"])

    @check_options("LOAD_BDES")
    def load_bdes(self) -> None:
        """Load BDES"""
        self.controls_information.PVs.ctrl.put(self.ctrl_options["LOAD_BDES"])

    @check_options("UNDO_BDES")
    def undo_bdes(self) -> None:
        """Undo BDES"""
        self.controls_information.PVs.ctrl.put(self.ctrl_options["UNDO_BDES"])

    @check_options("DAC_ZERO")
    @check_state
    def dac_zero(self) -> None:
        """DAC zero magnet"""
        self.controls_information.PVs.ctrl.put(self.ctrl_options["DAC_ZERO"])

    @check_options("CALIB")
    @check_state
    def calibrate(self) -> None:
        """Calibrate magnet"""
        self.controls_information.PVs.ctrl.put(self.ctrl_options["CALIB"])

    @check_options("STDZ")
    @check_state
    def standardize(self) -> None:
        """Standardize magnet, when Degaussing is not available due to power supply."""
        self.controls_information.PVs.ctrl.put(self.ctrl_options["STDZ"])

    @check_options("RESET")
    def reset(self) -> None:
        """Reset magnet"""
        self.controls_information.PVs.ctrl.put(self.ctrl_options["RESET"])

    @check_options("TURN_OFF")
    def turn_off(self) -> None:
        """Turn off magnet"""
        self.controls_information.PVs.ctrl.put(self.ctrl_options["TURN_OFF"])

    @check_options("TURN_ON")
    def turn_on(self) -> None:
        """Turn on magnet"""
        self.controls_information.PVs.ctrl.put(self.ctrl_options["TURN_ON"])

    @check_options("DEGAUSS")
    def degauss(self):
        """Degauss magnet"""
        self.controls_information.PVs.ctrl.put(self.ctrl_options["DEGAUSS"])


class MagnetCollection(DeviceCollection):
    devices: Dict[str, SerializeAsAny[Magnet]] = Field(alias="magnets")

    def __init__(self, *args, **kwargs):
        super(MagnetCollection, self).__init__(*args, **kwargs)

    @property
    def magnets(self) -> Dict[str, SerializeAsAny[Magnet]]:
        """A dictionary (key=name, value=Magnet) to directly access magnet objects"""
        return self.devices

    def _seconds_since(self, time_to_check: datetime) -> int:
        if not isinstance(time_to_check, datetime):
            raise TypeError("Please provide a datetime object for comparison.")
        return (datetime.now() - time_to_check).seconds

    def _make_magnet_names_list_from_args(
        self, args: Union[str, List[str], None]
    ) -> List[str]:
        magnet_names = args
        if magnet_names:
            if isinstance(magnet_names, str):
                magnet_names = [args]
        else:
            magnet_names = list(self.devices.keys())
        return magnet_names

    def set_bdes(
        self,
        magnet_dict: Dict[str, float],
        settle_timeout_in_seconds: int = 5,
    ) -> None:
        """
        Set BDES and TRIMs for a set of magnets in the collection by providing settings in the following
        form:

        {'MAGB' : 1.0, 'MAGC' : 2.0, ..., 'MAGZ' : 3.0}

        Automatically waits until each magnet is settled within a wait-time (default = 5 seconds)
        """

        if not magnet_dict:
            return

        for magnet, bval in magnet_dict.items():
            try:
                self.devices[magnet].bdes = bval
                self.devices[magnet].trim()
                time_when_trim_started = datetime.now()
                while not self.devices[magnet].is_bact_settled():
                    if (
                        self._seconds_since(time_when_trim_started)
                        > settle_timeout_in_seconds
                    ):
                        print(
                            "Took more than ",
                            settle_timeout_in_seconds,
                            " seconds for ",
                            magnet,
                            ":BACT to reach ",
                            magnet,
                            ":BDES.",
                        )
                        break
            except KeyError:
                print(
                    "You tried to set a magnet that does not exist.",
                    f"{magnet} was not set to {bval}.",
                )

    def scan(
        self,
        scan_settings: List[Dict[str, float]],
        function: Optional[callable] = None,
    ) -> None:
        """
        Scans magnets given a list of magnet settings (Dict[magnet_name, bdes_value])
        and calls the provided function after each setting is achieved.
        """
        for setting in scan_settings:
            self.set_bdes(setting)
            function() if function else None

    def turn_off(
        self,
        magnets: Optional[Union[str, List]] = None,
    ) -> None:
        """Turns off the magnets provided"""
        magnets_to_turn_off = self._make_magnet_names_list_from_args(magnets)
        for magnet in magnets_to_turn_off:
            try:
                self.devices[magnet].turn_off()
            except KeyError:
                print(
                    "Could not find ",
                    magnet,
                    " in magnet collection, unable to turn off.",
                )

    def turn_on(
        self,
        magnets: Optional[Union[str, List]] = None,
    ) -> None:
        """Turns on the magnets provided"""
        magnets_to_turn_on = self._make_magnet_names_list_from_args(magnets)
        for magnet in magnets_to_turn_on:
            try:
                self.devices[magnet].turn_on()
            except KeyError:
                print(
                    "Could not find ",
                    magnet,
                    " in magnet collection, unable to turn on.",
                )

    def degauss(
        self,
        magnets: Optional[Union[str, List]] = None,
    ) -> None:
        """Perform a degauss for each magnet provided in the list"""
        magnets_to_degauss = self._make_magnet_names_list_from_args(magnets)
        if magnets_to_degauss:
            if isinstance(magnets, str):
                magnets_to_degauss = [magnets]
        else:
            magnets_to_degauss = list(self.devices.keys())
        for magnet in magnets_to_degauss:
            try:
                self.devices[magnet].degauss()
            except KeyError:
                print(
                    "Could not find ",
                    magnet,
                    " in magnet collection, unable to degauss.",
                )
