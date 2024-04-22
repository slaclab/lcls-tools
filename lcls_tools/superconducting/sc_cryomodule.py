from typing import Type, Dict, List

from lcls_tools.superconducting import sc_linac_utils as utils
from lcls_tools.superconducting.sc_cavity import Cavity
from lcls_tools.superconducting.sc_linac import Linac
from lcls_tools.superconducting.sc_magnet import Magnet
from lcls_tools.superconducting.sc_piezo import Piezo
from lcls_tools.superconducting.sc_rack import Rack
from lcls_tools.superconducting.sc_ssa import SSA
from lcls_tools.superconducting.sc_stepper import StepperTuner


class Cryomodule(utils.SCLinacObject):
    """
    Python representation of an LCLS II cryomodule. This class functions mostly
    as a container for racks and cryo-level PVs

    """

    def __init__(
        self,
        cryo_name,
        linac_object,
    ):
        # type: (str, Linac) -> None # noqa: E501
        """
        @param cryo_name: str name of Cryomodule i.e. "02", "03", "H1", "H2"
        @param linac_object: the linac object this cryomodule belongs to i.e.
                             CM02 is in linac L1B
        """

        self.name: str = cryo_name
        self.linac: Linac = linac_object

        self.magnet_class: Type[Magnet] = self.linac.magnet_class
        self.rack_class: Type[Rack] = self.linac.rack_class
        self.cavity_class: Type[Cavity] = self.linac.cavity_class
        self.ssa_class: Type[SSA] = self.linac.ssa_class
        self.stepper_class: Type[StepperTuner] = self.linac.stepper_class
        self.piezo_class: Type[Piezo] = self.linac.piezo_class

        if not self.is_harmonic_linearizer:
            self.quad: Magnet = self.magnet_class(magnet_type="QUAD", cryomodule=self)
            self.xcor: Magnet = self.magnet_class(magnet_type="XCOR", cryomodule=self)
            self.ycor: Magnet = self.magnet_class(magnet_type="YCOR", cryomodule=self)

        self._pv_prefix = f"ACCL:{self.linac.name}:{self.name}00:"

        self.cte_prefix = f"CTE:CM{self.name}:"
        self.cvt_prefix = f"CVT:CM{self.name}:"
        self.cpv_prefix = f"CPV:CM{self.name}:"

        if not self.is_harmonic_linearizer:
            self.jt_prefix = f"CLIC:CM{self.name}:3001:PVJT:"
        else:
            name_map: Dict[str, str] = {"H1": "HL01", "H2": "HL02"}
            self.jt_prefix = f"CLIC:{name_map[self.name]}:3001:PVJT:"

        self.ds_level_pv: str = f"CLL:CM{self.name}:2301:DS:LVL"
        self.us_level_pv: str = f"CLL:CM{self.name}:2601:US:LVL"
        self.ds_pressure_pv: str = f"CPT:CM{self.name}:2302:DS:PRESS"
        self.jt_valve_readback_pv: str = self.jt_prefix + "ORBV"
        self.heater_readback_pv: str = f"CPIC:CM{self.name}:0000:EHCV:ORBV"

        self.rack_a: Rack = self.rack_class(rack_name="A", cryomodule_object=self)
        self.rack_b: Rack = self.rack_class(rack_name="B", cryomodule_object=self)

        self.cavities: Dict[int, Cavity] = {}
        self.cavities.update(self.rack_a.cavities)
        self.cavities.update(self.rack_b.cavities)

        if self.is_harmonic_linearizer:
            self.coupler_vacuum_pvs: List[str] = [
                self.linac.vacuum_prefix + "{cm}09:COMBO_P".format(cm=self.name),
                self.linac.vacuum_prefix + "{cm}19:COMBO_P".format(cm=self.name),
            ]
        else:
            self.coupler_vacuum_pvs: List[str] = [
                self.linac.vacuum_prefix + "{cm}14:COMBO_P".format(cm=self.name)
            ]

        self.vacuum_pvs: List[str] = (
            self.coupler_vacuum_pvs
            + self.linac.beamline_vacuum_pvs
            + self.linac.insulating_vacuum_pvs
        )

    @property
    def is_harmonic_linearizer(self):
        return self.name in ["H1", "H2"]

    @property
    def pv_prefix(self):
        return self._pv_prefix
