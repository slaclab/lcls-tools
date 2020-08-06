import sys
import unittest
import numpy as np
from cor_plot_mat_scan import CorPlotMatScan as CPMS

# We need a scan where all struct names are populated
# to fully test.  Would have been nice to populate every
# possible field with something (even empty array), but that
# would be too similar to something that makes sense in the world
# of data structures

BAD_FILE = 'test_scan2.mat'

# TEST FIle metadata
BEAM_NAMES_TEST = (
    'profx',
    'xStat',
    'xStatStd',
    'profy',
    'yStat',
    'yStatStd',
    'profu',
    'uStat',
    'uStatStd',
    'method',
    'stats',
    'statsStd'
)
TEST_FILE = 'test_scan3.mat'
FIELDS_TEST = (
    'accelerator',
    'status',
    'ctrlPV',
    'readPV',
    'beam',
    'profPV',
    'ts',
    'config'
)
ACCL_TEST = 'LCLS2'
CTRL_PV_TEST = 'MIRR:LGUN:820:M3_MOTR_V'
CTRL_VAL_0_TEST = 1.9  # First value of scan ctrl pv
ITER_TEST = 27
TS_TEST = 737730.5
SAMPLES_TEST = 3

#QE File metadata
BEAM_NAMES_QE = None
QE_FILE = 'qe_scan.mat'
FIELDS_QE = (
    'accelerator',
    'status',
    'ctrlPV',
    'readPV',
    'ts',
    'config'
)
ACCL_QE = 'LCLS2'
CTRL_PV_QE = 'MIRR:LGUN:820:M3_MOTR_V'
CTRL_VAL_0_QE = 1.93
ITER_QE = 400
TS_QE = 737728.26

class CorPlotMatScanTest(unittest.TestCase):

    def test_init_mat_file_test(self):
        cpms = CPMS(TEST_FILE)
        self.assertEqual(cpms.accelerator, ACCL_TEST)
        self.assertEqual(cpms.ctrl_pv, CTRL_PV_TEST)
        self.assertEqual(cpms.iterations, ITER_TEST)
        self.assertEqual(round(cpms.ctrl_vals[0], 3), CTRL_VAL_0_TEST)
        self.assertEqual(cpms.beam_names, BEAM_NAMES_TEST)
        self.assertEqual(round(cpms.timestamp, 2), TS_TEST)
        self.assertEqual(cpms.samples, SAMPLES_TEST)

    def test_init_mat_file_qe(self):
        cpms = CPMS(QE_FILE)
        self.assertEqual(cpms.fields, FIELDS_QE)
        self.assertEqual(cpms.accelerator, ACCL_QE)
        self.assertEqual(cpms.ctrl_pv, CTRL_PV_QE)
        self.assertEqual(cpms.iterations, ITER_QE)
        self.assertEqual(round(cpms.ctrl_vals[0],2), CTRL_VAL_0_QE)
        self.assertEqual(cpms.beam_names, None)
        self.assertEqual(round(cpms.timestamp, 2), TS_QE)

    def test_init_bad_file(self):
        self.assertRaises(Exception, CPMS(BAD_FILE))

if __name__ == '__main__':
    unittest.main()