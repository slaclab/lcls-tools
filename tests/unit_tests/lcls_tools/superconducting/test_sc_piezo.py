from random import randint
from unittest import TestCase
from unittest.mock import MagicMock, Mock

from lcls_tools.superconducting.sc_linac import CavityIterator, MACHINE
from lcls_tools.superconducting.sc_linac_utils import (
    PIEZO_ENABLE_VALUE,
    PIEZO_DISABLE_VALUE,
    PIEZO_MANUAL_VALUE,
    PIEZO_FEEDBACK_VALUE,
)
from tests.unit_tests.lcls_tools.superconducting.test_sc_linac import make_mock_pv

cavity_iterator = CavityIterator()


class TestPiezo(TestCase):
    def setUp(self):
        self.num_calls = 0

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
        piezo = next(cavity_iterator.non_hl_iterator).piezo
        stat = randint(0, 1)
        piezo._feedback_stat_pv_obj = make_mock_pv(get_val=stat)
        self.assertEqual(piezo.feedback_stat, stat)

    def test_in_manual(self):
        piezo = next(cavity_iterator.non_hl_iterator).piezo
        piezo._feedback_stat_pv_obj = make_mock_pv(get_val=PIEZO_MANUAL_VALUE)
        self.assertTrue(piezo.in_manual)

    def test_not_in_manual(self):
        piezo = next(cavity_iterator.non_hl_iterator).piezo
        piezo._feedback_stat_pv_obj = make_mock_pv(get_val=PIEZO_FEEDBACK_VALUE)
        self.assertFalse(piezo.in_manual)

    def test_set_to_feedback(self):
        piezo = next(cavity_iterator.non_hl_iterator).piezo
        piezo._feedback_control_pv_obj = make_mock_pv()
        piezo.set_to_feedback()
        piezo._feedback_control_pv_obj.put.assert_called_with(PIEZO_FEEDBACK_VALUE)

    def test_set_to_manual(self):
        piezo = next(cavity_iterator.non_hl_iterator).piezo
        piezo._feedback_control_pv_obj = make_mock_pv()
        piezo.set_to_manual()
        piezo._feedback_control_pv_obj.put.assert_called_with(PIEZO_MANUAL_VALUE)

    def mock_status(self):
        if self.num_calls < 1:
            self.num_calls += 1
            return PIEZO_DISABLE_VALUE
        else:
            self.num_calls = 0
            return PIEZO_ENABLE_VALUE

    def test_enable(self):
        piezo = next(cavity_iterator.non_hl_iterator).piezo
        piezo._bias_voltage_pv_obj = make_mock_pv()
        piezo._enable_stat_pv_obj = make_mock_pv()
        piezo._enable_stat_pv_obj.get = self.mock_status
        piezo.cavity.check_abort = make_mock_pv()
        piezo._enable_pv_obj = make_mock_pv()

        piezo.enable()
        piezo._bias_voltage_pv_obj.put.assert_called_with(25)
        piezo.cavity.check_abort.assert_called()
        piezo._enable_pv_obj.put.assert_called_with(PIEZO_ENABLE_VALUE)

    def test_enable_feedback(self):
        piezo = next(cavity_iterator.non_hl_iterator).piezo
        piezo.enable = MagicMock()
        piezo._feedback_stat_pv_obj = make_mock_pv(get_val=PIEZO_MANUAL_VALUE)

        def set_feedback():
            piezo._feedback_stat_pv_obj = make_mock_pv(get_val=PIEZO_FEEDBACK_VALUE)

        piezo.set_to_feedback = Mock(side_effect=set_feedback)
        piezo.set_to_manual = MagicMock()

        piezo.enable_feedback()
        piezo.enable.assert_called()
        piezo.set_to_feedback.assert_called()

    def test_disable_feedback(self):
        piezo = next(cavity_iterator.non_hl_iterator).piezo
        piezo.enable = MagicMock()
        piezo._feedback_stat_pv_obj = make_mock_pv(get_val=PIEZO_FEEDBACK_VALUE)

        def set_manual():
            piezo._feedback_stat_pv_obj = make_mock_pv(get_val=PIEZO_MANUAL_VALUE)

        piezo.set_to_manual = Mock(side_effect=set_manual)
        piezo.set_to_feedback = MagicMock()

        piezo.disable_feedback()
        piezo.enable.assert_called()
        piezo.set_to_manual.assert_called()
