from typing import Optional, TYPE_CHECKING

from lcls_tools.common.controls.pyepics.utils import PV
from lcls_tools.superconducting import sc_linac_utils as utils

if TYPE_CHECKING:
    from lcls_tools.superconducting.sc_cryomodule import Cryomodule


class Magnet(utils.SCLinacObject):
    """
    Python representation of LCLS II magnets. This class provides wrappers for
    common magnet controls including powering on/off and changing strength

    """

    def __init__(self, magnet_type: str, cryomodule: "Cryomodule"):
        """
        @param magnet_type: One of QUAD, XCOR, or YCOR
        @param cryomodule: the cryomodule object in which this magnet is contained
        """

        self._pv_prefix = f"{magnet_type}:{cryomodule.linac.name}:{cryomodule.name}85:"

        self.name = magnet_type
        self.cryomodule: "Cryomodule" = cryomodule

        self.bdes_pv: str = self.pv_addr("BDES")
        self._bdes_pv_obj: Optional[PV] = None

        self.control_pv: str = self.pv_addr("CTRL")
        self._control_pv_obj: Optional[PV] = None

        self.interlock_pv: str = self.pv_addr("INTLKSUMY")
        self.ps_status_pv: str = self.pv_addr("STATE")
        self.bact_pv: str = self.pv_addr("BACT")
        self.iact_pv: str = self.pv_addr("IACT")

        # changing IDES immediately perturbs
        self.ides_pv: str = self.pv_addr("IDES")

    @property
    def pv_prefix(self):
        return self._pv_prefix

    @property
    def control_pv_obj(self) -> PV:
        if not self._control_pv_obj:
            self._control_pv_obj = PV(self.control_pv)
        return self._control_pv_obj

    @property
    def bdes(self):
        if not self._bdes_pv_obj:
            self._bdes_pv_obj = PV(self.bdes_pv)
        return self._bdes_pv_obj.get()

    @bdes.setter
    def bdes(self, value):
        self._bdes_pv_obj.put(value)
        self.control_pv_obj.put(utils.MAGNET_TRIM_VALUE)

    def reset(self):
        self.control_pv_obj.put(utils.MAGNET_RESET_VALUE)

    def turn_on(self):
        self.control_pv_obj.put(utils.MAGNET_ON_VALUE)

    def turn_off(self):
        self.control_pv_obj.put(utils.MAGNET_OFF_VALUE)

    def degauss(self):
        self.control_pv_obj.put(utils.MAGNET_DEGAUSS_VALUE)

    def trim(self):
        self.control_pv_obj.put(utils.MAGNET_TRIM_VALUE)
