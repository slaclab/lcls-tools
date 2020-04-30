import h5py
import numpy as np
import os,sys
from datetime import datetime

sys.path.append('../image_processing')
sys.path.append('../data_analysis')

import meme.archive
import meme.names
from mat_image import MatImage as MI
from archiver import get_iso_time, datenum_to_datetime, save_mat_image_to_h5, save_pvdata_to_h5 


def make_vcc_db(input_dict, pv_list, info='No info given at run time.'):
    """
    Return a h5 database with PV names and values
    corresponding to each VCC image.
    
    Assumes the user is supplying VCC and YAG images.
    This means only one set of PV values apply to each image.
    The data was only taken at ONE timestamp.
    This will not work for correlation plots, or scans.
    """
    #area      = input_dict['area']
    yag_files = input_dict['yag_files']
    vcc_files = input_dict['vcc_files']
    outname   = input_dict['outfile']
    top_group = input_dict['short_description']

    vhf = h5py.File(outname, 'w')
    vhf.attrs['information'] = info
    vtop = vhf.create_group(top_group+'_vcc')
    ytop = vhf.create_group(top_group+'_yag')

    for files,group in zip([vcc_files, yag_files],[vtop,ytop]):
 
        for filename in files:
            # Load vcc image
            mimage    = MI()
            mimage.load_mat_image(filename)  
            try:
                # Save vcc image + metadata
                image_group = save_mat_image_to_h5(mimage, group)        
                # Save pv data related to image
                save_pvdata_to_h5(pv_list,image_group) 
            except:
                print('Could not save YAG file:', filename)

    vhf.close()

           

