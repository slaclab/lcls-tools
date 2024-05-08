from random import randint
from unittest import TestCase
from unittest.mock import MagicMock

from lcls_tools.superconducting.sc_linac import CavityIterator
from lcls_tools.superconducting.sc_linac_utils import (
    StepperAbortError,
    STEPPER_ON_LIMIT_SWITCH_VALUE,
    DEFAULT_STEPPER_MAX_STEPS,
    DEFAULT_STEPPER_SPEED,
)
from tests.unit_tests.lcls_tools.superconducting.test_sc_linac import make_mock_pv

cavity_iterator = CavityIterator()


class TestStepperTuner(TestCase):
    def setUp(self):
        self.step_scale = -0.00589677

    def test_pv_prefix(self):
        cavity = next(cavity_iterator.non_hl_iterator)
        self.assertEqual(cavity.stepper_tuner.pv_prefix, cavity.pv_prefix + "STEP:")

    def test_hz_per_microstep(self):
        stepper = next(cavity_iterator.non_hl_iterator).stepper_tuner
        stepper._hz_per_microstep_pv_obj = make_mock_pv(get_val=self.step_scale)
        self.assertEqual(stepper.hz_per_microstep, abs(self.step_scale))

    def test_check_abort(self):
        cavity = next(cavity_iterator.non_hl_iterator)
        cavity.check_abort = MagicMock()

        stepper = cavity.stepper_tuner
        stepper.abort = MagicMock()
        stepper.abort_flag = False
        try:
            stepper.check_abort()
            cavity.check_abort.assert_called()
        except StepperAbortError:
            self.fail(f"{stepper} abort called unexpectedly")

        stepper.abort_flag = True
        self.assertRaises(
            StepperAbortError,
            stepper.check_abort,
            f"{stepper} did not abort when flag set to true",
        )

    def test_abort(self):
        stepper = next(cavity_iterator.non_hl_iterator).stepper_tuner
        stepper._abort_pv_obj = make_mock_pv()
        stepper.abort()
        stepper._abort_pv_obj.put.assert_called_with(1)

    def test_move_positive(self):
        stepper = next(cavity_iterator.non_hl_iterator).stepper_tuner
        stepper._move_pos_pv_obj = make_mock_pv()
        stepper.move_positive()
        stepper._move_pos_pv_obj.put.assert_called_with(1)

    def test_move_negative(self):
        stepper = next(cavity_iterator.non_hl_iterator).stepper_tuner
        stepper._move_neg_pv_obj = make_mock_pv()
        stepper.move_negative()
        stepper._move_neg_pv_obj.put.assert_called_with(1)

    def test_step_des(self):
        stepper = next(cavity_iterator.non_hl_iterator).stepper_tuner
        step_des = randint(0, 10000000)
        stepper._step_des_pv_obj = make_mock_pv(get_val=step_des)
        self.assertEqual(stepper.step_des, step_des)

    def test_motor_moving(self):
        stepper = next(cavity_iterator.non_hl_iterator).stepper_tuner
        stepper._motor_moving_pv_obj = make_mock_pv(get_val=1)
        self.assertTrue(stepper.motor_moving)

        stepper._motor_moving_pv_obj = make_mock_pv(get_val=0)
        self.assertFalse(stepper.motor_moving)

    def test_reset_signed_steps(self):
        stepper = next(cavity_iterator.non_hl_iterator).stepper_tuner
        stepper._reset_signed_pv_obj = make_mock_pv()
        stepper.reset_signed_steps()
        stepper._reset_signed_pv_obj.put.assert_called_with(0)

    def test_on_limit_switch_a(self):
        stepper = next(cavity_iterator.non_hl_iterator).stepper_tuner
        stepper._limit_switch_a_pv_obj = make_mock_pv(
            get_val=STEPPER_ON_LIMIT_SWITCH_VALUE
        )
        stepper._limit_switch_b_pv_obj = make_mock_pv(
            get_val=STEPPER_ON_LIMIT_SWITCH_VALUE + 1
        )
        self.assertTrue(stepper.on_limit_switch)

    def test_on_limit_switch_b(self):
        stepper = next(cavity_iterator.non_hl_iterator).stepper_tuner
        stepper._limit_switch_a_pv_obj = make_mock_pv(
            get_val=STEPPER_ON_LIMIT_SWITCH_VALUE + 1
        )
        stepper._limit_switch_b_pv_obj = make_mock_pv(
            get_val=STEPPER_ON_LIMIT_SWITCH_VALUE
        )
        self.assertTrue(stepper.on_limit_switch)

    def test_on_limit_switch_neither(self):
        stepper = next(cavity_iterator.non_hl_iterator).stepper_tuner
        stepper._limit_switch_a_pv_obj = make_mock_pv(
            get_val=STEPPER_ON_LIMIT_SWITCH_VALUE + 1
        )
        stepper._limit_switch_b_pv_obj = make_mock_pv(
            get_val=STEPPER_ON_LIMIT_SWITCH_VALUE + 1
        )
        self.assertFalse(stepper.on_limit_switch)

    def test_max_steps(self):
        stepper = next(cavity_iterator.non_hl_iterator).stepper_tuner
        max_steps = randint(0, 10000000)
        stepper._max_steps_pv_obj = make_mock_pv(get_val=max_steps)
        self.assertEqual(stepper.max_steps, max_steps)

    def test_speed(self):
        stepper = next(cavity_iterator.non_hl_iterator).stepper_tuner
        speed = randint(0, 10000000)
        stepper._speed_pv_obj = make_mock_pv(get_val=speed)
        self.assertEqual(stepper.speed, speed)

    def test_restore_defaults(self):
        stepper = next(cavity_iterator.non_hl_iterator).stepper_tuner
        stepper._max_steps_pv_obj = make_mock_pv()
        stepper._speed_pv_obj = make_mock_pv()

        stepper.restore_defaults()
        stepper._max_steps_pv_obj.put.assert_called_with(DEFAULT_STEPPER_MAX_STEPS)
        stepper._speed_pv_obj.put.assert_called_with(DEFAULT_STEPPER_SPEED)

    def test_move(self):
        stepper = next(cavity_iterator.non_hl_iterator).stepper_tuner
        num_steps = randint(-DEFAULT_STEPPER_MAX_STEPS, 0)
        stepper.check_abort = MagicMock()
        stepper._max_steps_pv_obj = make_mock_pv()
        stepper._speed_pv_obj = make_mock_pv()
        stepper._step_des_pv_obj = make_mock_pv()
        stepper.issue_move_command = MagicMock()
        stepper.restore_defaults = MagicMock()

        stepper.move(num_steps=num_steps)
        stepper.check_abort.assert_called()
        stepper._max_steps_pv_obj.put.assert_called_with(DEFAULT_STEPPER_MAX_STEPS)
        stepper._speed_pv_obj.put.assert_called_with(DEFAULT_STEPPER_SPEED)
        stepper._step_des_pv_obj.put.assert_called_with(abs(num_steps))
        stepper.issue_move_command.assert_called_with(num_steps, check_detune=True)
        stepper.restore_defaults.assert_called()

    def test_issue_move_command(self):
        stepper = next(cavity_iterator.non_hl_iterator).stepper_tuner
        stepper.issue_move_command()
