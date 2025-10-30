from typing import Dict

import numpy as np

from lcls_tools.common.devices.magnet import Magnet

from lcls_tools.common.measurements.screen_profile import ScreenBeamProfileMeasurement


def bmag(twiss, twiss_reference):
    """Calculates BMAG from imput twiss and reference twiss"""
    beta_a, alpha_a, beta_b, alpha_b = twiss
    beta_a_ref, alpha_a_ref, beta_b_ref, alpha_b_ref = twiss_reference
    bmag_a = bmag_func(beta_a, alpha_a, beta_a_ref, alpha_a_ref)
    bmag_b = bmag_func(beta_b, alpha_b, beta_b_ref, alpha_b_ref)
    return (bmag_a, bmag_b)


def bmag_func(bb, ab, bl, al):
    """Calculates the BMAG miss match parameter.  bb and ab are the modeled
    beta and alpha functions at a given element and bl and al are the
    reference (most of the time desing) values"""
    return 1 / 2 * (bl / bb + bb / bl + bb * bl * (ab / bb - al / bl) ** 2)


def kmod_to_bdes(e_tot=None, effective_length=None, k=None, element=None, tao=None):
    """Returns BDES in kG given K
    Inputs:
    e_tot - particle energy (eV)
    lEff - Effective quad length (m)
    K - focusing strengt (1/m^2)
    OR
    element, tao
    """
    if e_tot is not None and effective_length is not None and k is not None:
        bp = e_tot / 1e9 / 299.792458 * 1e4  # kG m
    elif element is not None and tao is not None:
        ele_attributes = tao.ele_gen_attribs(element)
        bp = ele_attributes["E_TOT"] / 1e9 / 299.792458 * 1e4  # kG m
        effective_length = ele_attributes["L"]
        k = ele_attributes["K1"]
    else:
        print(
            "Invalid input: Please provide either \
        (e_tot, effective_length and k) or (element and tao)"
        )
    return k * bp * effective_length  # 1/m^2 * kG m * m = kG


def bdes_to_kmod(e_tot=None, effective_length=None, bdes=None, tao=None, element=None):
    """Returns K in 1/m^2 given BDES
    Need to privide either particle energy e_tot and quad effective_length
    or element name and tao object"""
    if e_tot is not None and effective_length is not None and bdes is not None:
        bp = e_tot / 1e9 / 299.792458 * 1e4  # kG m
    elif element is not None and tao is not None:
        ele = tao.ele_gen_attribs(element)
        bp = ele["E_TOT"] / 1e9 / 299.792458 * 1e4  # kG m
        effective_length = ele["L"]
    return bdes / effective_length / bp  # kG / m / kG m = 1/m^2


def quad_scan_optics(
    magnet: Magnet, measurement: ScreenBeamProfileMeasurement, physics_model="BMAD"
) -> Dict:
    """Get rmat from magnet to measurement device and twiss at measurement device"""
    # TODO: get optics from arbitrary devices (potentially in different beam lines)
    model = _get_model_from_device(measurement.beam_profile_device, physics_model)
    rmat = model.get_rmat(
        from_device=magnet.name,
        to_device=measurement.beam_profile_device.name,
    )
    twiss = model.get_twiss(measurement.beam_profile_device.name)
    return {"rmat": rmat, "design_twiss": twiss}


def multi_device_optics(
    measurements: list[ScreenBeamProfileMeasurement], physics_model="BMAD"
) -> Dict:
    """Get rmat and twiss at measurement devices"""
    model = _get_model_from_device(measurements[-1].beam_profile_device, physics_model)
    device_names = [
        measurement.beam_profile_device.name for measurement in measurements
    ]
    rmat = model.get_rmat(device_names)
    twiss = model.get_twiss(device_names)
    return {"rmat": rmat, "design_twiss": twiss}


def _get_model_from_device(device, physics_model):
    from meme.model import Model

    beam_path = None
    for bp in device.metadata.beam_path:
        if bp in [
            "CU_HXR",
            "CU_SXR",
            "CU_SPEC",
            "SC_DIAG0",
            "SC_BSYD",
            "SC_HXR",
            "SC_SXR",
            "FACET2E",
        ]:
            beam_path = bp
            break
    if beam_path is None:
        raise ValueError("Valid beam path not found in device metadata.")

    return Model(beam_path, model_source=physics_model, use_design=False)


def propagate_twiss(twiss_init: np.ndarray, rmat: np.ndarray):
    """
    Propagates twiss parameters downstream given a transport rmat.

    Parameters:
        twiss_init: numpy array shape batchshape x 3 containing the initial twiss params
                    (ordered: beta, alpha, gamma)
        rmat: numpy array shape batchshape x 2 x 2 containing 2x2 transport rmats

    Outputs:
        twiss_final: numpy array shape batchshape x 3 containing the downstream twiss params
                    (ordered: beta, alpha, gamma)
    """
    twiss_transport = twiss_transport_mat_from_rmat(
        rmat
    )  # result shape (batchshape x 3 x 3)

    twiss_final = twiss_transport @ np.expand_dims(twiss_init, axis=-1)
    # result shape (batchshape x 3 x 1)

    return twiss_final.squeeze(-1)


def twiss_transport_mat_from_rmat(rmat: np.ndarray):
    """
    Converts from 2x2 rmats to 3x3 twiss transport matrices.

    Parameters:
        rmat: numpy array shape batchshape x 2 x 2

    Outputs:
        result: numpy array shape batchshape x 3 x 3
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
    )  # result shape (batchshape, 3, 3)
    return result


def build_quad_rmat(k: np.ndarray, q_len: float, thin_lens: bool = False):
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

    source: https://uspas.fnal.gov/materials/11ODU/Lecture6_Transverse_Beam_Optics_1.pdf
    """

    if not thin_lens:
        sqrt_k = np.sqrt(np.abs(k)) + 1.0e-6  # add small value for numerical stability

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
