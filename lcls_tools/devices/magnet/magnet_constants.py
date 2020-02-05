#!/usr/local/lcls/package/python/current/bin/python

CTRL = [
    'Ready', 
    'TRIM', 
    'PERTURB',
    'BCON_TO_BDES', 
    'SAVE_BDES', 
    'LOAD_BDES', 
    'UNDO_BDES', 
    'DAC_ZERO', 
    'CALIB', 
    'STDZ', 
    'RESET'
]

def create_mag_dict(base, tol, length):
    mag_dict = {
        'bctrl': base + ':BCTRL',
        'bact': base + ':BACT',
        'bdes': base + ':BDES',
        'bcon': base + ':BCON',
        'ctrl': base + ':CTRL',
        'tol': tol,
        'length': length
    }
    
    return mag_dict

MAGNETS = {
    #'SOL1B': create_mag_dict('SOLN:GUNB:212', 0.002, 0.1342),
    'SOL2B': create_mag_dict('SOLN:GUNB:823', 0.002, 0.135),
    'SOL1B': create_mag_dict('QUAD:LI22:201', 0.05, 0.1)
}
