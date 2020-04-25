import glob
from database import make_vcc_db

FILES = glob.glob('vcc/*')

H5FILE = 'test_database.h5'

description = "vcc images and corresponding pv names and values for magnets in GUNB area"
test_db = make_vcc_db(FILES[:3], area="GUNB", outname=H5FILE, info=description)

