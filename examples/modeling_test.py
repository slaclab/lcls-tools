from pytao import Tao
from lcls_tools.common.data_analysis.bmad_modeling import bmad_modeling as mod
from lcls_tools.common.data_analysis.bmad_modeling.outputs import bmad_modeling_outputs as outfn
OPTIONS = '-slice BEGINNING:END -noplot '

INIT = f'-init $LCLS_LATTICE/bmad/models/sc_sxr/tao.init {OPTIONS}'
tao = Tao(INIT)
tao.cmd('set ele BEGINNING:ENDCOL0 field_master=True')


def tc(cmd):
    [print(line) for line in tao.cmd(cmd)]


bm = mod.BmadModeling('sc_sxr', 'DES')
bm.date_time = '2024-04-02T09:00:00.000000-08:00'
output_design = mod.get_output(tao)
rf_quads_pv_list = mod.get_rf_quads_pvlist(tao, bm.all_data_maps)
energy_gain_pv_list = mod.get_energy_gain_pvlist(bm.beam_path)
pvdata = mod.get_machine_values(bm.data_source, rf_quads_pv_list + energy_gain_pv_list)
tao_cmds = mod.get_tao(pvdata, bm)
output = mod.evaluate_tao(tao, tao_cmds)

figs = outfn.plot_betas(output_design, output)
outfn.show_twiss(tao, 'HTRUNDB', 'HTR')
outfn.quad_table(tao)
outfn.plot_twiss(tao, output_design)
figs = outfn.plot_betas(output_design, output)


expected_energy_gain = mod.get_expected_energy_gain(pvdata, 'L3', bm.beam_path)

mod.update_energy_gain_sc(tao, pvdata, 'L1', bm)
mod.update_energy_gain_sc(tao, pvdata, 'L2', bm)
mod.update_energy_gain_sc(tao, pvdata, 'L3', bm)
output = mod.get_output(tao)
[print(line) for line in tao.cmd("show merit")]


# For developers:
"""
import importlib
importlib.reload(mod)
importlib.reload(outfn)
"""
