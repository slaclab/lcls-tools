from unittest import TestCase
from unittest.mock import MagicMock

from lcls_tools.common.controls.epics import EPICS_NO_ALARM_VAL
from lcls_tools.superconducting.sc_linac import Machine, Linac
from lcls_tools.superconducting.sc_linac_utils import (
    ALL_CRYOMODULES,
    BEAMLINE_VACUUM_INFIXES,
    INSULATING_VACUUM_CRYOMODULES,
    LINAC_CM_MAP,
)


def make_mock_pv(
    pv_name: str = None, get_val=None, severity=EPICS_NO_ALARM_VAL
) -> MagicMock:
    return MagicMock(
        pvname=pv_name,
        put=MagicMock(return_value=1),
        get=MagicMock(return_value=get_val),
        severity=severity,
    )


class TestLinac(TestCase):
    def setUp(self):
        self.machine = Machine()

    def test_names(self):
        for i in range(4):
            linac = self.machine.linacs[i]
            self.assertEqual(linac.name, f"L{i}B")

    def test_crymodules(self):
        for i in range(4):
            linac = self.machine.linacs[i]
            for cm_name in LINAC_CM_MAP[i]:
                self.assertTrue(cm_name in linac.cryomodules.keys())

    def test_beamline_vacuum_pvs(self):
        for i in range(4):
            linac = self.machine.linacs[i]
            for infix in BEAMLINE_VACUUM_INFIXES[i]:
                self.assertTrue(
                    f"VGXX:{linac.name}:{infix}:COMBO_P" in linac.beamline_vacuum_pvs,
                    msg=f"VGXX:{linac.name}:{infix}:COMBO_P not found",
                )

    def test_insulating_vacuum_pvs(self):
        for i in range(4):
            linac = self.machine.linacs[i]
            for cm in INSULATING_VACUUM_CRYOMODULES[i]:
                self.assertTrue(
                    f"VGXX:{linac.name}:{cm}96:COMBO_P" in linac.insulating_vacuum_pvs,
                    msg=f"VGXX:{linac.name}:{cm}96:COMBO_P not found",
                )


class TestMachine(TestCase):
    def setUp(self):
        self.machine: Machine = Machine()

    def test_num_linacs(self):
        self.assertEqual(len(self.machine.linacs), second=4)

    def test_linac_names(self):
        for i in range(4):
            linac: Linac = self.machine.linacs[i]
            self.assertEqual(
                linac.name,
                second=f"L{i}B",
                msg=f"{linac} not indexed correctly in machine",
            )

    def test_cryomodules(self):
        for cm_name in ALL_CRYOMODULES:
            self.assertTrue(cm_name in self.machine.cryomodules)
