import sys
import unittest
import numpy as np
from mat_emit_scan import MatEmitScan as MES

FILE = 'test_scan2.mat'
BAD_FILE = 'test_scan3.mat'
ITERS = 5
TYPE = 'scan'
PROF_NAME = 'OTRS:IN20:571'
QUAD_NAME = 'QUAD:IN20:525'
QUAD_VAL = -4.22
TIMESTAMP = 737963.0
CHARGE = 0.2446
ENERGY = 0.135
EMIT_X = .36
BETA_X = 1.8
ALPHA_X = -0.6
BMAG_X = 1.2
EMIT_Y = .47
BETA_Y = 1.3
ALPHA_Y = -0.0
BMAG_Y = 1.0

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
        self.assertEqual(round(mes.quad_vals[0], 2), QUAD_VAL)
        self.assertEqual(len(mes.use), ITERS)
        self.assertEqual(round(mes.timestamp), TIMESTAMP)
        self.assertEqual(round(mes.charge, 4), CHARGE)
        self.assertEqual(round(mes.energy, 4), ENERGY)
        self.assertEqual(round(mes.emit_x['Gaussian'], 2), EMIT_X)
        self.assertEqual(round(mes.beta_x['Gaussian'], 1), BETA_X)
        self.assertEqual(round(mes.alpha_x['Gaussian'], 1), ALPHA_X)
        self.assertEqual(round(mes.bmag_x['Gaussian'], 1), BMAG_X)
        self.assertEqual(round(mes.emit_y['Gaussian'], 2), EMIT_Y)
        self.assertEqual(round(mes.beta_y['Gaussian'], 1), BETA_Y)
        self.assertEqual(round(mes.alpha_y['Gaussian'], 1), ALPHA_Y)
        self.assertEqual(round(mes.bmag_y['Gaussian'], 1), BMAG_Y)

if __name__ == '__main__':
    unittest.main()
