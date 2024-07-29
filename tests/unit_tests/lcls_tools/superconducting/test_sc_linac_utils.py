from random import randint
from unittest import TestCase

from lcls_tools.superconducting.sc_linac_utils import stepper_tol_factor


class Test(TestCase):
    def test_stepper_tol_factor_low(self):
        self.assertEqual(stepper_tol_factor(randint(-50000, 0)), 10)

    def test_stepper_tol_factor_high(self):
        self.assertEqual(
            stepper_tol_factor(randint(int(50e6) + 1, int(50e6 * 2))), 1.01
        )

    def test_stepper_tol_factor(self):
        self.assertTrue(1.01 <= stepper_tol_factor(randint(50000, int(50e6))) <= 10)
