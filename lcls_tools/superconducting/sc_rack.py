from typing import Type, Dict

from lcls_tools.superconducting import sc_linac_utils as utils
from lcls_tools.superconducting.sc_cavity import Cavity
from lcls_tools.superconducting.sc_cryomodule import Cryomodule


class Rack(utils.SCLinacObject):
    """
    Python representation of LCLS II RF Racks. This class functions mostly as a
    container for cavities.
    Rack A has cavities 1 through 4, Rack B has cavities 5 through 8.
    """

    def __init__(
        self,
        rack_name,
        cryomodule_object,
    ):
        # type: (str, Cryomodule) -> None
        """
        Parameters
        ----------
        rack_name: str name of rack (always either "A" or "B")
        cryomodule_object: the cryomodule object this rack belongs to
        """

        self.cryomodule: Cryomodule = cryomodule_object
        self.rack_name = rack_name

        self.cavity_class: Type[Cavity] = self.cryomodule.cavity_class
        self.ssa_class = self.cryomodule.ssa_class
        self.stepper_class = self.cryomodule.stepper_class
        self.piezo_class = self.cryomodule.piezo_class

        self.cavities: Dict[int, Cavity] = {}
        self._pv_prefix = self.cryomodule.pv_addr(
            "RACK{RACK}:".format(RACK=self.rack_name)
        )

        if rack_name == "A":
            # rack A always has cavities 1 - 4
            for cavityNum in range(1, 5):
                self.cavities[cavityNum] = self.cavity_class(
                    cavity_num=cavityNum, rack_object=self
                )

        elif rack_name == "B":
            # rack B always has cavities 5 - 8
            for cavityNum in range(5, 9):
                self.cavities[cavityNum] = self.cavity_class(
                    cavity_num=cavityNum, rack_object=self
                )

        else:
            raise Exception(f"Bad rack name {rack_name}")

    @property
    def pv_prefix(self):
        return self._pv_prefix
