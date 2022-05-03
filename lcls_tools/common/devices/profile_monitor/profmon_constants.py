# There are likely redundancy issues and can be
# optimized further, this is just a POC.  A Database would be nice
# to reference as this is Database schema

# TODO: Make this a .yaml file for cleanliness and
# cross language reference if needed

# Error Strings
ALREADY_INSERTED = 'Profile Monitor is already inserted'
ALREADY_EXTRACTED = 'Profile Monitor is already extracted'

# Completed Action Strings
INSERTED = 'Profile Monitor has been inserted'
EXTRACTED = 'Profile Monitor has been extracted'

# Profile Monitor State
IN = 'IN'
OUT = 'OUT'

############# LCLS Profile Monitor ###########

def create_profmon_dict(base):
    profmon_dict = {
        'set': base + ':PNEUMATIC',
        'get': base + ':TGT_STS',
        'image': base + ':IMAGE',
        'res': base + ':RESOLUTION',
        'xsize': base + ':N_OF_COL',
        'ysize': base + ':N_OF_ROW',
        'rate': base + ':FRAME_RATE'
        }
    
    return profmon_dict

# Because why would we ever be consistent in naming conventions
def create_profmon2_dict(base):
    profmon_dict = {
        'set': base + ':PNEUMATIC',
        'get': base + ':TGT_STS',
        'image': base + ':Image:ArrayData',
        'res': base + ':RESOLUTION',
        'xsize': base + ':ArraySizeX_RBV',
        'ysize': base + ':ArraySizeY_RBV',
        'rate': base + ':FRAME_RATE'
        }

    return profmon_dict

YAG01 = create_profmon_dict('YAGS:IN20:211')
OTR02 = create_profmon_dict('OTRS:IN20:571')
YAG01B = create_profmon2_dict('YAGS:GUNB:753')

# Dict of Profile Monitors
PROFS = {
    'YAG01B': YAG01B,
    'YAG01': YAG01,
    'OTR02': OTR02
}
