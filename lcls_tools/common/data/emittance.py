import numpy as np
from scipy.optimize import minimize
import importlib.util
from lcls_tools.common.data.model_general_calcs import (
    bmag_func,
    propagate_twiss,
    build_quad_rmat,
    bdes_to_kmod,
)


def compute_emit_bmag(
    beamsize_squared: np.ndarray,
    rmat: np.ndarray,
    twiss_design: np.ndarray = None,
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
        Array of shape (batchshape x n_measurements), representing the mean-square
        beamsize outputs in [mm^2].

    rmat : numpy.ndarray
        Array of shape (n_measurements x 2 x 2) or (batchshape x n_measurements x 2 x 2)
        containing the 2x2 R matrices describing the transport from a common upstream
        point in the beamline to the locations at which each beamsize was observed.

    twiss_design : numpy.ndarray, optional
        Array of shape (2,) or (batchshape x 2) designating the design (beta, alpha)
        twiss parameters at the screen.

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
        - 'twiss_at_screen': numpy.ndarray of shape (batchshape x nsteps x 3) containing the
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

    beamsize_squared = np.expand_dims(beamsize_squared, -1)

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
                (torch.sqrt(amat @ sig) - torch.sqrt(beamsize_squared))
                .abs()
                .sum()
            )
            return total_abs_error

        def loss_jacobian(params):
            return (
                torch.autograd.functional.jacobian(
                    loss_torch, torch.from_numpy(params)
                )
                .detach()
                .numpy()
            )

        def loss(params):
            return loss_torch(torch.from_numpy(params)).detach().numpy()

    else:
        # define loss function in numpy without jacobian
        def loss(params):
            params = np.reshape(params, [*beamsize_squared.shape[:-2], 3])
            sig = np.expand_dims(
                np.stack(beam_matrix_tuple(params), axis=-1), axis=-1
            )
            # sig should now be shape batchshape x 3 x 1 (column vectors)
            total_abs_error = np.sum(
                np.abs(np.sqrt(amat @ sig) - np.sqrt(beamsize_squared))
            )
            return total_abs_error

        loss_jacobian = None

    # for numerical stability
    eps = 1.0e-6

    # get initial guesses for lambda1, lambda2, c, from pseudo-inverse method
    init_beam_matrix = np.linalg.pinv(np.array(amat)) @ np.array(
        beamsize_squared
    )
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
    rv["twiss_at_screen"] = propagate_twiss(
        _twiss_upstream(rv["beam_matrix"]), rmat
    )
    # result shape (batchshape x nsteps x 3)
    beta, alpha = (
        rv["twiss_at_screen"][..., 0],
        rv["twiss_at_screen"][..., 1],
    )
    # shapes batchshape x nsteps

    # compute bmag if twiss_design is provided
    if twiss_design is not None:
        beta_design, alpha_design = (
            twiss_design[..., 0:1],
            twiss_design[..., 1:2],
        )
        # results shape batchshape x 1

        # result batchshape x 3 containing [beta, alpha, gamma]
        rv["bmag"] = bmag_func(
            beta, alpha, beta_design, alpha_design
        )  # result batchshape x nsteps
    else:
        rv["bmag"] = None

    return rv


