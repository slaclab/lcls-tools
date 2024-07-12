from random import randint
from unittest import TestCase

from lcls_tools.superconducting.sc_linac import MACHINE


class TestCryomodule(TestCase):
    def test_is_harmonic_linearizer_true(self):
        hl = MACHINE.cryomodules[f"H{randint(1,2)}"]
        self.assertTrue(
            hl.is_harmonic_linearizer, msg=f"{hl} is_harmonic_linearizer is not true"
        )

    def test_is_harmonic_linearizer_false(self):
        cm = MACHINE.cryomodules[f"{randint(1, 35):02d}"]
        self.assertFalse(
            cm.is_harmonic_linearizer, msg=f"{cm} is_harmonic_linearizer is not false"
        )

    def test_pv_prefix(self):
        cm = MACHINE.cryomodules["01"]
        self.assertEqual(cm.pv_prefix, "ACCL:L0B:0100:")

    def test_num_cavities(self):
        cm = MACHINE.cryomodules[f"{randint(1, 35):02d}"]
        self.assertEqual(len(cm.cavities.keys()), 8)
