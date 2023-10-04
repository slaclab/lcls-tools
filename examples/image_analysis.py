import sys  # NEEDS FIX

sys.path.append("../lcls_tools/image_processing")

import numpy as np
import matplotlib.pyplot as plt
from mat_image import MatImage as MI

filename = "ProfMon-CAMR_LGUN_950-2019-08-15-171000.mat"
matlab_file = MI()
matlab_file.load_mat_image(filename)

# List of functions in image class:
# ['__class__', '__delattr__', '__dict__', '__doc__', '__format__', '__getattribute__', '__hash__', '__init__', '__module__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__weakref__', '_back', '_bit_depth', '_cam_name', '_center_x', '_center_y', '_filt_od', '_filt_stat', '_image_attn', '_image_object', '_is_raw', '_mat_file', '_n_col', '_n_row', '_orient_x', '_orient_y', '_pulse_id', '_res', '_roi_x', '_roi_x_n', '_roi_y', '_roi_y_n', '_ts', '_unpack_mat_data', 'back', 'bit_depth', 'camera_name', 'center_x', 'center_y', 'columns', 'filt_od', 'filt_stat', 'image', 'image_as_list', 'image_attn', 'image_object', 'is_raw', 'load_mat_image', 'mat_file', 'orientation_x', 'orientation_y', 'pulse_id', 'resolution', 'roi_x', 'roi_x_n', 'roi_y', 'roi_y_n', 'rows', 'show_image', 'timestamp']

# in microns per pixels (um/px)
resolution = matlab_file.resolution
print("resolution in um/px:", resolution)

plt.imshow(matlab_file.image)
plt.xlabel("microns")
plt.show()
