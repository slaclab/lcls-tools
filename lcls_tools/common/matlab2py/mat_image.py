from numpy import ndarray
import scipy.io as sio
import matplotlib.pyplot as plt
import os

from lcls_tools.common.image import Image


class MatImage(object):
    """.mat image object from typical LCLS .mat file (R2012-2020a)"""

    def __init__(self):
        self._mat_file = None
        self._cam_name = None
        self._image_object = None
        self._roi_x_n = None
        self._roi_y_n = None
        self._ts = None
        self._pulse_id = None
        self._n_col = None
        self._n_row = None
        self._bit_depth = None
        self._res = None
        self._roi_x = None
        self._roi_y = None
        self._orient_x = None
        self._orient_y = None
        self._center_x = None
        self._center_y = None
        self._filt_stat = None
        self._filt_od = None
        self._image_attn = None
        self._is_raw = None
        self._back = None

    @property
    def mat_file(self):
        return self._mat_file

    @property
    def camera_name(self):
        return self._cam_name

    @property
    def image_object(self):
        return self._image_object

    @property
    def image(self):
        if self._image_object:
            return self._image_object.image

    @property
    def image_as_list(self):
        if not self._image_object:
            return []

        return ndarray.tolist(
            self._image_object.image,
        )

    @property
    def roi_x_n(self):
        return self._roi_x_n

    @property
    def roi_y_n(self):
        return self._roi_y_n

    @property
    def timestamp(self):
        """epoch time"""
        return self._ts

    @property
    def pulse_id(self):
        return self._pulse_id

    @property
    def columns(self):
        return self._n_col

    @property
    def rows(self):
        return self._n_row

    @property
    def bit_depth(self):
        return self._bit_depth

    @property
    def resolution(self):
        return self._res

    @property
    def roi_x(self):
        return self._roi_x

    @property
    def roi_y(self):
        return self._roi_y

    @property
    def orientation_x(self):
        return self._orient_x

    @property
    def orientation_y(self):
        return self._orient_y

    @property
    def center_x(self):
        return self._center_x

    @property
    def center_y(self):
        return self._center_y

    @property
    def filt_stat(self):
        return self._filt_stat

    @property
    def filt_od(self):
        return self._filt_od

    @property
    def image_attn(self):
        return self._image_attn

    @property
    def is_raw(self):
        return self._is_raw

    @property
    def back(self):
        return self._back

    def _unpack_mat_data(self, mat_file):
        """TODO: Try to generalize this."""
        file_contents = sio.loadmat(mat_file)
        data = file_contents["data"][0][0]
        self._mat_file = mat_file
        self._cam_name = str(data[0][0])
        self._image_object = Image(data[1])  # Create object
        self._roi_x_n = data[2][0][0]
        self._roi_y_n = data[3][0][0]
        self._ts = data[4][0][0]
        self._pulse_id = data[5][0][0]
        self._n_col = data[6][0][0]
        self._n_row = data[7][0][0]
        self._bit_depth = data[8][0][0]
        self._res = data[9][0][0]
        self._roi_x = data[10][0][0]
        self._roi_y = data[11][0][0]
        self._orient_x = data[12][0][0]
        self._orient_y = data[13][0][0]
        self._center_x = data[14][0][0]
        self._center_y = data[15][0][0]
        self._filt_stat = data[16][0]
        self._filt_od = data[17][0]
        self._image_attn = data[18][0][0]
        self._is_raw = data[19][0][0]
        self._back = data[20][0][0]

    def load_mat_image(self, mat_file):
        """Converting .mat image data structure to an object"""
        if not os.path.isfile(mat_file):
            raise FileNotFoundError(f"Could not find {mat_file}")
        try:
            self._unpack_mat_data(mat_file)
        except Exception as e:
            print("Error loading mat file {0}: {1}".format(mat_file, e))

    def show_image(self):
        if self._image_object is None:
            raise AttributeError(
                "image is None. please call load_mat_image before trying to show image."
            )

        plt.imshow(self._image_object.image, aspect="auto")
        plt.show(block=False)
