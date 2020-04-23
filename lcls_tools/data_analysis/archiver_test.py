import sys
sys.path.append('/Users/nneveu/Github/lcls-tools/lcls_tools/image_processing')
import unittest
from mat_image import MatImage as MI
from archiver import *

FILE = 'vcc/ProfMon-CAMR_IN20_186-2018-11-30-235925.mat'
mi = MI()
mi.load_mat_image(FILE)

class ArchiverTest(unittest.TestCase):

    #mi = MI()
    #mi.load_mat_image(FILE)

    def test_datenum_to_datetime(self):
        self.assertRaises(Exception, datenum_to_datetime(mi.timestamp), '2018-11-30 23:59:25.636356')

    #def test_get_matimage_timestamp(self):
    #    FILE = 'vcc/ProfMon-CAMR_IN20_186-2018-11-30-235925.mat'
    #    self.assertRaises(Exception, get_matimage_timestamp(FILE), 737394.9996022726)

    def test_get_iso_time(self):
        pytime = datenum_to_datetime(mi.timestamp)
        self.assertRaises(Exception, get_iso_time(pytime), '2018-11-30T23:59:25.636356')

if __name__ == '__main__':
    unittest.main()
