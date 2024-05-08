from random import randint
from unittest import TestCase

from lcls_tools.superconducting.sc_linac import CavityIterator, MACHINE
from lcls_tools.superconducting.sc_linac_utils import (
    PIEZO_ENABLE_VALUE,
    PIEZO_DISABLE_VALUE,
)
from tests.unit_tests.lcls_tools.superconducting.test_sc_linac import make_mock_pv

cavity_iterator = CavityIterator()


class TestPiezo(TestCase):
    def test_pv_prefix(self):
        piezo = MACHINE.cryomodules["01"].cavities[1].piezo
        self.assertEqual(piezo.pv_prefix, "ACCL:L0B:0110:PZT:")

    def test_voltage(self):
        piezo = next(cavity_iterator.non_hl_iterator).piezo
        val = randint(-50, 50)
        piezo._voltage_pv_obj = make_mock_pv(get_val=val)
        self.assertEqual(piezo.voltage, val)

    def test_bias_voltage(self):
        piezo = next(cavity_iterator.non_hl_iterator).piezo
        val = randint(-50, 50)
        piezo._bias_voltage_pv_obj = make_mock_pv(get_val=val)
        self.assertEqual(piezo.bias_voltage, val)

    def test_dc_setpoint(self):
        piezo = next(cavity_iterator.non_hl_iterator).piezo
        val = randint(-50, 50)
        piezo._dc_setpoint_pv_obj = make_mock_pv(get_val=val)
        self.assertEqual(piezo.dc_setpoint, val)

    def test_feedback_setpoint(self):
        piezo = next(cavity_iterator.non_hl_iterator).piezo
        val = randint(-50, 50)
        piezo._feedback_setpoint_pv_obj = make_mock_pv(get_val=val)
        self.assertEqual(piezo.feedback_setpoint, val)

    def test_is_enabled(self):
        piezo = next(cavity_iterator.non_hl_iterator).piezo
        piezo._enable_stat_pv_obj = make_mock_pv(get_val=PIEZO_ENABLE_VALUE)
        self.assertTrue(piezo.is_enabled)

    def test_is_not_enabled(self):
        piezo = next(cavity_iterator.non_hl_iterator).piezo
        piezo._enable_stat_pv_obj = make_mock_pv(get_val=PIEZO_DISABLE_VALUE)
        self.assertFalse(piezo.is_enabled)

    def test_feedback_stat(self):
        self.fail()

    def test_in_manual(self):
        self.fail()

    def test_set_to_feedback(self):
        self.fail()

    def test_set_to_manual(self):
        self.fail()

    def test_enable(self):
        self.fail()

    def test_enable_feedback(self):
        self.fail()

    def test_disable_feedback(self):
        self.fail()
