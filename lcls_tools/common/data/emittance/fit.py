import numpy as np
from scipy.optimize import minimize
import importlib.util
from matrix_calcs import propagate_twiss, twiss_transport_mat_from_rmat, build_quad_rmat
from lcls_tools.common.data.model_general_calcs import bmag_func

def compute_emit_bmag(
    k: np.ndarray,
    beamsize_squared: np.ndarray,
    q_len: float,
    rmat: np.ndarray,
    twiss_design: np.ndarray = None,
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
    # construct the A matrix from eq. (3.2) & (3.3) of source paper
    quad_rmat = build_quad_rmat(
        k, q_len, thin_lens=thin_lens
    )  # result shape (batchshape x nsteps x 2 x 2)
    total_rmat = np.expand_dims(rmat, -3) @ quad_rmat
    # result shape (batchshape x nsteps x 2 x 2)

    # prepare the A matrix
    r11, r12 = total_rmat[..., 0, 0], total_rmat[..., 0, 1]
    amat = np.stack((r11**2, 2.0 * r11 * r12, r12**2), axis=-1)
    # amat result (batchshape x nsteps x 3)

    beamsize_squared = np.expand_dims(beamsize_squared, -1)

    def beam_matrix_tuple(params):
        # converts fit parameters to beam matrix parameters and packages for stacking
        return (
            params[..., 0, :] ** 2,  # lamba1^2 = sig11
            params[..., 0, :]
            * params[..., 1, :]
            * params[..., 2, :],  # lambda1*lambda2*c = sig12
            params[..., 1, :] ** 2, # lamba2^2 = sig22
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
            params = torch.reshape(params, [*beamsize_squared.shape[:-2], 3, 1])
            sig = torch.stack(beam_matrix_tuple(params), dim=-2)
            # sig should now be shape batchshape x 3 x 1
            total_squared_error = (amat @ sig - beamsize_squared).pow(2).sum()
            return total_squared_error

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
            params = np.reshape(params, [*beamsize_squared.shape[:-2], 3, 1])
            sig = np.stack(beam_matrix_tuple(params), axis=-2)
            # sig should now be shape batchshape x 3 x 1
            total_squared_error = np.sum((amat @ sig - beamsize_squared) ** 2)
            return total_squared_error

        loss_jacobian = None

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
    res = minimize(loss, init_params, jac=loss_jacobian, bounds=bounds, options=options)

    fit_params = res.x
    fit_params = np.reshape(fit_params, [*beamsize_squared.shape[:-2], 3, 1])

    # convert fit params back to beam matrix params
    beam_matrix = np.stack(beam_matrix_tuple(fit_params), axis=-2)
    # result shape (batchshape x 3 x 1) containing column vectors of [sig11, sig12, sig22]

    emit = np.sqrt(
        beam_matrix[..., 0, 0] * beam_matrix[..., 2, 0] - beam_matrix[..., 1, 0] ** 2
    )  # result shape (batchshape)

    if twiss_design is not None:
        beta_design, alpha_design = twiss_design[...,0:1], twiss_design[...,1:]
        # results shape batchshape x 1 (last dim will be broadcast)

        # get twiss at measurement quad from beam_matrix
        twiss_upstream = np.stack((beam_matrix[...,0,0:], 
                                   -1*beam_matrix[...,1,0:], 
                                   beam_matrix[...,2,0:]
                                  ), axis=-2) / np.expand_dims(emit, axis=(-1,-2))
        twiss = propagate_twiss(np.expand_dims(twiss_upstream, axis=-3), total_rmat)
        # result shape (batchshape x nsteps x 3 x 1)
        beta, alpha = twiss[...,0,0], twiss[...,1,0]
        # shapes batchshape x nsteps

        bmag = bmag_func(beta, alpha, beta_design, alpha_design) # result batchshape
    else:
        bmag = None

    return emit, bmag, beam_matrix

# def bmag_func(bb, ab, bl, al):
#     """Calculates the BMAG miss match parameter.  bb and ab are the modeled
#     beta and alpha functions at a given element and bl and al are the
#     reference (most of the time desing) values """
#     return 1 / 2 * (bl / bb + bb / bl + bb * bl * (ab / bb - al / bl) ** 2)

def normalize_emittance(emit, energy):
    gamma = energy / (
        0.511e-3
    )  # beam energy (GeV) divided by electron rest energy (GeV)
    beta = 1.0 - 1.0 / (2 * gamma**2)
    emit_n = gamma * beta * emit
    return emit_n  # the normalized emittance
