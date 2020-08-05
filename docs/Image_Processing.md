# Image Processing Package

The Image Processing package takes an electron beam image .mat file and 
turns it into a python data object. The goal of this package is to analyze
and describe an electron beam image, which allows a glimps into the size 
of the beam and also can be used to calculate the emittance. 

This package contains several utilities that are essential to the image 
processing utility. They are as follows:

* [fit_gaussian.py](https://github.com/slaclab/lcls-tools/blob/master/lcls_tools/image_processing/fit_gaussian.py)
*       This utility reads in a matlab file of xcor data and fits gaussians to it.
* [image.py](https://github.com/slaclab/lcls-tools/blob/master/lcls_tools/image_processing/image.py)
*       Defines the functions that turn the image into a python object.
* [mat_image.py](https://github.com/slaclab/lcls-tools/blob/master/lcls_tools/image_processing/mat_image.py)
*       Creates a .mat image object from a typical LCLS .mat file.  

---------------------------
## Image Processing Utility
The image processing utility has several functions that can be
used to analyze the electron beam images. This utility can be 
found [here](https://github.com/slaclab/lcls-tools/blob/python3devel/lcls_tools/image_processing/image_processing.py).

Initialization and import usage: 

```
>>> Utility imports
Below is a list of the imports required to run the utility:
   import numpy as np
   import scipy.ndimage as snd
   from scipy.optimize import curve_fit
   from scipy import asarray
   import matplotlib.pyplot as plt
   import fit_gaussian as fg
   from time import time
To use the utility, install the package and 
import image_processing.py as ip

```

---------------
## Function Use

The following explains how to use the functions in the utility.

```
>>> ip.fliplr(image)
Flips the image over the vertical axis.

>>> ip.flipup(image)
Flips the image over the horizontal axis.

>>> ip.center_of_mass(image, sigma=5)
Finds the center of mass of the image by calculating the mean the image's 
pixels and adding that to the sigma multiplied to standard deviation of
the image's pixels.

>>> ip.average_image(images)
Finds the average number of images.

>>> ip.shape_image(image, x_size, y_size)
Shapes the size of the image by rewriting the array.

>>> ip.x_projection(image, axis=0, subtract_baseline=true)
Expects an ndarray and returns an x projection. Sums up all the elements in the array at 
axis = 0.

>>> ip.y_projection(image, subtract_baseline=true)
Returns y projection.

>>> ip.gauss_func
Calculates the gaussian function for the image.

>>> ip.gauss_fit
Calculates the best gaussian fit for the image array.
```

Each utility has a test associated with it that is meant to check 
that each function is 

