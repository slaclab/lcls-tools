import numpy as np
import yaml
import os
import epics
from lcls_live.datamaps import get_datamaps
from lcls_live.archiver import lcls_archiver_restore


def get_rf_quads_pvlist(tao, all_data_maps, beam_code=1):
<<<<<<< HEAD
    """Returns pvlist from lcls_live datamaps for given beam_path
    for Cu beampaths beam_code can be 1 or 2"""
=======
    """Returns pvlist for given beam_path"""
>>>>>>> ed37cc8ec1f2f7a00bd319bfb6b2fc6ab1fa40c4
    pvlist = set()
    for dm_key, map in all_data_maps.items():
        if dm_key in ["cavities", "quad"]:
            elements = (map.data["bmad_name"].to_list())
            pvs = map.pvlist
            model_elements = []
            full_model_elements = tao.lat_list("*", "ele.name")
            for mdl_ele in full_model_elements:
                if "#2" in mdl_ele:  # Deal with split elements in bmad
                    continue
                new_ele = mdl_ele.replace("#1", "")
                model_elements.append(new_ele)
            for indx, ele in enumerate(elements):
                if ele in model_elements:
                    pvlist.add(pvs[indx])
        if dm_key.startswith('K'):  # One for each Klystron station
            for pv in map.pvlist:
                if "BEAMCODE" in pv:
                    pv = f"BEAMCODE{beam_code}_STAT"
                pvlist.add(pv)
    return list(pvlist)


def get_energy_gain_pvlist(beam_path):
<<<<<<< HEAD
    """Interim function to get list of EDES PVs from YAML file"""
    pvlist = []
    yaml_dir = '/sdf/home/c/colocho/lcls-tools/lcls_tools/' \
               'common/data_analysis/bmad_modeling/yaml/'
    print("Current working directory:", os.getcwd())
=======
    pvlist = []
    yaml_dir = '/sdf/home/c/colocho/lcls-tools/lcls_tools/' \
               'common/data_analysis/bmad_modeling/yaml/'
>>>>>>> ed37cc8ec1f2f7a00bd319bfb6b2fc6ab1fa40c4
    with open(yaml_dir + 'energy_measurements.yml', 'r') as file:
        engy_meas = yaml.safe_load(file)[beam_path[0:2]]
    [pvlist.append(engy_meas[key]) for key in engy_meas.keys()]
    return pvlist


def evaluate_tao(tao, tao_cmds):
    """
<<<<<<< HEAD
    Evaluate set of tao commands, toggles lattice_calculation OFF/ON
=======
    Evaluate set of tao command, toggles lattice_calculation OFF/ON
>>>>>>> ed37cc8ec1f2f7a00bd319bfb6b2fc6ab1fa40c4
    in between command list
    """
    tao.cmd("set global lattice_calc_on = F")
    tao.cmds(tao_cmds)
    tao.cmd("set global lattice_calc_on = T")
    output = get_output(tao)
    return output


def get_twiss(tao, element, which="design"):
    """Gets twiss for element, which can be model, desing or base"""
    result = tao.ele_twiss(element, which=which)
    return [result[p] for p in ["beta_a", "alpha_a", "beta_b", "alpha_b"]]

<<<<<<< HEAD
def list_to_numpy_array(x, val_type = 'Ampl', ampl_reject = 0.5, none_value = 0):
    """Convert None to 0.0 for values in x, if is_phase convert to radians
    if is_ampl set values less than 0.5 Mev to zero"""
    x_np = np.array(x)
    x_np = np.where(x == None, np.nan, x).astype(float)
    x_np = np.nan_to_num(x_np, nan=0.0)
    if val_type == 'Ampl':
        x_np = np.where(x_np < ampl_reject, 0, x_np)
    if val_type == 'Phas':
        x_np = np.deg2rad(x_np)
    return x_np
    
=======

