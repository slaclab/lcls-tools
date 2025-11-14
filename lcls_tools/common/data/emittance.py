import numpy as np
from scipy.optimize import minimize
import importlib.util
from lcls_tools.common.data.model_general_calcs import (
    bmag_func,
    propagate_twiss,
)


def compute_emit_bmag(
    beamsize_squared: np.ndarray,
    rmat: np.ndarray,
    twiss_lattice: np.ndarray = None,
    maxiter: int = None,
):
    """
    Computes the emittance(s) from a set of beamsize measurements and their corresponding
    transport matrices (rmats).
    Must provide beamsize measurements corresponding to at least 3 unique rmats (e.g. quad scan
    with minimum of 3 steps, or 3-wire scan).
    Uses nonlinear fitting of beam matrix parameters to guarantee physically valid results.


    Parameters
    ----------
    beamsize_squared : numpy.ndarray
        Array of shape (batchshape x n_measurements x 1), representing the mean-square
        beamsize outputs in [mm^2].

    rmat : numpy.ndarray
        Array of shape (n_measurements x 2 x 2) or (batchshape x n_measurements x 2 x 2)
        containing the 2x2 R matrices describing the transport from a common upstream
        point in the beamline to the locations at which each beamsize was observed.

    twiss_lattice : numpy.ndarray, optional
        Array of shape (batchshape x n_measurements x 2) designating the design (beta, alpha)
        twiss parameters at each measurement location.
        Note that it is also possible to pass an array of shape (batchshape x 1 x 2),
        which will result in broadcasting a single set of design twiss parameters
        to each measurement in the respective batch for the calculation of Bmag
        (useful for quad scans).

    maxiter : int, optional
        Maximum number of iterations to perform in nonlinear fitting (minimization algorithm).

    Returns
    -------
    dict
        Dictionary containing the following keys:
        - 'emittance': numpy.ndarray of shape (batchshape x 1) containing the geometric emittance
          fit results for each scan in mm-mrad.
        - 'bmag': numpy.ndarray of shape (batchshape x n_steps) containing the bmag corresponding
          to each point in each scan.
        - 'beam_matrix': numpy.ndarray of shape (batchshape x 3) containing [sig11, sig12, sig22]
          where sig11, sig12, sig22 are the reconstructed beam matrix parameters at the entrance
          of the measurement quad.
        - 'twiss': numpy.ndarray of shape (batchshape x nsteps x 3) containing the
          reconstructed twiss parameters at the measurement screen for each step in each quad scan.

    References
    ----------
    SOURCE PAPER: http://www-library.desy.de/preparch/desy/thesis/desy-thesis-05-014.pdf
    """
    # return variable dictionary
    rv = {}

    # prepare the A matrix from eq. (3.2) & (3.3) of source paper
    r11, r12 = rmat[..., 0, 0], rmat[..., 0, 1]
    amat = np.stack((r11**2, 2.0 * r11 * r12, r12**2), axis=-1)
    # amat result (batchshape x nsteps x 3)

    def beam_matrix_tuple(params):
        """
        converts fit parameters (batchshape x 3), containing [lambda1, lambda2, c],
        to tuple of beam matrix parameters (sig11, sig12, sig22) where each
        element in the tuple is shape batchshape, for stacking.
        """
        return (
            params[..., 0] ** 2,  # lamba1^2 = sig11
            params[..., 0]
            * params[..., 1]
            * params[..., 2],  # lambda1*lambda2*c = sig12
            params[..., 1] ** 2,  # lamba2^2 = sig22
        )

    # check if torch is available to be imported
    torch_spec = importlib.util.find_spec("torch")
    torch_found = torch_spec is not None
    if torch_found:
        # define loss function in torch and use autograd to get its jacobian
        import torch

        amat = torch.from_numpy(amat)
        beamsize_squared = torch.from_numpy(beamsize_squared)

        def loss_torch(params):
            params = torch.reshape(params, [*beamsize_squared.shape[:-2], 3])
            sig = torch.stack(beam_matrix_tuple(params), dim=-1).unsqueeze(-1)
            # sig should now be shape batchshape x 3 x 1 (column vectors)
            total_abs_error = (
                (torch.sqrt(amat @ sig) - torch.sqrt(beamsize_squared)).abs().nansum()
            )
            return total_abs_error

        def loss_jacobian(params):
            return (
                torch.autograd.functional.jacobian(loss_torch, torch.from_numpy(params))
                .detach()
                .numpy()
            )

        def loss(params):
            return loss_torch(torch.from_numpy(params)).detach().numpy()

    else:
        # define loss function in numpy without jacobian
        def loss(params):
            params = np.reshape(params, [*beamsize_squared.shape[:-2], 3])
            sig = np.expand_dims(np.stack(beam_matrix_tuple(params), axis=-1), axis=-1)
            # sig should now be shape batchshape x 3 x 1 (column vectors)
            total_abs_error = np.nansum(
                np.abs(np.sqrt(amat @ sig) - np.sqrt(beamsize_squared))
            )
            return total_abs_error

        loss_jacobian = None

    # for numerical stability
    eps = 1.0e-6

    # get initial guesses for lambda1, lambda2, c, from pseudo-inverse method
    init_beam_matrix = np.linalg.pinv(np.array(amat)) @ np.array(beamsize_squared)
    lambda1 = np.sqrt(init_beam_matrix[..., 0, 0].clip(min=eps))
    lambda2 = np.sqrt(init_beam_matrix[..., 2, 0].clip(min=eps))
    c = (init_beam_matrix[..., 1, 0] / (lambda1 * lambda2)).clip(
        min=-1 + eps, max=1 - eps
    )
    init_params = np.stack((lambda1, lambda2, c), axis=-1).flatten()

    # define bounds (only c parameter is bounded, between -1 and 1)
    bounds = np.tile(
        np.array([[None, None], [None, None], [-1.0 + eps, 1.0 - eps]]),
        (np.prod(beamsize_squared.shape[:-2]), 1),
    )
    if maxiter is not None:
        options = {"maxiter": maxiter}
    else:
        options = None

    # minimize loss
    res = minimize(
        loss,
        init_params,
        jac=loss_jacobian,
        bounds=bounds,
        options=options,
    )

    # get the fit result and reshape to (batchshape x 3)
    fit_params = np.reshape(res.x, [*beamsize_squared.shape[:-2], 3])

    # convert fit params back to beam matrix params
    rv["beam_matrix"] = np.stack(beam_matrix_tuple(fit_params), axis=-1)
    # result shape (batchshape x 3) containing [sig11, sig12, sig22]

    rv["emittance"] = np.sqrt(
        rv["beam_matrix"][..., 0:1] * rv["beam_matrix"][..., 2:3]
        - rv["beam_matrix"][..., 1:2] ** 2
    )
    # result shape (batchshape x 1)

    # get twiss at upstream origin from beam_matrix
    def _twiss_upstream(b_matrix):
        return np.expand_dims(
            np.stack(
                (
                    b_matrix[..., 0],
                    -1 * b_matrix[..., 1],
                    b_matrix[..., 2],
                ),
                axis=-1,
            )
            / rv["emittance"],
            axis=-2,
        )

    # propagate twiss params to screen (expand_dims for broadcasting)
    rv["twiss"] = propagate_twiss(_twiss_upstream(rv["beam_matrix"]), rmat)
    # result shape (batchshape x nsteps x 3)
    beta, alpha = (
        rv["twiss"][..., 0],
        rv["twiss"][..., 1],
    )
    # shapes batchshape x nsteps

    # compute bmag if twiss_lattice is provided
    if twiss_lattice is not None:
        beta_design, alpha_design = (
            twiss_lattice[..., 0],
            twiss_lattice[..., 1],
        )
        # shape batchshape x nsteps x 1 (multi-device) or batchshape x 1 (quad scan)

        # result batchshape x 3 containing [beta, alpha, gamma]
        rv["bmag"] = bmag_func(
            beta, alpha, beta_design, alpha_design
        )  # result batchshape x nsteps
    else:
        rv["bmag"] = None

    return rv


def normalize_emittance(emit, energy):
    gamma = energy / (
        0.511e-3
    )  # beam energy (GeV) divided by electron rest energy (GeV)
    beta = 1.0 - 1.0 / (2 * gamma**2)
    emit_n = gamma * beta * emit
    return emit_n  # the normalized emittance
