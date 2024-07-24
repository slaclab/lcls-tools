from random import randint
from unittest import TestCase

from lcls_tools.superconducting.sc_linac import Machine, MACHINE
from lcls_tools.superconducting.sc_linac_utils import (
    MAGNET_TRIM_VALUE,
    MAGNET_RESET_VALUE,
    MAGNET_ON_VALUE,
    MAGNET_OFF_VALUE,
    MAGNET_DEGAUSS_VALUE,
)
from tests.unit_tests.lcls_tools.superconducting.test_sc_linac import make_mock_pv

machine = Machine()

# HLs don't have magnets
machine.cryomodules.pop("H1")
machine.cryomodules.pop("H2")

magnets = []
for cm in machine.cryomodules.values():
    magnets.append(cm.quad)
    magnets.append(cm.xcor)
    magnets.append(cm.ycor)

magnet_iterator = iter(magnets)


class TestMagnet(TestCase):
    def test_pv_prefix_quad(self):
        quad = MACHINE.cryomodules["01"].quad
        self.assertEqual(quad.pv_prefix, "QUAD:L0B:0185:")

    def test_pv_prefix_xcor(self):
        quad = MACHINE.cryomodules["01"].xcor
        self.assertEqual(quad.pv_prefix, "XCOR:L0B:0185:")

    def test_pv_prefix_ycor(self):
        quad = MACHINE.cryomodules["01"].ycor
        self.assertEqual(quad.pv_prefix, "YCOR:L0B:0185:")

    def test_bdes(self):
        magnet = next(magnet_iterator)
        val = randint(-10, 10)
        magnet._bdes_pv_obj = make_mock_pv(get_val=val)
        self.assertEqual(magnet.bdes, val)

    def test_bdes_setter(self):
        magnet = next(magnet_iterator)
        val = randint(-10, 10)
        magnet._bdes_pv_obj = make_mock_pv()
        magnet._control_pv_obj = make_mock_pv()
        magnet.bdes = val
        magnet._bdes_pv_obj.put.assert_called_with(val)
        magnet._control_pv_obj.put.assert_called_with(MAGNET_TRIM_VALUE)

    def test_reset(self):
        magnet = next(magnet_iterator)
        magnet._control_pv_obj = make_mock_pv()
        magnet.reset()
        magnet._control_pv_obj.put.assert_called_with(MAGNET_RESET_VALUE)

    def test_turn_on(self):
        magnet = next(magnet_iterator)
        magnet._control_pv_obj = make_mock_pv()
        magnet.turn_on()
        magnet._control_pv_obj.put.assert_called_with(MAGNET_ON_VALUE)

    def test_turn_off(self):
        magnet = next(magnet_iterator)
        magnet._control_pv_obj = make_mock_pv()
        magnet.turn_off()
        magnet._control_pv_obj.put.assert_called_with(MAGNET_OFF_VALUE)

    def test_degauss(self):
        magnet = next(magnet_iterator)
        magnet._control_pv_obj = make_mock_pv()
        magnet.degauss()
        magnet._control_pv_obj.put.assert_called_with(MAGNET_DEGAUSS_VALUE)

    def test_trim(self):
        magnet = next(magnet_iterator)
        magnet._control_pv_obj = make_mock_pv()
        magnet.trim()
        magnet._control_pv_obj.put.assert_called_with(MAGNET_TRIM_VALUE)