>>>>>>> ed37cc8ec1f2f7a00bd319bfb6b2fc6ab1fa40c4
def bmag(twiss, twiss_reference):
    """Calculates BMAG from imput twiss and reference twiss"""
    beta_a, alpha_a, beta_b, alpha_b = twiss
    beta_a_ref, alpha_a_ref, beta_b_ref, alpha_b_ref = twiss_reference
    bmag_a = bmag_func(beta_a, alpha_a, beta_a_ref, alpha_a_ref)
    bmag_b = bmag_func(beta_b, alpha_b, beta_b_ref, alpha_b_ref)
    return (bmag_a, bmag_b)


def bmag_func(bb, ab, bl, al):
    """bmag function"""
    return 1 / 2 * (bl / bb + bb / bl + bb * bl * (ab / bb - al / bl) ** 2)


def get_bmad_bdes(tao, element, b1_gradient=[]):
    """Returns BDES from Bmad B1_GRADIENT or given gradient"""
    ele_attr = tao.ele_gen_attribs(element)
    if not b1_gradient:
        b1_gradient = ele_attr["B1_GRADIENT"]
    return -b1_gradient * ele_attr["L"] * 10


def match_twiss(tao, variable, datum):
    """Performs optimization for given variable and datum"""
    match_cmds = ["veto var *", "veto dat *@*",
                  "set global n_opti_cycles = 912"]
    match_cmds.append(f"use var {variable}[1:4]")
    match_cmds.append(f"use dat {datum}[1:4]")
    tao.cmds(match_cmds)
    tao.cmd("run")


def get_tao(pvdata, mdl_obj):
    """
<<<<<<< HEAD
    Returns tao commands from pvdata, if data_source is DES, calls use_klys_when_beam off for Cu Linac
=======
    Returns tao commands, if data_source is DES, calls use_klys_when_beam off
    for Cu Linac
>>>>>>> ed37cc8ec1f2f7a00bd319bfb6b2fc6ab1fa40c4
    """
    lines_quads, lines_rf = [], []
    for dm_key, map in mdl_obj.all_data_maps.items():
        if dm_key.startswith("K"):
            acc_pv = map.accelerate_pvname
            if acc_pv == "":
                continue
            acc_pv = f"{acc_pv[0:21]}{mdl_obj.beam_code}{acc_pv[22:]}"
            map.accelerate_pvname = acc_pv
            lines_rf += map.as_tao(pvdata)
        if dm_key == "cavities":
            lines_rf = map.as_tao(pvdata)
        if dm_key == "quads":
            lines_quads += map.as_tao(pvdata)
    if "DES" in mdl_obj.data_source and "cu" in mdl_obj.beam_path:
        new_lines = []
        for cmd in lines_rf:
            if "in_use" in cmd:
                if "K21_1" in cmd or "K21_2" in cmd:
                    new_lines.append(cmd)  # L1 always on Beam Code 1
                    continue
                ele = cmd.split()[2]
                [sector, station] = ele[1:].split("_")
                pv = f"KLYS:LI{sector}:{station}1:"
                f"BEAMCODE{mdl_obj.beam_code}_STAT"
                cmd_words = cmd.split()
                cmd_words[-1] = str(pvdata[pv])
                new_lines.append(" ".join(cmd_words))
            else:
                new_lines.append(cmd)
        lines_rf = new_lines
    return lines_rf + lines_quads


def get_machine_values(data_source, pv_list, date_time=''):
    """Returns pvdata, a dictionary with keys containing the PV name and values from Actual, Desired or Archive"""
    if data_source in ["DES", "ACT"]:
        pvdata = get_live(pv_list)
    elif "ARCHIVE" in data_source:
        pvdata = lcls_archiver_restore(pv_list, date_time)
    return pvdata


def kmod_to_bdes(tao, element, K=0):
    """Returns BDES given K1 in the Bmad model"""
    ele = tao.ele_gen_attribs(element)
    bp = ele["E_TOT"] / 1e9 / 299.792458 * 1e4  # kG m
    return ele["K1"] * bp * ele["L"]


