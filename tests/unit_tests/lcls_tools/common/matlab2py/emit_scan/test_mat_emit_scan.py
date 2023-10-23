import os
import unittest
import numpy as np
from lcls_tools.common.matlab2py.emit_scan.mat_emit_scan import MatEmitScan as MES


ITERS = 3
TYPE = "scan"
PROF_NAME = "YAGS:GUNB:753"
QUAD_NAME = "SOLN:GUNB:212"
QUAD_VAL = 0.08
TIMESTAMP = 737730.0
CHARGE = 0.0007
ENERGY = 0.0008
EMIT_X = 6.41
BETA_X = 159.5
ALPHA_X = -110.8
BMAG_X = 2009.8
EMIT_Y = 6.22
BETA_Y = 171.3
ALPHA_Y = -119.1
BMAG_Y = 2155.9


class MatEmitScanTest(unittest.TestCase):
    dataset_location = "tests/datasets/scan/emittance/matlab/"
    if not os.path.isdir(dataset_location):
        raise FileNotFoundError(f"Could not find dataset files in {dataset_location}")

    def setUp(self) -> None:
        self.file = os.path.join(
            self.dataset_location, "Emittance-scan-YAGS_GUNB_753-2019-11-01-005431.mat"
        )
        self.bad_file = os.path.join(self.dataset_location, "junk.mat")
        return super().setUp()

    def test_load_mat_file_exception(self):
        self.assertRaises(Exception, MES(self.bad_file))

    def test_init_mat_file(self):
        """Check a vfew of the values, there's a lot of data in beam,
        but not using that now."""
        mes = MES(self.file)
        self.assertEqual(mes.mat_file, self.file)
        self.assertEqual(len(mes.status), ITERS)
        self.assertEqual(mes.scan_type, TYPE)
        self.assertEqual(mes.name, PROF_NAME)
        self.assertEqual(mes.quad_name, QUAD_NAME)
        self.assertEqual(round(mes.quad_vals[2], 2), QUAD_VAL)
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
