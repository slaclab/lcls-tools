from typing import Dict, Callable, Union
from epics import PV


class ControlInformationNotFoundError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class MetadataNotFoundError(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class ApplyDeviceCallbackError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class RemoveDeviceCallbackError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class Device:
    name: str
    control_information: Dict = None
    metadata: Dict = None
    _mandatory_fields: list = ["control_information", "metadata"]

    def __init__(self, name: str = None, config: Dict = None):
        self.name = name
        try:
            # extract and create metadata and control_information attributes from **kwargs.
            [
                setattr(self, k, v)
                for k, v in config.items()
                if k in self._mandatory_fields
            ]
        except KeyError as ke:
            missing_key = ke.args[0]
            if missing_key == "control_information":
                raise ControlInformationNotFoundError(
                    f"Missing control information for device {self.name}, please check yaml file."
                )
            elif missing_key == "metadata":
                raise MetadataNotFoundError(
                    f"Missing metadata for device {self.name}, please check yaml file."
                )

    def _is_callback_already_assigned(
        self, pv: PV, callback_function: Callable
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
        self, pv: PV, callback_function: Callable
    ) -> Union[None, int]:
        for index, callback in pv.callbacks.items():
            f, _ = callback
            if f == callback_function:
                return index
        return None

    def _get_pv_object_from_str(self, pv: str) -> PV:
        pv_obj = getattr(self, "_" + pv, None)
        if not pv_obj or not isinstance(pv_obj, PV):
            raise ApplyDeviceCallbackError(f"could not find PV attribute for {pv}")
        return pv_obj

    def add_callback_to_pv(self, pv: str, function: Callable):
        # check function args
        if not isinstance(pv, str):
            raise ApplyDeviceCallbackError(f"variable {pv} must be of type str")
        if not isinstance(function, Callable):
            raise ApplyDeviceCallbackError(f"variable {function} must be a Callable.")
        # function args okay, try to access class member variable
        pv_obj = self._get_pv_object_from_str(pv)
        # class member variable exists, check if callback is already assigned
        if self._is_callback_already_assigned(pv_obj, function):
            raise ApplyDeviceCallbackError(
                f"function {function.__name__} exists as a callback for {pv}"
            )
        # callback not assigned, so lets add the callback:
        pv_obj.add_callback(function)

    def remove_callback_from_pv(self, pv: str, function: Callable):
        if not isinstance(pv, str):
            raise ApplyDeviceCallbackError(f"variable {pv} must be of type str")
        if not isinstance(function, Callable):
            raise ApplyDeviceCallbackError(f"variable {function} must be a Callable.")
        # function args okay, try to access class member variable
        pv_obj = self._get_pv_object_from_str(pv)
        # class member variable exists, check if callback exists
        if not self._is_callback_already_assigned(pv_obj, function):
            raise RemoveDeviceCallbackError(
                f"function {function.__name__} does not exist as a callback for {pv}"
            )
        if index := self._get_callback_index(pv_obj, function):
            pv_obj.remove_callback(index)