def bdes_to_kmod(tao, element, bdes):
    """Returns K1 given BDES"""
    ele = tao.ele_gen_attribs(element)
    bp = ele["E_TOT"] / 1e9 / 299.792458 * 1e4  # kG m
    return bdes / ele["L"] / bp  # kG / m / kG m = 1/m^2


def get_output(tao):
    """
    Returns dictionary of modeled parameters, including element name,
    twiss and Rmats
    """
    yaml_dir = '/sdf/home/c/colocho/lcls-tools/lcls_tools/' \
               'common/data_analysis/bmad_modeling/yaml/'
    with open(yaml_dir + 'outkeys.yml', 'r') as file:
        outkeys = yaml.safe_load(file)['outkeys'].split()
    output = {k: tao.lat_list("*", k) for k in outkeys}
    return output


def get_element(tao, datum):
    """Do I need this?"""
    return tao.data_parameter(datum, "ele_name")[0].split(";")[1]


def get_live(pvlist):
    """Returns dictionary with PV names as keys and values of PVs"""
    return dict(zip(pvlist, epics.caget_many(pvlist)))


def use_klys_when_beam_off(tao_cmds, pvdata, beam_code="1"):
    """Modifies tao_cmds, in_use set to 1 if station active on
        beam_code"""
    # use = {}
    new_cmd = []
    for cmd in tao_cmds:
        if 'in_use' in cmd:
            ele = cmd.split()[2]
            [sector, station] = ele[1:].split("_")
            pv = f"KLYS:LI{sector}:{station}1:BEAMCODE{beam_code}_STAT"
            # use[ele] = pvdata[pv]
            cmd_words = cmd.split()
            cmd_words[-1] = pvdata[pv]
            new_cmd.append(" ".join(cmd_words))
        else:
            new_cmd.append(cmd)
    return new_cmd


def get_tao_cmds(pvdata, data_maps):
    """Returns command lines to update the Bmad model with Tao
    where element values come from pvdata"""
    lines = []
    for dm_key in data_maps.keys():
        lines += data_maps[dm_key].as_tao(pvdata)
    return lines


def create_emitmeas_datum(tao, element):
    tao.cmd("set global lattice_calc_on = F")
    tao.data_d2_create(f"emitmeas{element}", 1, "twiss^^1^^4")
    tao.datum_create(
        f"emitmeas{element}.twiss[1]",
        "beta.a",
        ele_name=element,
        merit_type="target",
        weight=10,
    )
    tao.datum_create(
        f"emitmeas{element}.twiss[2]",
        "alpha.a",
        ele_name=element,
        merit_type="target",
        weight=10,
    )
    tao.datum_create(
        f"emitmeas{element}.twiss[3]",
        "beta.b",
        ele_name=element,
        merit_type="target",
        weight=10,
    )
    tao.datum_create(
        f"emitmeas{element}.twiss[4]",
        "alpha.b",
        ele_name=element,
        merit_type="target",
        weight=10,
    )
    tao.data_set_design_value()
    tao.cmd("set global lattice_calc_on = T")


def get_expected_energy_gain(pvdata, region, beam_path):
    """
    expected gain PV NOT from lcls-live
    region is one of L0, L1, L2, L3
    """
    yaml_dir = '/sdf/home/c/colocho/lcls-tools/lcls_tools/' \
               'common/data_analysis/bmad_modeling/yaml/'
<<<<<<< HEAD
    print("Current working directory:", os.getcwd())
    with open('energy_measurements.yml', 'r') as file:
=======
    with open(yaml_dir + 'energy_measurements.yml', 'r') as file:
>>>>>>> ed37cc8ec1f2f7a00bd319bfb6b2fc6ab1fa40c4
        engy_meas = yaml.safe_load(file)[beam_path[0:2]]
    if region == 'L1':
        previous_region = 'GUN'
    else:
        previous_region = 'L' + str(int(region[1]) - 1)
    expected_gain = pvdata[engy_meas[region]] - \
        pvdata[engy_meas[previous_region]]
    return expected_gain


