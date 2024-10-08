import numpy as np


class Image(object):
    def __init__(self, image):
        if not isinstance(image, np.ndarray):
            raise TypeError("input must be ndarray")
        self._image = image

    @property
    def image(self):
        """Image, typically numpy array or 2darray"""
        return self._image

    @property
    def std(self):
        """Std Deviation"""
        return self._image.std()

    @property
    def mean(self):
        """Mean"""
        return self._image.mean()

    @property
    def n_col(self):
        """Number of columns or x size"""
        return self._image.shape[0]

    @property
    def n_row(self):
        """Number of rows or y size"""
        return self._image.shape[1]

    @property
    def shape(self):
        """Returns shape (cols, rows)"""
        return self._image.shape

    @property
    def min(self):
        """Returns min of ndarray"""
        return self._image.min()

    @property
    def max(self):
        """Returns max of ndarray"""
        return self._image.max()
