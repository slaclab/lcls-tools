import sys
import unittest
import numpy as np
from cor_plot_mat_scan import CorPlotMatScan as CPMS

# We need a scan where all struct names are populated
# to fully test.  Would have been nice to populate every
# possible field with something (even empty array), but that
# would be too similar to something that makes sense in the world
# of data structures
TEST_FILE = 'test_scan.mat'
QE_FILE = 'qe_scan.mat'
BAD_FILE = 'junk.mat'

class MatEmitScanTest(unittest.TestCase):

    def test_load_mat_file_test(self):
        cpms = CPMS(TEST_FILE)

    def test_load_mat_file_qe(self):
        cpms = CPMS(QE_FILE)

    def test_load_bad_file(self):
        self.assertRaises(Exception, CPMS(BAD_FILE))

if __name__ == '__main__':
    unittest.main()