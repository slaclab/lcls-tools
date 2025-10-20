from typing import Optional, Tuple, Callable

import scipy
import numpy as np
from pydantic import ConfigDict
from scipy.ndimage import median_filter
from skimage.measure import block_reduce
from skimage.filters import threshold_triangle
import lcls_tools


class ImageProcessor(lcls_tools.common.BaseModel):
    """
    Image Processing class that allows for background subtraction and roi cropping
    ------------------------
    Arguments:
    background_image: np.ndarray (optional image that will be used in
        background subtraction if passed),
    pool_size : int, optional
        Size of the pooling window. If None, no pooling is applied.
    median_filter_size : int, optional
        Size of the median filter. If None, no median filter is applied.
    threshold : float, optional
        Threshold to apply before filtering. If None, calculated via triangle method.
    threshold_multiplier : float, optional
        Multiplier for the threshold value. Default is 1.0.
    n_stds : int, optional
        Number of standard deviations for cropping. Default is 8.
    center : bool, optional
        If True, center images using the image fitter. Default is True.
    crop : bool, optional
        If True, crop images using fitted centroid and RMS size. Default is True.
    ------------------------
    Methods:
    subtract_background: takes a raw image and does pixel intensity subtraction
    process: takes raw image and calls subtract_background then processes the images
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    background_image: Optional[np.ndarray] = None
    pool_size: Optional[int] = (None,)
    median_filter_size: Optional[int] = (None,)
    threshold: Optional[float] = (None,)
    threshold_multiplier: float = (1.0,)
    n_stds: int = (8,)
    center: bool = (True,)
    crop: bool = (True,)

    def subtract_background(self, raw_image: np.ndarray) -> np.ndarray:
        """Subtract background pixel intensity from a raw image"""
        if self.background_image is not None:
            image = raw_image - self.background_image
        else:
            image = raw_image - self.threshold

        # clip images to make sure values are positive
        return np.clip(image, 0, None)

    def process(self, raw_images: np.ndarray) -> np.ndarray:
        return process_images(
            self.subtract_background(raw_images),
            pool_size=self.pool_size,
            median_filter_size=self.median_filter_size,
            threshold=self.threshold,
            threshold_multiplier=self.threshold_multiplier,
            n_stds=self.n_stds,
            center=self.center,
            crop=self.crop,
        )


def compute_blob_stats(image):
    """
    Compute the RMS size and centroid of a blob in a 2D image using intensity-weighted averages.

    Parameters
    ----------
    image : np.ndarray
        2D array representing the image. Shape should be (height (y size), width (x size)).

    Returns
    -------
    centroid : np.ndarray
        Array containing the centroid coordinates (x_center, y_center).
    rms_size : np.ndarray
        Array containing the RMS size along (x, y) axes.
    """
    if image.ndim != 2:
        raise ValueError("Input image must be a 2D array")

    # Get coordinate grids
    y_indices, x_indices = np.indices(image.shape)

    # Flatten everything
    x = x_indices.ravel()
    y = y_indices.ravel()
    weights = image.ravel()

    # Total intensity
    total_weight = np.sum(weights)
    if total_weight == 0:
        raise ValueError(
            "Total image intensity is zero — can't compute centroid or RMS size."
        )

    # Weighted centroid
    x_center = np.sum(x * weights) / total_weight
    y_center = np.sum(y * weights) / total_weight

    # Weighted RMS size
    x_rms = np.sqrt(np.sum(weights * (x - x_center) ** 2) / total_weight)
    y_rms = np.sqrt(np.sum(weights * (y - y_center) ** 2) / total_weight)

    return np.array((x_center, y_center)), np.array((x_rms, y_rms))


def calc_image_centroids(
    images: np.ndarray, image_fitter: Callable = compute_blob_stats
) -> np.ndarray:
    """
    Calculate centroids for a batch of images using the provided image_fitter function.

    Parameters
    ----------
    images : np.ndarray
        Batch of images with shape (..., height (y size), width (x size)).
    image_fitter : Callable, optional
        Function that returns (centroid, rms) for a single image.

    Returns
    -------
    np.ndarray
        Array of centroids with shape (..., 2), where the last dimension is (x, y) coordinates.
    """

    batch_shape = images.shape[:-2]
    flattened_images = images.reshape((-1,) + images.shape[-2:])
    flattened_centroids = np.zeros((flattened_images.shape[0], 2))

    for i in range(flattened_images.shape[0]):
        centroid, _ = image_fitter(flattened_images[i])
        flattened_centroids[i] = centroid

    return flattened_centroids.reshape(batch_shape + (2,))


def center_images(
    images: np.ndarray,
    image_centroids: np.ndarray,
) -> np.ndarray:
    """
    Centers a batch of images based on provided centroid coordinates.

    Each image in the batch is shifted such that its centroid aligns with the center of the image.

    Parameters
    ----------
    images : np.ndarray
        Batch of images with shape (..., height (y size), width (x size)).
    image_centroids : np.ndarray
        Array of centroid coordinates for each image, shape (..., 2).

    Returns
    -------
    np.ndarray
        Batch of centered images with the same shape as the input.
    """

    center_location = np.array(images.shape[-2:]) // 2
    center_location = center_location[::-1]

    # Flatten batch dimensions
    flattened_images = images.reshape((-1,) + images.shape[-2:])
    flattened_centroids = image_centroids.reshape((flattened_images.shape[0], 2))
    centered_images = np.zeros_like(flattened_images)

    for i in range(flattened_images.shape[0]):
        # Shift the images to center them
        centered_images[i] = scipy.ndimage.shift(
            flattened_images[i],
            -(flattened_centroids[i] - center_location)[::-1],
            order=1,  # Linear interpolation to avoid artifacts
        )

    # Reshape back to original shape
    centered_images = centered_images.reshape(images.shape)

    return centered_images


def calc_crop_ranges(
    images,
    n_stds: int = 8,
    image_fitter=compute_blob_stats,
    filter_size: int = 5,
) -> np.ndarray:
    """
    Calculate crop ranges for a batch of images based on the centroid and RMS size of the mean image.

    Parameters
    ----------
    images : np.ndarray
        Batch of images with shape (..., height (y size), width (x size)).
    n_stds : int, optional
        Number of standard deviations (RMS size) to include in the crop range. Default is 8.
    image_fitter : Callable, optional
        Function to compute centroid and RMS size from an image. Default is compute_blob_stats.

    Returns
    -------
    np.ndarray
        Array of shape (2, 2) containing crop ranges for each axis:
        [[start_x, end_x], [start_y, end_y]].
    """

    batch_shape = images.shape[:-2]
    batch_dims = tuple(range(len(batch_shape)))

    test_images = np.copy(images)
    total_image = np.mean(test_images, axis=batch_dims)

    # apply a strong median filter to remove noise
    total_image = median_filter(total_image, size=filter_size)

    # apply a threshold to remove background noise
    threshold = threshold_triangle(total_image)

    total_image[total_image < threshold] = 0

    centroid, rms_size = image_fitter(total_image)
    centroid = centroid[::-1]
    rms_size = rms_size[::-1]

    crop_ranges = np.array(
        [
            (centroid - n_stds * rms_size).astype("int"),
            (centroid + n_stds * rms_size).astype("int"),
        ]
    )
    crop_ranges = crop_ranges.T  # Transpose to match (start_x, end_x), (start_y, end_y)

    return crop_ranges


def crop_images(
    images: np.ndarray,
    crop_ranges: np.ndarray,
) -> np.ndarray:
    """
    Crops a batch of images according to specified crop ranges.

    Parameters
    ----------
    images : np.ndarray
        A batch of images to be cropped. The shape should be (..., height (y_size), width (x_size)).
    crop_ranges : np.ndarray
        An array specifying the crop ranges for x,y. Should be of shape (2, 2),
        where crop_ranges[0] is [start_x, end_x] and crop_ranges[1] is [start_y, end_y].

    Returns
    -------
    np.ndarray
        The cropped images as a numpy array with the same batch dimensions as the input.
    """
    if crop_ranges.shape != (2, 2):
        raise ValueError("crop_ranges must be of shape (2, 2)")

    if images.ndim < 2:
        raise ValueError(
            "images must have at least 2 dimensions (batch, height, width)"
        )

    crop_ranges[0] = np.clip(crop_ranges[0], 0, images.shape[-2])
    crop_ranges[1] = np.clip(crop_ranges[1], 0, images.shape[-1])

    cropped_images = images[
        ...,
        crop_ranges[0][0] : crop_ranges[0][1],
        crop_ranges[1][0] : crop_ranges[1][1],
    ]

    return cropped_images


def pool_images(images: np.ndarray, pool_size) -> np.ndarray:
    """
    Pools (downsamples) the input images by applying mean pooling over non-overlapping blocks.

    Parameters
    ----------
    images : np.ndarray
        Input array of images. The last two dimensions are assumed to be spatial (height, width).
    pool_size : Optional[int], optional
        Size of the pooling window along each spatial dimension. If None, no pooling is applied.

    Returns
    -------
    np.ndarray
        Array of pooled images with reduced spatial dimensions.
    """

    batch_shape = images.shape[:-2]
    block_size = (1,) * len(batch_shape) + (pool_size,) * 2
    pooled_images = block_reduce(images, block_size=block_size, func=np.mean)
    return pooled_images


def process_images(
    images: np.ndarray,
    image_fitter: Callable = compute_blob_stats,
    pool_size: Optional[int] = None,
    median_filter_size: Optional[int] = None,
    threshold: Optional[float] = None,
    threshold_multiplier: float = 1.0,
    n_stds: int = 8,
    center: bool = False,
    crop: bool = False,
    image_centroids: Optional[np.ndarray] = None,
    crop_ranges: Optional[np.ndarray] = None,
) -> Tuple[np.ndarray, Tuple[np.ndarray, np.ndarray]]:
    """
    Process a batch of images for use in GPSR.

    Applies a series of processing steps to a batch of images:
    - Median filtering (optional)
    - Thresholding (using a provided value or the triangle method)
    - Centering (optional, using an image fitter function)
    - Cropping (optional, based on fitted centroid and RMS size)

    Parameters
    ----------
    images : np.ndarray
        Batch of images with shape (..., height (y size), width (x size)).
    image_fitter : Callable, optional
        Function that fits an image and returns (centroid, rms) in pixel coordinates.
    pool_size : int, optional
        Size of the pooling window. If None, no pooling is applied.
    median_filter_size : int, optional
        Size of the median filter. If None, no median filter is applied.
    threshold : float, optional
        Threshold to apply before filtering. If None, calculated via triangle method.
    threshold_multiplier : float, optional
        Multiplier for the threshold value. Default is 1.0.
    n_stds : int, optional
        Number of standard deviations for cropping. Default is 8.
    center : bool, optional
        If True, center images using the image fitter. Default is False.
    crop : bool, optional
        If True, crop images using fitted centroid and RMS size. Default is False.
    image_centroids : np.ndarray, optional
        Precomputed centroids for centering. If None, computed internally.
    crop_ranges : np.ndarray, optional
        Precomputed crop ranges. If None, computed internally.

    Returns
    -------
    np.ndarray
        Processed images
    """

    batch_shape = images.shape[:-2]
    batch_dims = tuple(range(len(batch_shape)))

    # median filter
    if median_filter_size is not None:
        images = median_filter(
            images,
            size=median_filter_size,
            axes=[-2, -1],
        )

    # apply threshold if provided -- otherwise calculate threshold using triangle method
    if threshold is None:
        avg_image = np.mean(images, axis=batch_dims)
        threshold = threshold_triangle(avg_image)
    images = np.clip(images - threshold_multiplier * threshold, 0, None)

    # center the images
    if center:
        if image_centroids is None:
            image_centroids = calc_image_centroids(images, image_fitter=image_fitter)
        centered_images = center_images(images, image_centroids)
    else:
        centered_images = images

    # crop the images
    if crop:
        if crop_ranges is None:
            crop_ranges = calc_crop_ranges(
                centered_images,
                n_stds=n_stds,
                image_fitter=image_fitter,
            )

        cropped_images = crop_images(
            centered_images,
            crop_ranges=crop_ranges,
        )
    else:
        cropped_images = centered_images

    if pool_size is not None:
        pooled_images = pool_images(cropped_images, pool_size=pool_size)
    else:
        pooled_images = cropped_images

    return pooled_images
