from meme.model import Model


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
    reference (most of the time desing) values """
    return 1 / 2 * (bl / bb + bb / bl + bb * bl * (ab / bb - al / bl) ** 2)


def kmod_to_bdes(e_tot=None, effective_length=None, k=None,
                 element=None, tao=None):
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
        print("Invalid input: Please provide either \
        (e_tot, effective_length and k) or (element and tao)")
    return k * bp * effective_length  # 1/m^2 * kG m * m = kG


def bdes_to_kmod(e_tot=None, effective_length=None, bdes=None,
                 tao=None, element=None):
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


def get_optics(magnet: str, measurement_device: str, beamline: str):
    """Get rmats and twiss for a given beamline, magnet and measurement device"""
    model = Model(beamline)
    rmats = model.get_rmat(from_device=magnet, to_device=measurement_device)
    twiss = model.get_twiss(magnet)
    return rmats, twiss
