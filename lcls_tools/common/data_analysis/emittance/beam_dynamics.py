import numpy as np
from scipy.optimize import minimize
import importlib.util

def compute_bmag(beam_matrix, rmat, beta0, alpha0):
    """
    parameters:
        beam_matrix: numpy array shape batchshape x 3 x 1 giving the initial beam matrix before the measurement quad
                
        rmat: numpy array shape batchshape x nsteps x 2 x 2 giving the rmats that describe transport
                    through the meas quad and to the screen for each step in the measurement scan(s)
        
        beta0: float or numpy array shape (batchshape x 1) designating the design beta (twiss) parameter
                at the screen
        
        alpha0: float or numpy array shape (batchshape x 1) designating the design alpha (twiss) parameter
                at the screen
    returns:
        bmag: numpy array shape batchshape x nsteps containing the bmag from each step in each measurement scan
    """
    twiss_at_screen = propagate_beam_matrix(beam_matrix, rmat)[1]
    # result shape (batchshape x nsteps x 3 x 1)

    # get design gamma0 from design beta0, alpha0
    gamma0 = (1 + alpha0**2) / beta0

    # compute bmag
    bmag = 0.5 * (twiss_at_screen[...,0,0] * gamma0
                - 2 * twiss_at_screen[...,1,0] * alpha0
                + twiss_at_screen[...,2,0] * beta0
               )
    # result shape (batchshape x nsteps)

    return bmag


def reconstruct_beam_matrix(k, beamsize_squared, q_len, rmat, thin_lens=False, maxiter=None):
    """
    Reconstructs the beam matrices corresponding to a set of quadrupole measurement scans
    using nonlinear fitting to guarantee physically valid results. Fitting will use torch autograd
    if available. If torch is not available, jacobians will be approximated with finite difference.

    Parameters:
        k: numpy array of shape (n_steps_quad_scan,) or (batchshape x n_steps_quad_scan),
            representing the measurement quad geometric focusing strengths in [m^-2]
            used in a batch of emittance scans

        beamsize_squared: numpy array of shape (batchshape x n_steps_quad_scan),
                where each row represents the mean-square beamsize outputs in [mm^2] of an emittance scan
                with inputs given by k

        q_len: float defining the (longitudinal) quadrupole length or "thickness" in [m]
        
        rmat: numpy array shape (2x2) or (batchshape x 2 x 2)
                containing the 2x2 R matrices describing the transport from the end of the 
                measurement quad to the observation screen.

        thin_lens: boolean specifying whether or not to use thin lens approximation for measurement quad.

        max_iter: maximum number of iterations to perform in nonlinear fitting (minimization algorithm)
                
    Outputs:
        beam_matrix: numpy array of shape (batchshape x 3 x 1) containing column vectors of sig11, sig12, sig22

        total_rmat: numpy array of shape (batchshape x nsteps x 2 x 2) containing R matrices describing
                    transport from the BEGINNING of the measurement quadrupole to the screen, for each
                    step in the quadrupole scan(s).
    """
    
    # construct the A matrix from eq. (3.2) & (3.3) of source paper
    quad_rmat = build_quad_rmat(k, q_len, thin_lens=thin_lens) # result shape (batchshape x nsteps x 2 x 2)
    total_rmat = np.expand_dims(rmat,-3) @ quad_rmat
    # result shape (batchshape x nsteps x 2 x 2)
    
    # prepare the A matrix
    r11, r12 = total_rmat[...,0,0], total_rmat[...,0,1]
    amat = np.stack((r11**2, 2.*r11*r12, r12**2), axis=-1)
    # amat result (batchshape x nsteps x 3)

    beamsize_squared = np.expand_dims(beamsize_squared,-1)

    def beam_matrix_tuple(params): 
        # converts fit parameters to beam matrix parameters and packages for stacking
        return (params[...,0,:]**2, # lamba1^2 = sig11
                params[...,0,:]*params[...,1,:]*params[...,2,:], # lambda1*lambda2*c = sig12
                params[...,1,:]**2) # lamba2^2 = sig22

    # check if torch is available to be imported
    torch_spec = importlib.util.find_spec("torch")
    torch_found = torch_spec is not None
    if torch_found:
        # define loss function in torch and use autograd to get its jacobian
        import torch
        amat = torch.from_numpy(amat)
        beamsize_squared = torch.from_numpy(beamsize_squared)
        def loss_torch(params):
            # add documentation for these funcs
            params = torch.reshape(params, [*beamsize_squared.shape[:-2],3,1])
            sig = torch.stack(beam_matrix_tuple(params), dim=-2)
            # sig should now be shape batchshape x 3 x 1
            total_squared_error = (amat @ sig - beamsize_squared).pow(2).sum()
            return total_squared_error
        def loss_jacobian(params):
            return(
            torch.autograd.functional.jacobian(
                loss_torch, torch.from_numpy(params)
            ).detach().numpy()
            )
        def loss(params):
            return loss_torch(torch.from_numpy(params)).detach().numpy()
    else:
        # define loss function in numpy without jacobian
        def loss(params):
            params = np.reshape(params, [*beamsize_squared.shape[:-2],3,1])
            sig = np.stack(beam_matrix_tuple(params), axis=-2)
            # sig should now be shape batchshape x 3 x 1
            total_squared_error =np.sum((amat @ sig - beamsize_squared)**2)
            return total_squared_error
        loss_jacobian = None

    eps = 1.e-6

    # get initial guesses for lambda1, lambda2, c, from pseudo-inverse method
    init_beam_matrix = np.linalg.pinv(np.array(amat)) @ np.array(beamsize_squared)
    lambda1 = np.sqrt(init_beam_matrix[...,0,0].clip(min=eps))
    lambda2 = np.sqrt(init_beam_matrix[...,2,0].clip(min=eps))
    c = (init_beam_matrix[...,1,0]/(lambda1*lambda2)).clip(min=-1+eps, max=1-eps)
    init_params = np.stack((lambda1, lambda2, c), axis=-1).flatten()

    # define bounds (only c parameter is bounded, between -1 and 1)
    bounds = np.tile(np.array([[None, None], [None, None], [-1.+eps, 1.-eps]]), 
                     (np.prod(beamsize_squared.shape[:-2]), 1)
                    )
    if maxiter is not None:
        options = {'maxiter':maxiter}
    else:
        options = None

    # minimize loss
    res = minimize(loss, 
                   init_params, 
                   jac=loss_jacobian,
                   bounds=bounds,
                   options=options
                  )

    fit_params = res.x
    fit_params = np.reshape(fit_params, [*beamsize_squared.shape[:-2],3,1])

    # convert fit params back to beam matrix params
    beam_matrix = np.stack(beam_matrix_tuple(fit_params), axis=-2) 
    # result shape (batchshape x 3 x 1) containing column vectors of [sig11, sig12, sig22]

    return beam_matrix, total_rmat

