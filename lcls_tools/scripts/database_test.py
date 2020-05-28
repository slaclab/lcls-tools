import glob
from database import make_vcc_db

# PV Notes:
# 'IRIS:LGUN:%' = SC laser PV's
# 

H5FILE = 'oct_2019_vcc_database.h5'

#FILES = glob.glob('/u1/lcls/matlab/data/2018/2018-11/2018-11-*/ProfMon-CAMR_IN20_*')
#FILES = glob.glob('/u1/lcls/matlab/data/2019/2019-10/2019*/ProfMon*LGUN*')
VFILES = glob.glob('/u1/lcls/matlab/data/2019/2019-10/2019-10-3*/ProfMon*LGUN*')
YFILES = glob.glob('/u1/lcls/matlab/data/2019/2019-10/2019-10-3*/ProfMon-YAGS_GUNB*')

# Must contain pv's searchable by meme
pv_groups = ['IRIS:LGUN:%','%:GUNB:%:BACT','%:GUNB:%:AACT','TORO:GUNB:%:CHRG']

# Must contain the following:
# data file paths, output filename, pv types and labels.
input_dict = {
            'vcc_files': VFILES,
            'yag_files': YFILES, 
            'outfile':H5FILE,
            'short_description': 'lcls_sc_image_and_pv_data'}  

long_description = "vcc and YAG images with corresponding pv names and data values for EIC area"

test_db = make_vcc_db(input_dict, pv_groups, info=long_description)

