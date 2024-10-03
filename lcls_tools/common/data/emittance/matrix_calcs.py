import numpy as np


def propagate_twiss(twiss_init: np.ndarray, rmat: np.ndarray):
    """
    Propagates twiss parameters downstream given a transport rmat.

    Parameters:
        twiss_init: numpy array shape batchshape x 3 x 1
        rmat: numpy array shape batchshape x 2 x 2

    Outputs:
        twiss_final: numpy array shape batchshape x 3 x 1
    """
    twiss_transport = twiss_transport_mat_from_rmat(
        rmat
    )  # result shape (batchshape x 3 x 3)

    twiss_final = twiss_transport @ twiss_init
    # result shape (batchshape x nsteps x 3 x 1)

    return twiss_final


def twiss_transport_mat_from_rmat(rmat: np.ndarray):
    """
    Converts from 2x2 rmats to 3x3 twiss transport matrices.

    Parameters:
        rmat: numpy array shape batchshape x 2 x 2

    Outputs:
        result: numpy array shape batchshape x 3 x 1
    """
    # Converts from 2x2 rmats to 3x3 twiss transport matrices.
    c, s, cp, sp = rmat[..., 0, 0], rmat[..., 0, 1], rmat[..., 1, 0], rmat[..., 1, 1]
    result = np.stack(
        (
            np.stack((c**2, -2 * c * s, s**2), axis=-1),
            np.stack((-c * cp, c * sp + cp * s, -s * sp), axis=-1),
            np.stack((cp**2, -2 * cp * sp, sp**2), axis=-1),
        ),
        axis=-2,
    )  # result shape (*rmat.shape, 3, 3)
    return result


def build_quad_rmat(k: np.ndarray, q_len: float, thin_lens: bool=False):
    """
    Constructs quad rmat transport matrices for a quadrupole of length q_len with geometric focusing strengths
    given by k.

    Parameters:
        k: numpy array containing geometric focusing strengths
        q_len: float specifying quad length in meters
        thin_lens: boolean specifying whether or not to use thin-lens approximation

    Outputs:
        rmat: numpy array of shape (*k.shape, 2, 2) containing rmats corresponding to the
                various focusing strengths given by k
    """

    if not thin_lens:
        sqrt_k = np.sqrt(np.abs(k))

        c = (
            np.cos(sqrt_k * q_len) * (k > 0)
            + np.cosh(sqrt_k * q_len) * (k < 0)
            + np.ones_like(k) * (k == 0)
        )
        s = (
            np.nan_to_num(1.0 / sqrt_k) * np.sin(sqrt_k * q_len) * (k > 0)
            + np.nan_to_num(1.0 / sqrt_k) * np.sinh(sqrt_k * q_len) * (k < 0)
            + q_len * np.ones_like(k) * (k == 0)
        )
        cp = (
            -sqrt_k * np.sin(sqrt_k * q_len) * (k > 0)
            + sqrt_k * np.sinh(sqrt_k * q_len) * (k < 0)
            + np.zeros_like(k) * (k == 0)
        )
        sp = (
            np.cos(sqrt_k * q_len) * (k > 0)
            + np.cosh(sqrt_k * q_len) * (k < 0)
            + np.ones_like(k) * (k == 0)
        )

    else:
        c, s, cp, sp = (np.ones_like(k), np.zeros_like(k), -k * q_len, np.ones_like(k))

    rmat = np.stack(
        (
            np.stack((c, s), axis=-1),
            np.stack((cp, sp), axis=-1),
        ),
        axis=-2,
    )  # final shape (*k.shape, 2, 2)

    return rmat
