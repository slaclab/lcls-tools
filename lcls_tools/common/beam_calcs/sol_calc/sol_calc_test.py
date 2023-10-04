import sys
import unittest
from sol_calc import SolCalc as S


class SolCorrectionTest(unittest.TestCase):
    def test_initialization(self):
        """Test initial properties propagate and are gettable"""
        s = S(0.05, 0.5, 0.1)
        self.assertEqual(s.length, 0.05)
        self.assertEqual(s.gun_energy, 0.5)
        self.assertEqual(s.distance, 0.1)

    def test_momentum(self):
        """Test momentume calculation is correct for 0.5 MeV"""
        s = S(0.05, 0.5, 0.1)
        self.assertEqual("%.3g" % s.calc_p(), "4.66e-22")


if __name__ == "__main__":
    unittest.main()