def propagate_beam_matrix(beam_matrix_init, rmat):
    """
    parameters:
        beam_matrix_init: numpy array shape batchshape x 3 x 1
        rmat: numpy array shape batchshape x nsteps x 2 x 2
    returns:
        beam_matrix_final: numpy array shape batchshape x nsteps x 3 x 1
        twiss_final: numpy array shape batchshape x nsteps x 3 x 1
    """
    emit = np.sqrt(beam_matrix_init[...,0,0]*beam_matrix_init[...,2,0] - beam_matrix_init[...,1,0]**2) # result shape (batchshape)
    temp = np.array([[[1., 0., 0.],
                           [0., -1., 0.],
                           [0., 0., 1.]]])
    twiss_init = (temp @ beam_matrix_init) @ (1/emit.reshape(*emit.shape,1,1)) # result shape (batchshape x 3 x 1)
    
    twiss_transport = twiss_transport_mat_from_rmat(rmat) # result shape (batchshape x 3 x 3)

    twiss_final = twiss_transport @ np.expand_dims(twiss_init,-3)
    # result shape (batchshape x nsteps x 3 x 1)

    beam_matrix_final = (temp @ twiss_final) @ emit.reshape(*emit.shape,1,1,1) 
    # result shape (batchshape x nsteps x 3 x 1)
    
    return beam_matrix_final, twiss_final


def twiss_transport_mat_from_rmat(rmat):
    # Converts from 2x2 rmats to 3x3 twiss transport matrices.
    c, s, cp, sp = rmat[...,0,0], rmat[...,0,1], rmat[...,1,0], rmat[...,1,1]
    result = np.stack((
        np.stack((c**2, -2*c*s, s**2), axis=-1), 
        np.stack((-c*cp, c*sp + cp*s, -s*sp), axis=-1),
        np.stack((cp**2, -2*cp*sp, sp**2), axis=-1)), 
        axis=-2
    ) # result shape (*rmat.shape, 3, 3)
    return result


def build_quad_rmat(k, q_len, thin_lens=False):
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

        c = (np.cos(sqrt_k*q_len)*(k > 0) 
            + np.cosh(sqrt_k*q_len)*(k < 0) 
            + np.ones_like(k)*(k == 0)
            )
        s = (np.nan_to_num(1./sqrt_k) * np.sin(sqrt_k*q_len)*(k > 0) 
             + np.nan_to_num(1./sqrt_k) * np.sinh(sqrt_k*q_len)*(k < 0) 
             + q_len*np.ones_like(k)*(k == 0)
            )
        cp = (-sqrt_k * np.sin(sqrt_k*q_len)*(k > 0) 
              + sqrt_k * np.sinh(sqrt_k*q_len)*(k < 0)
              + np.zeros_like(k)*(k == 0)
             )
        sp = (np.cos(sqrt_k*q_len)*(k > 0) 
              + np.cosh(sqrt_k*q_len)*(k < 0)
              + np.ones_like(k)*(k == 0)
             )
                       
    else:
        c, s, cp, sp = (np.ones_like(k), np.zeros_like(k), -k*q_len, np.ones_like(k))
        
    rmat = np.stack((
        np.stack((c, s), axis=-1), 
        np.stack((cp, sp), axis=-1),), 
        axis=-2
    ) # final shape (*k.shape, 2, 2)
     
    return rmat