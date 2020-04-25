import h5py
import numpy as np
import os,sys
sys.path.append('../image_processing')
from datetime import datetime

import meme.archive
import meme.names
from mat_image import MatImage as MI
from archiver import get_iso_time, datenum_to_datetime

def make_vcc_db(files, area="GUNB", outname='vcc_database', top_group = 'lcls_sc_vcc_image_and_pv_data/', info='Not given'):
    """
    Return a h5 database with PV names and values
    corresponding to each VCC image.
    
    Assumes the user is supplying VCC images.
    This means only one set of PV values apply to each image.
    The data waos only taken at ONE timestamp.
    This will not work for correlation plots, or scans.
    """
    
    vhf = h5py.File(outname, 'w')
    top = vhf.create_group(top_group)
    top.attrs['information'] = info
 
    for filename in files:
        mimage    = MI()
        mimage.load_mat_image(filename)  
        
        timestamp = datenum_to_datetime(mimage.timestamp)
        isotime   = get_iso_time(timestamp)
        group     = vhf.create_group(top_group+isotime)
        group.create_dataset('image', data=mimage.image)
        
        magnets   = vhf.create_group(top_group+isotime+'/magnets')
        pv_names  = meme.names.list_pvs('%:%:BACT',tag=area, sort_by="z")
        pv_values = meme.archive.get(pv_names, from_time=timestamp, to_time=timestamp)

        for pv in pv_values:
            magnets.create_dataset(pv['pvName'], data=pv['value']['value']['values'])

        #print(type(pv_values[:]))
        #print(np.shape(pv_values[:][0]))
	#print(i['pvName'], i['value']['value']['values'])
        #print('\n\n\n')  
    #print(pv_values)
    vhf.close()

           

