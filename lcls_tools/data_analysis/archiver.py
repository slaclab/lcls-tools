from datetime import datetime, timedelta
#import sys
#sys.path.append('../image_processing')
#from mat_image import MatImage as MI

import meme.archive 
import meme.names 

def datenum_to_datetime(datenum):
    """Convert Matlab datenum into Python datetime.

    :param datenum: Date in datenum format
    :return:        Datetime object corresponding to datenum.
    https://gist.github.com/victorkristof/b9d794fe1ed12e708b9d
    """
    days = datenum % 1
    return datetime.fromordinal(int(datenum)) \
           + timedelta(days=days) \
           - timedelta(days=366)

#def get_matimage_timestamp(filename):
#    """Get timestamp from matlab image
#    
#    filename: matlab image file
#    returns:  python datetime  
#    """
#    matimage = MI()
#    matimage.load_mat_image(filename)
#    return datenum_to_datetime(matimage.timestamp)
#    

def get_pvdata(devices,area, timestamp): 
    pv_names  = meme.names.list_pvs(devices,tag=area, sort_by="z")
    pv_values = meme.archive.get(pv_names, from_time=timestamp, to_time=timestamp)
    return pv_values

def get_iso_time(pytime):
    """Return iso time from pyton datetime"""
    return pytime.isoformat()

def add_mat_image_attributes(mi,h5):
    """Save mat image attrs to h5 dataset or group"""
    for attr, value in mi.__dict__.items():
        try:
            h5.attrs[attr[1:]] = value
        except:
            print('Did not save', attr, 'to attributes.')
    return None
