import unittest
from lcls_tools.common.beam_calcs.sol_calc.sol_calc import SolCalc


class SolCorrectionTest(unittest.TestCase):
    def test_initialization(self):
        """Test initial properties propagate and are gettable"""
        s = SolCalc(0.05, 0.5, 0.1)
        self.assertEqual(s.length, 0.05)
        self.assertEqual(s.gun_energy, 0.5)
        self.assertEqual(s.distance, 0.1)

    def test_momentum(self):
        """Test momentume calculation is correct for 0.5 MeV"""
        s = SolCalc(0.05, 0.5, 0.1)
        self.assertEqual("%.3g" % s.calc_p(), "4.66e-22")