def compute_emit_bmag_quad_scan(
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

    Parameters
    ----------
    k : numpy.ndarray
        Array of shape (n_steps_quad_scan,) or (batchshape x n_steps_quad_scan)
        representing the measurement quad geometric focusing strengths in [m^-2]
        used in the emittance scan(s).

    beamsize_squared : numpy.ndarray
        Array of shape (batchshape x n_steps_quad_scan), representing the mean-square
        beamsize outputs in [mm^2] of the emittance scan(s) with inputs given by k.

    q_len : float
        The (longitudinal) quadrupole length or "thickness" in [m].

    rmat : numpy.ndarray
        Array of shape (2x2) or (batchshape x 2 x 2) containing the 2x2 R matrices
        describing the transport from the end of the measurement quad to the observation screen.

    twiss_design : numpy.ndarray, optional
        Array of shape (2,) or (batchshape x 2) designating the design (beta, alpha)
        twiss parameters at the screen.

    thin_lens : bool, optional
        Specifies whether or not to use thin lens approximation for measurement quad.

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
        - 'twiss_at_screen': numpy.ndarray of shape (batchshape x nsteps x 3) containing the
          reconstructed twiss parameters at the measurement screen for each step in each quad scan.
    """
    # calculate and add the measurement quad transport to the rmats
    quad_rmat = build_quad_rmat(
        k, q_len, thin_lens=thin_lens
    )  # result shape (batchshape x nsteps x 2 x 2)
    total_rmat = np.expand_dims(rmat, -3) @ quad_rmat
    # result shape (batchshape x nsteps x 2 x 2)

    # compute emittance
    rv = compute_emit_bmag(beamsize_squared, total_rmat, twiss_design, maxiter)

    return rv


def preprocess_inputs(
    quad_vals: list, beamsizes: list, energy: float, q_len: float
):
    """
    Preprocesses the inputs for analyze_quad_scan.

    Parameters
    ----------
    quad_vals : list
        A list of two arrays containing the quadrupole values in kG for x and y respectively.
    beamsizes : dict
        A list of two arrays containing the beam sizes in meters for x and y respectively.
    energy : float
        The energy of the beam in eV.
    q_len : float
        The effective length of the quadrupole in meters.

    Returns
    -------
    tuple
        A tuple containing the list of kmod values and the list of beam sizes squared.
    """
    kmod_list = []
    beamsizes_squared_list = []

    for i in range(2):
        # Get rid of nans
        idx = ~np.isnan(beamsizes[i])
        q = quad_vals[i][idx]
        b = beamsizes[i][idx]

        # Beamsizes to mm squared
        beamsizes_squared_list.append((b * 1e3) ** 2)

        # Quad values to kmod
        kmod = bdes_to_kmod(energy, q_len, q)

        # Negate for y
        if i == 1:
            kmod = -1 * kmod

        kmod_list.append(kmod)

    return kmod_list, beamsizes_squared_list


def compute_emit_bmag_quad_scan_machine_units(
    quad_vals: list,
    beamsizes: list,
    q_len: float,
    rmat: np.ndarray,
    energy: float,
    twiss_design: np.ndarray,
    thin_lens: bool = False,
    maxiter: int = None,
):
    """
    Wrapper for analyze_quad_scan that takes quads in machine units and beamsize in meters.

    Parameters
    ----------
    quad_vals : list
        A list of two arrays containing the quadrupole values in kG for x and y respectively.
    beamsizes : list
        A list of two arrays containing the beam sizes in meters for x and y respectively.
    q_len : float
        The effective length of the quadrupole in meters.
    rmat : np.ndarray
        The R-matrix. Shape (2, 2, 2).
    energy : float
        The energy of the beam in eV.
    twiss_design : np.ndarray or None
        The design Twiss parameters. Shape (2, 2).
    thin_lens : bool, optional
        Whether to use the thin lens approximation. Default is False.
    maxiter : int, optional
        Maximum number of iterations for the optimization. Default is None.

    Returns
    -------
    dict
        The results of the emittance calculation.
    """  # Preprocessing data
    kmod_list, beamsizes_squared_list = preprocess_inputs(
        quad_vals, beamsizes, energy, q_len
    )

    # Prepare outputs
    results = {
        "emittance": [],
        "twiss_at_screen": [],
        "beam_matrix": [],
        "bmag": [] if twiss_design is not None else None,
        "quadrupole_focusing_strengths": [],
        "quadrupole_pv_values": [],
        "rms_beamsizes": [],
    }

    # Then call analyze_quad_scan
    # fit scans independently for x/y
    # only keep data that has non-nan beam sizes -- independent for x/y
    for i in range(2):
        result = compute_emit_bmag_quad_scan(
            k=kmod_list[i],
            beamsize_squared=beamsizes_squared_list[i],
            q_len=q_len,
            rmat=rmat[i],
            twiss_design=(
                twiss_design[i] if twiss_design is not None else None
            ),
            thin_lens=thin_lens,
            maxiter=maxiter,
        )

        result.update({"quadrupole_focusing_strengths": kmod_list[i]})
        result.update(
            {"quadrupole_pv_values": quad_vals[i][~np.isnan(beamsizes[i])]}
        )

        # add results to dict object
        for name, value in result.items():
            if name == "bmag" and value is None:
                continue
            else:  # beam matrix and emittance get appended
                results[name].append(value)

        results["rms_beamsizes"].append(beamsizes[i][~np.isnan(beamsizes[i])])

    return results


def normalize_emittance(emit, energy):
    gamma = energy / (
        0.511e-3
    )  # beam energy (GeV) divided by electron rest energy (GeV)
    beta = 1.0 - 1.0 / (2 * gamma**2)
    emit_n = gamma * beta * emit
    return emit_n  # the normalized emittance
