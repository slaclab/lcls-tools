from pydantic import BaseModel, SerializeAsAny, ConfigDict, field_validator
from typing import List, Union, Callable, Dict
from epics import PV


class PVSet(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="forbid",
        frozen=True,
    )
    ...


class ControlInformation(BaseModel):
    model_config = ConfigDict(
        frozen=True,
    )
    control_name: str
    PVs: PVSet

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super(
            ControlInformation,
            self,
        ).__init__(
            *args,
            **kwargs,
        )


class Metadata(BaseModel):
    area: str
    beam_path: List[str]
    sum_l_meters: float

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super(
            Metadata,
            self,
        ).__init__(
            *args,
            **kwargs,
        )


class ApplyDeviceCallbackError(Exception):
    def __init__(
        self,
        message: str,
        *args,
        **kwargs,
    ) -> None:
        super(
            ApplyDeviceCallbackError,
            self,
        ).__init__(
            message,
            *args,
            **kwargs,
        )


class RemoveDeviceCallbackError(Exception):
    def __init__(
        self,
        message: str,
        *args,
        **kwargs,
    ) -> None:
        super(
            RemoveDeviceCallbackError,
            self,
        ).__init__(
            message,
            *args,
            **kwargs,
        )


class Device(BaseModel):
    name: str = None
    controls_information: SerializeAsAny[ControlInformation]
    metadata: SerializeAsAny[Metadata]

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super(Device, self).__init__(
            *args,
            **kwargs,
        )

    @property
    def area(self) -> str:
        """The machine area for this device"""
        return self.metadata.area

    @property
    def sum_l_meters(self) -> float:
        """The position for this device in the design in meters"""
        return self.metadata.sum_l_meters

    @property
    def beam_path(self) -> List[str]:
        """The list of beampaths that include this device"""
        return self.metadata.beam_path

    def get_callbacks(self, pv: str) -> Union[None, dict]:
        """Find which callbacks are tied for the given PV"""
        pv_obj = self._get_pv_object_from_str(pv)
        if pv_obj:
            return pv_obj.callbacks
        return None

    def _is_callback_already_assigned(
        self,
        pv: PV,
        callback_function: Callable,
    ) -> bool:
        """
        Check if a given callback function is already applied to a PV object
        :param pv: an EPICS PV object associated with the class
        :type pv: :class:`epics.PV`
        :param callback_function: The function that will be checked against the pv callback list
        :type callback_function: Callable
        :return: True if callback is already assigned, False is not.
        """
        # items of this list are of the form [(function, kw-args), (function, kw-args), ..]
        applied_callback_functions = list(pv.callbacks.values())
        callback_exists = any(
            [callback_function == f for f, _ in applied_callback_functions]
        )
        return callback_exists

    def _get_callback_index(
        self,
        pv: PV,
        callback_function: Callable,
    ) -> Union[None, int]:
        for index, callback in pv.callbacks.items():
            f, _ = callback
            if f == callback_function:
                return index
        return None

    def _get_attribute(self, attr: str) -> Union[object, None]:
        """
        Wrap around getattr for testing purposes.
        We can mock this function much easier than getattr directly
        """
        return getattr(self, attr, None)

    def _get_pv_object_from_str(self, pv: str) -> PV:
        pv_obj = self._get_attribute("_" + pv)
        return pv_obj

    def add_callback_to_pv(
        self,
        pv: str,
        function: Callable,
    ) -> None:
        """Add a callback function to a given PV that is called upon PV-value change."""
        # check function args
        if not isinstance(pv, str):
            raise ApplyDeviceCallbackError(f"variable {pv} must be of type str")
        if not isinstance(function, Callable):
            raise ApplyDeviceCallbackError(f"variable {function} must be a Callable.")
        # function args okay, try to access class member variable
        pv_obj = self._get_pv_object_from_str(pv)
        if not pv_obj or not isinstance(pv_obj, PV):
            raise ApplyDeviceCallbackError(f"could not find PV attribute for {pv}")
        # class member variable exists, check if callback is already assigned
        if self._is_callback_already_assigned(pv_obj, function):
            raise ApplyDeviceCallbackError(
                f"function {function.__name__} exists as a callback for {pv}"
            )
        # callback not assigned, so lets add the callback:
        pv_obj.add_callback(function)

    def remove_callback_from_pv(
        self,
        pv: str,
        function: Callable,
    ) -> None:
        """Remove a callback function to a given PV."""
        if not isinstance(pv, str):
            raise RemoveDeviceCallbackError(f"variable {pv} must be of type str")
        if not isinstance(function, Callable):
            raise RemoveDeviceCallbackError(f"variable {function} must be a Callable.")
        # function args okay, try to access class member variable
        pv_obj = self._get_pv_object_from_str(pv)
        if not pv_obj or not isinstance(pv_obj, PV):
            raise RemoveDeviceCallbackError(f"could not find PV attribute for {pv}")
        # class member variable exists, check if callback exists
        if not self._is_callback_already_assigned(pv_obj, function):
            raise RemoveDeviceCallbackError(
                f"function {function.__name__} does not exist as a callback for {pv}"
            )
        index = self._get_callback_index(pv_obj, function)
        if index:
            pv_obj.remove_callback(index)


class DeviceCollection(BaseModel):
    devices: Dict[str, SerializeAsAny[Device]] = None

    @field_validator("devices", mode="before")
    def _validate_devices(cls, v):
        """
        Add name field to data that will be passed to Device class
        and then use that dictionary to create each Device.
        """
        for name, device in v.items():
            device = dict(device)
            device.update({"name": name})
            v.update({name: device})
        return v

    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super(
            DeviceCollection,
            self,
        ).__init__(
            *args,
            **kwargs,
        )

    @property
    def device_names(self) -> List[str]:
        """Get all device names in the collection"""
        return list(self.devices.keys())
