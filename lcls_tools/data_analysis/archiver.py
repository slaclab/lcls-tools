from datetime import datetime, timedelta
#import sys
#sys.path.append('../image_processing')
#from mat_image import MatImage as MI

#import meme.archive 
#import meme.names 

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

def get_iso_time(pytime):
    """Return iso time from pyton datetime"""
    return pytime.isoformat()

