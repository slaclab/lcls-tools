import os
import unittest
from lcls_tools.common.matlab2py.cor_plot.cor_plot_mat_scan import (
    CorPlotMatScan as CPMS,
)

# We need a scan where all struct names are populated
# to fully test.  Would have been nice to populate every
# possible field with something (even empty array)

# TEST FIle metadata
BEAM_NAMES_TEST = (
    "profx",
    "xStat",
    "xStatStd",
    "profy",
    "yStat",
    "yStatStd",
    "profu",
    "uStat",
    "uStatStd",
    "method",
    "stats",
    "statsStd",
)

FIELDS_TEST = ("accelerator", "status", "ctrlPV", "beam", "profPV", "ts", "config")
ACCL_TEST = "LCLS2"
CTRL_PV_TEST = "SOLN:GUNB:212:BCTRL"
CTRL_VAL_0_TEST = 0.073  # First value of scan ctrl pv
ITER_TEST = 10
TS_TEST = 737730.05
SAMPLES_TEST = 2

# QE File metadata
BEAM_NAMES_QE = None

FIELDS_QE = ("accelerator", "status", "ctrlPV", "readPV", "ts", "config")
ACCL_QE = "LCLS2"
CTRL_PV_QE = "MIRR:LGUN:820:M3_MOTR_V"
CTRL_VAL_0_QE = 1.93
ITER_QE = 400
TS_QE = 737728.26


class CorPlotMatScanTest(unittest.TestCase):
    dataset_location: str = "tests/datasets/scan/correlation/matlab"

    def setUp(self) -> None:
        self.file = os.path.join(self.dataset_location, "test_scan.mat")
        self.bad_file = os.path.join(self.dataset_location, "junk.mat")
        self.qe_file = os.path.join(self.dataset_location, "qe_scan.mat")
        try:
            if not os.path.isfile(self.file):
                raise FileNotFoundError(f"Could not find {self.file}, aborting test.")
            if not os.path.isfile(self.bad_file):
                raise FileNotFoundError(
                    f"Could not find {self.bad_file}, aborting test."
                )
            if not os.path.isfile(self.qe_file):
                raise FileNotFoundError(
                    f"Could not find {self.qe_file}, aborting test."
                )
        except FileNotFoundError:
            self.skipTest("Invalid dataset location")
        return super().setUp()

    def test_init_mat_file_test(self):
        cpms = CPMS(self.file)
        self.assertEqual(cpms.fields, FIELDS_TEST)
        self.assertEqual(cpms.accelerator, ACCL_TEST)
        self.assertEqual(cpms.ctrl_pv, CTRL_PV_TEST)
        self.assertEqual(cpms.iterations, ITER_TEST)
        self.assertEqual(round(cpms.ctrl_vals[0], 3), CTRL_VAL_0_TEST)
        self.assertEqual(cpms.beam_names, BEAM_NAMES_TEST)
        self.assertEqual(round(cpms.timestamp, 2), TS_TEST)
        self.assertEqual(cpms.samples, SAMPLES_TEST)

    def test_init_mat_file_qe(self):
        cpms = CPMS(self.qe_file)
        self.assertEqual(cpms.fields, FIELDS_QE)
        self.assertEqual(cpms.accelerator, ACCL_QE)
        self.assertEqual(cpms.ctrl_pv, CTRL_PV_QE)
        self.assertEqual(cpms.iterations, ITER_QE)
        self.assertEqual(round(cpms.ctrl_vals[0], 2), CTRL_VAL_0_QE)
        self.assertEqual(cpms.beam_names, None)
        self.assertEqual(round(cpms.timestamp, 2), TS_QE)

    def test_init_bad_file(self):
        self.assertRaises(Exception, CPMS(self.bad_file))
