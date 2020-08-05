# Data Analysis
---------------

## Archiver
The data analysis package consists of the archiver utility and its associated 
test. The goal of the data Archiver utility is to provide functions 
that assist in converting data into python objects and storing 
that data in H5 files. This utility is found 
[here](https://github.com/slaclab/lcls-tools/blob/python3devel/lcls_tools/data_analysis/archiver.py).

Initializations and imports 
```
>>> from datetime import datetime, timedelta
>>> import meme.archive 
>>> import meme.names 
>>> from mat_image import MatImage as MI
mi = MI() 
```

The following explains how the functions in the Archiver are used.

```
>>> arch.datenum_to_datetime(datenum)
Converts Matlab datenum into Python datetime. This is helpful to analyze
the data.

>>> arch.get_iso_time(pytime)
This will format iso time from python datetime.

>>> arch.save_mat_image_attributes(mi,h5)
Attempts to save .mat image attributes to an h5 file.

>>> arch.save_image_to_h5(mi, h5group)
Saves .mat image and meta data to h5 file. 
The data is seperated by timestamp, which 
is converted from matlab datnum to python datetime.
mi      -- matlab image object 
h5group -- h5 group or dataset to save attributes

>>> arch.save_pvdata_to_h5
This function will save pvdata at specific isotime to h5 file.
```
The utility is currently under development. 


## Archiver test
This utility will test the functions in the Archiver package 
to ensure that the package will complete it's intended purpose. 
The full test can be found [here](https://github.com/slaclab/lcls-tools/blob/python3devel/lcls_tools/data_analysis/archiver_test.py).






