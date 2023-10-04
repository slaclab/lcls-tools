import sys
import unittest
import numpy as np
from mat_emit_scan import MatEmitScan as MES

FILE = "test_scan.mat"
BAD_FILE = "junk.mat"
ITERS = 10
TYPE = "scan"
PROF_NAME = "YAGS:GUNB:753"
QUAD_NAME = "SOLN:GUNB:212"
QUAD_VAL = 0.08
TIMESTAMP = 737730.0
CHARGE = 0.0007
ENERGY = 0.0008
EMIT_X = 2.28
BETA_X = 96.1
ALPHA_X = -66.5
BMAG_X = 1207.3
EMIT_Y = 2.63
BETA_Y = 136.9
ALPHA_Y = -94.6
BMAG_Y = 1716.6


class MatEmitScanTest(unittest.TestCase):
    def test_load_mat_file_exception(self):
        self.assertRaises(Exception, MES(BAD_FILE))

    def test_init_mat_file(self):
        """Check a vfew of the values, there's a lot of data in beam,
        but not using that now."""
        mes = MES(FILE)
        self.assertEqual(mes.mat_file, FILE)
        self.assertEqual(len(mes.status), ITERS)
        self.assertEqual(mes.scan_type, TYPE)
        self.assertEqual(mes.name, PROF_NAME)
        self.assertEqual(mes.quad_name, QUAD_NAME)
        self.assertEqual(round(mes.quad_val[9], 2), QUAD_VAL)
        self.assertEqual(len(mes.use), ITERS)
        self.assertEqual(round(mes.timestamp), TIMESTAMP)
        self.assertEqual(round(mes.charge, 4), CHARGE)
        self.assertEqual(round(mes.energy, 4), ENERGY)
        self.assertEqual(round(mes.emit_x["Gaussian"], 2), EMIT_X)
        self.assertEqual(round(mes.beta_x["Gaussian"], 1), BETA_X)
        self.assertEqual(round(mes.alpha_x["Gaussian"], 1), ALPHA_X)
        self.assertEqual(round(mes.bmag_x["Gaussian"], 1), BMAG_X)
        self.assertEqual(round(mes.emit_y["Gaussian"], 2), EMIT_Y)
        self.assertEqual(round(mes.beta_y["Gaussian"], 1), BETA_Y)
        self.assertEqual(round(mes.alpha_y["Gaussian"], 1), ALPHA_Y)
        self.assertEqual(round(mes.bmag_y["Gaussian"], 1), BMAG_Y)


if __name__ == "__main__":
    unittest.main()
