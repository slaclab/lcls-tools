import numpy as np
from beam_dynamics import reconstruct_beam_matrix, compute_bmag
from numpy import ndarray


def compute_emit_bmag(
    k: ndarray,
    beamsize_squared: ndarray,
    q_len: float,
    rmat: ndarray,
    beta0: float = None,
    alpha0: float = None,
    thin_lens: bool = False,
    maxiter: int = None,
):
    """
    Computes the emittance(s) corresponding to a set of quadrupole measurement scans
    using nonlinear fitting of beam matrix parameters to guarantee physically valid results.

    Parameters:
        k: numpy array of shape (n_steps_quad_scan,) or (batchshape x n_steps_quad_scan)
            representing the measurement quad geometric focusing strengths in [m^-2]
            used in the emittance scan(s)

        beamsize_squared: numpy array of shape (batchshape x n_steps_quad_scan),
                representing the mean-square beamsize outputs in [mm^2] of the emittance scan(s)
                with inputs given by k

        q_len: float defining the (longitudinal) quadrupole length or "thickness" in [m]

        rmat: numpy array shape (2x2) or (batchshape x 2 x 2)
                containing the 2x2 R matrices describing the transport from the end of the
                measurement quad to the observation screen.

        beta0: float or numpy array shape (batchshape x 1) designating the design beta twiss parameter at the screen

        alpha0: float or numpy array shape (batchshape x 1) designating the design alpha twiss parameter at the screen

        thin_lens: boolean specifying whether or not to use thin lens approximation for measurement quad.

        max_iter: maximum number of iterations to perform in nonlinear fitting (minimization algorithm)

    Returns:
        emit: numpy array shape (batchshape) containing the geometric emittance fit results for each scan in mm-mrad
        bmag: numpy array shape (batchshape x n_steps) containing the bmag corresponding to each point in each scan
        beam_matrix: numpy array shape (batchshape x 3 x 1) containing column vectors of [sig11, sig12, sig22]
                     where sig11, sig12, sig22 are the beam matrix parameters

    SOURCE PAPER: http://www-library.desy.de/preparch/desy/thesis/desy-thesis-05-014.pdf
    """
    # get upstream beam_matrix and transport matrices for each step in the quad scan
    beam_matrix, total_rmat = reconstruct_beam_matrix(
        k, beamsize_squared, q_len, rmat, thin_lens=thin_lens, maxiter=maxiter
    )
    emit = np.sqrt(
        beam_matrix[..., 0, 0] * beam_matrix[..., 2, 0] - beam_matrix[..., 1, 0] ** 2
    )  # result shape (batchshape)

    if (beta0 is not None) and (alpha0 is not None):
        bmag = compute_bmag(beam_matrix, total_rmat, beta0, alpha0)  # result batchshape
    elif beta0 is not None or alpha0 is not None:
        print(
            "WARNING: beta0 and alpha0 must both be specified to compute bmag. Skipping bmag calc."
        )
        bmag = None
    else:
        bmag = None

    return emit, bmag, beam_matrix


def normalize_emittance(emit, energy):
    gamma = energy / (
        0.511e-3
    )  # beam energy (GeV) divided by electron rest energy (GeV)
    beta = 1.0 - 1.0 / (2 * gamma**2)
    emit_n = gamma * beta * emit
    return emit_n  # the normalized emittance
