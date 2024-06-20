from time import sleep
from typing import Optional, TYPE_CHECKING

from lcls_tools.common.controls.pyepics.utils import PV
from lcls_tools.superconducting import sc_linac_utils as utils

if TYPE_CHECKING:
    from lcls_tools.superconducting.sc_cavity import Cavity


class Piezo(utils.SCLinacObject):
    """
    Python representation of LCLS II piezo tuners. This class provides utility
    functions for toggling feedback mode and changing bias voltage and DC offset

    """

    def __init__(self, cavity: "Cavity"):
        """
        @param cavity: The cavity object tuned by this piezo
        """

        self.cavity: "Cavity" = cavity
        self._pv_prefix: str = self.cavity.pv_addr("PZT:")

        self.enable_pv: str = self.pv_addr("ENABLE")
        self._enable_pv_obj: Optional[PV] = None

        self.enable_stat_pv: str = self.pv_addr("ENABLESTAT")
        self._enable_stat_pv_obj: Optional[PV] = None

        self.feedback_control_pv: str = self.pv_addr("MODECTRL")
        self._feedback_control_pv_obj: Optional[PV] = None

        self.feedback_stat_pv: str = self.pv_addr("MODESTAT")
        self._feedback_stat_pv_obj: Optional[PV] = None

        self.feedback_setpoint_pv: str = self.pv_addr("INTEG_SP")
        self._feedback_setpoint_pv_obj: Optional[PV] = None

        self.dc_setpoint_pv: str = self.pv_addr("DAC_SP")
        self._dc_setpoint_pv_obj: Optional[PV] = None

        self.bias_voltage_pv: str = self.pv_addr("BIAS")
        self._bias_voltage_pv_obj: Optional[PV] = None

        self.voltage_pv: str = self.pv_addr("V")
        self._voltage_pv_obj: Optional[PV] = None

    def __str__(self):
        return self.cavity.__str__() + " Piezo"

    @property
    def pv_prefix(self):
        return self._pv_prefix

    @property
    def voltage_pv_obj(self):
        if not self._voltage_pv_obj:
            self._voltage_pv_obj = PV(self.voltage_pv)
        return self._voltage_pv_obj

    @property
    def voltage(self):
        return self.voltage_pv_obj.get()

    @property
    def bias_voltage_pv_obj(self):
        if not self._bias_voltage_pv_obj:
            self._bias_voltage_pv_obj = PV(self.bias_voltage_pv)
        return self._bias_voltage_pv_obj

    @property
    def bias_voltage(self):
        return self.bias_voltage_pv_obj.get()

    @bias_voltage.setter
    def bias_voltage(self, value):
        self.bias_voltage_pv_obj.put(value)

    @property
    def dc_setpoint_pv_obj(self) -> PV:
        if not self._dc_setpoint_pv_obj:
            self._dc_setpoint_pv_obj = PV(self.dc_setpoint_pv)
        return self._dc_setpoint_pv_obj

    @property
    def dc_setpoint(self):
        return self.dc_setpoint_pv_obj.get()

    @dc_setpoint.setter
    def dc_setpoint(self, value: float):
        self.dc_setpoint_pv_obj.put(value)

    @property
    def feedback_setpoint_pv_obj(self) -> PV:
        if not self._feedback_setpoint_pv_obj:
            self._feedback_setpoint_pv_obj = PV(self.feedback_setpoint_pv)
        return self._feedback_setpoint_pv_obj

    @property
    def feedback_setpoint(self):
        return self.feedback_setpoint_pv_obj.get()

    @feedback_setpoint.setter
    def feedback_setpoint(self, value):
        self.feedback_setpoint_pv_obj.put(value)

    @property
    def enable_pv_obj(self) -> PV:
        if not self._enable_pv_obj:
            self._enable_pv_obj = PV(self._pv_prefix + "ENABLE")
        return self._enable_pv_obj

    @property
    def is_enabled(self) -> bool:
        if not self._enable_stat_pv_obj:
            self._enable_stat_pv_obj = PV(self.enable_stat_pv)
        return self._enable_stat_pv_obj.get() == utils.PIEZO_ENABLE_VALUE

    @property
    def feedback_control_pv_obj(self) -> PV:
        if not self._feedback_control_pv_obj:
            self._feedback_control_pv_obj = PV(self.feedback_control_pv)
        return self._feedback_control_pv_obj

    @property
    def feedback_stat(self):
        if not self._feedback_stat_pv_obj:
            self._feedback_stat_pv_obj = PV(self.feedback_stat_pv)
        return self._feedback_stat_pv_obj.get()

    @property
    def in_manual(self) -> bool:
        return self.feedback_stat == utils.PIEZO_MANUAL_VALUE

    def set_to_feedback(self):
        self.feedback_control_pv_obj.put(utils.PIEZO_FEEDBACK_VALUE)

    def set_to_manual(self):
        self.feedback_control_pv_obj.put(utils.PIEZO_MANUAL_VALUE)

    def enable(self):
        self.bias_voltage = 25
        while not self.is_enabled:
            self.cavity.check_abort()
            print(f"{self} not enabled, trying to enable")
            self.enable_pv_obj.put(utils.PIEZO_DISABLE_VALUE)
            sleep(2)
            self.enable_pv_obj.put(utils.PIEZO_ENABLE_VALUE)
            sleep(2)

    def enable_feedback(self):
        self.enable()
        while self.in_manual:
            self.cavity.check_abort()
            print(f"{self} feedback not enabled, trying to enable feedback")
            self.set_to_manual()
            sleep(2)
            self.set_to_feedback()
            sleep(2)

    def disable_feedback(self):
        self.enable()
        while not self.in_manual:
            self.cavity.check_abort()
            print(f"{self} feedback enabled, trying to disable feedback")
            self.set_to_feedback()
            sleep(2)
            self.set_to_manual()
            sleep(2)