<<<<<<< HEAD
def update_energy_gain_sc(tao, pvdata, region, mdl_obj):
=======
class BmadModeling:
    def __init__(self, beam_path, data_source):
        self.beam_path: str = beam_path
        self.data_source: str = data_source
        self.beam_code: str = '1'
        self.date_time: str = '2024-03-24T17:10:00.000000-08:00'
        """updates datamaps depending on data source used by lcls-live"""
        if "LCLS_LATTICE" not in os.environ:
            raise OSError("Environment variable LCLS_LATTICE not defined")
        self.all_data_maps = get_datamaps(self.beam_path)
        if self.data_source == "DES":
            use_pv = "pvname"
        elif self.data_source == "ACT":
            use_pv = "pvname_rbv"
        elif self.data_source == "ARCHIVE":
            use_pv = "pvname"
        if "sc" in self.beam_path:
            self.all_data_maps["cavities"].pvname = use_pv
            self.injector_energy = 0.09
        self.all_data_maps["quad"].pvname = use_pv
        self.energy_measurements = self.all_data_maps['tao_energy_measurements'].data.to_dict()


def update_energy_gain_sc(self, tao, pvdata, region):
>>>>>>> ed37cc8ec1f2f7a00bd319bfb6b2fc6ab1fa40c4
    """
    Updates SC Linac energy gain profile based on bending magnets,
    calculates a fudge and modifies model's cavity amplitudes and phases
    """
<<<<<<< HEAD
    expected_gain = get_expected_energy_gain(pvdata, region, mdl_obj.beam_path)
=======
    expected_gain = self.get_expected_energy_gain(region)
>>>>>>> ed37cc8ec1f2f7a00bd319bfb6b2fc6ab1fa40c4
    cavities = tao.lat_list(
        f"LCAV::BEG{region}B:END{region}B", "ele.name")
    for indx, cav in enumerate(cavities):
        cavities[indx] = cav.split("#")[0]
    cavities = list(set(cavities))
    devices = [tao.ele_head(element)["alias"] for element in cavities]
    if mdl_obj.data_source == "ACT":
        attr = "ACTMEAN"
    elif mdl_obj.data_source in ["DES", "ARCHIVE"]:
        attr = "DES"
    ampl = [pvdata[dev + ":A" + attr] for dev in devices]
    phas = [pvdata[dev + ":P" + attr] for dev in devices]
    amplNp = list_to_numpy_array(ampl)
    phasNp = list_to_numpy_array(phas, val_type = 'Phas')
    gainMeasured = amplNp * np.cos(phasNp)
<<<<<<< HEAD
    dF = (expected_gain - sum(gainMeasured)) / amplNp.sum()

=======
    dF = (expected_gain - sum(gainMeasured)) / sum(ampl)
>>>>>>> ed37cc8ec1f2f7a00bd319bfb6b2fc6ab1fa40c4
    # fudge = 1 + dF
    complexGain = amplNp * np.exp(1j * phasNp)
    complexGainFudged = complexGain + amplNp * dF
    amplF = np.abs(complexGainFudged)
    phasF = np.degrees(np.angle(complexGainFudged))
    pvdata_fudge = dict()
    pvdata_reg = dict()
    for indx, pv in enumerate(devices):
        pvdata_fudge[f"{pv}:PACTMEAN"] = phasF[indx]
        pvdata_fudge[f"{pv}:AACTMEAN"] = amplF[indx]
        pvdata_reg[f"{pv}:P{attr}"] = phasF[indx]
        pvdata_reg[f"{pv}:A{attr}"] = amplF[indx]
    data_map = {"cavities": mdl_obj.all_data_maps["cavities"]}
    tao_cmds = get_tao_cmds(pvdata, data_map)
    evaluate_tao(tao, tao_cmds)
    region_e_tot = tao.ele_gen_attribs(f"END{region}B")["E_TOT"] / 1e9
    print(region_e_tot)


