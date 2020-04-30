import h5py
import numpy as np
import os,sys
sys.path.append('../image_processing')
from datetime import datetime

import meme.archive
import meme.names
from mat_image import MatImage as MI
from archiver import get_iso_time, datenum_to_datetime, add_mat_image_attributes 


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
    top = vhf.create_group(top_group+'_vcc')
    top.attrs['information'] = info
 
    for filename in vcc_files:
        # Load vcc image
        mimage    = MI()
        mimage.load_mat_image(filename)  
        # Get timestamp and save vcc image + metadata 
        timestamp   = datenum_to_datetime(mimage.timestamp)
        isotime     = get_iso_time(timestamp)
        image_group = top.create_group(isotime)
        image_data  = image_group.create_dataset('image', data=mimage.image)
        image_data.attrs['isotime'] = isotime	
        add_mat_image_attributes(mimage, image_data)
    
        #print(image_group) 
        pv_group  = image_group.create_group('pvdata')
        pv_names  = []
        for pv_name in pv_list:
            pv_names  = pv_names + meme.names.list_pvs(pv_name)
        pv_values = meme.archive.get(pv_names, from_time=timestamp, to_time=timestamp)
        for entry in pv_values:
            label = entry['pvName']
            value = entry['value']['value']['values']
            pv_group.attrs[label] = value 
        #for pv_name in pv_names: #pv_values:
        #    try:
        #        pv_value = meme.names.list_pvs(pv_name,tag=area, sort_by="z")
        #        pv_group.attrs[pv_name] = pv_value['value']['value']['values']
        #        #pv_group.attrs[pv['pvName']] = pv['value']['value']['values']
        #    except:
        #        print(pv_name, 'not available')

        #print(type(pv_values[:]))
        #print(np.shape(pv_values[:][0]))
    vhf.close()

    return           

