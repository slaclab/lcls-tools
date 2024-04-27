from unittest import TestCase

from lcls_tools.superconducting.sc_linac import MACHINE
from lcls_tools.superconducting.sc_stepper import StepperTuner
from tests.unit_tests.lcls_tools.superconducting.test_sc_linac import make_mock_pv


class TestStepperTuner(TestCase):
    def setUp(self):
        self.stepper_tuner: StepperTuner = (
            MACHINE.cryomodules["03"].cavities[1].stepper_tuner
        )
        self.step_scale = -0.00589677
        self.stepper_tuner._hz_per_microstep_pv_obj = make_mock_pv(
            self.stepper_tuner.hz_per_microstep_pv, get_val=self.step_scale
        )

    def test_pv_prefix(self):
        self.skipTest("not implemented")

    def test_hz_per_microstep(self):
        self.assertEqual(self.stepper_tuner.hz_per_microstep, abs(self.step_scale))

    def test_check_abort(self):
        self.fail()

    def test_abort(self):
        self.fail()

    def test_move_positive(self):
        self.fail()

    def test_move_negative(self):
        self.fail()

    def test_step_des(self):
        self.fail()

    def test_motor_moving(self):
        self.fail()

    def test_reset_signed_steps(self):
        self.fail()

    def test_on_limit_switch(self):
        self.fail()

    def test_max_steps(self):
        self.fail()

    def test_speed(self):
        self.fail()

    def test_restore_defaults(self):
        self.fail()

    def test_move(self):
        self.fail()

    def test_issue_move_command(self):
        self.fail()
