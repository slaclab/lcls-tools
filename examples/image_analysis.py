import numpy as np
import LCLS_Devices as inj
import glob 

#Not tested, or cleaned up yet

filename = 'ProfMon-CAMR_LGUN_950-2019-08-15-171000.mat'

yag = inj.ProMo('YAG01B')
yag.acquireImage(load=filename, calc_centroid=True, calc_rms=True, plotstat=True, plotmm=True)