<<<<<<< HEAD
def update_energy_gain_cu(tao, pvdata, mdl_obj):
=======
def update_energy_gain_cu(self, tao, pvdata, region):
>>>>>>> ed37cc8ec1f2f7a00bd319bfb6b2fc6ab1fa40c4
    """
    Updates Cu Linac energy gain profile based on bending magnets,
    calculates a fudge and modifies model's cavity amplitudes and phases
    """
<<<<<<< HEAD
    expected_gain = get_expected_energy_gain(region)
=======
    expected_gain = self.get_expected_energy_gain(region)
>>>>>>> ed37cc8ec1f2f7a00bd319bfb6b2fc6ab1fa40c4
    init_cmds = ["veto dat *", "veto var *"]
    if region == "L2":
        tao.cmd(f"set dat BC1.energy[2]|meas = {expected_gain} ")
        optimize_cmds = init_cmds + [
            "use dat BC2.energy[1]",
            "use var linac_fudge[2]"]
    if region == "L3":
        tao.cmd(f"set dat L3[2]|meas ={expected_gain} ")
        optimize_cmds = init_cmds + [
            "use dat L3.energy[2]",
            "use var linac_fudge[3]"]
    tao.cmds(optimize_cmds)
    r = tao.cmd("run")
    print(r)
<<<<<<< HEAD


def update_datum_meas(tao, datum, mdl_obj, useDesing=True):
    """
    Updates datum with EPICS or design twiss values
    """
    [d2_name, d1_name] = datum.split('.')
    element = tao.data(d2_name, d1_name)['ele_name']
=======
    [print(line) for line in tao.cmd("show merit")]


def update_datum_meas(self, tao, datum, useDesing=True):
    """
    Updates datum with EPICS or design twiss values
    """
    element = self.get_element(tao, datum)
>>>>>>> ed37cc8ec1f2f7a00bd319bfb6b2fc6ab1fa40c4
    TWISS = ["beta_a", "alpha_a", "beta_b", "alpha_b"]
    cmd = []
    if useDesing:
        ele_twiss = tao.ele_twiss(element, which="design")
        for ii, p in enumerate(TWISS):
            cmd.append(f"set dat {datum}[{ii+1}]|meas = {ele_twiss[p]}")
    else:
        device = tao.ele_head(element)["alias"]
        EPICS_ATTRIBUTE = ["BETA_X", "ALPHA_X", "BETA_Y", "ALPHA_Y"]
        pvs = [device + ":" + twiss for twiss in EPICS_ATTRIBUTE]
        if self.data_source in ["ACT", "DES"]:
            measured = get_live(pvs)
        elif self.data_source == "ARCHIVE":
            measured = lcls_archiver_restore(pvs, self.date_time)
        for ii, pv in enumerate(pvs):
            cmd.append(
                f"set dat {datum}[{ii+1}]|meas = {measured[pvs[ii]]}")
    tao.cmds(cmd)
    tao.cmd(f"show dat {datum}")
<<<<<<< HEAD


class BmadModeling:
    def __init__(self, beam_path, data_source):
        self.beam_path: str = beam_path
        self.data_source: str = data_source
        self.beam_code: str = '1'
        self.date_time: str = '2024-03-24T17:10:00.000000-08:00'
        """updates datamaps depending on data source used by lcls-live"""
        if "LCLS_LATTICE" not in os.environ:
            raise OSError("Environment variable LCLS_LATTICE not defined")
        self.all_data_maps = get_datamaps(self.beam_path)
        if self.data_source == "DES":
            use_pv = "pvname"
        elif self.data_source == "ACT":
            use_pv = "pvname_rbv"
        elif self.data_source == "ARCHIVE":
            use_pv = "pvname"
        if "sc" in self.beam_path:
            self.all_data_maps["cavities"].pvname = use_pv
            self.injector_energy = 0.09
        self.all_data_maps["quad"].pvname = use_pv


=======
>>>>>>> ed37cc8ec1f2f7a00bd319bfb6b2fc6ab1fa40c4
