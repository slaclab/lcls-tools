from pytao import Tao
from lcls_tools.common.data_analysis.bmad_modeling import bmad_modeling as mod
from lcls_tools.common.data_analysis.bmad_modeling.outputs import bmad_modeling_outputs as outfn

#Instaintiate a tao object
OPTIONS = '-slice BEGINNING:END -noplot '
INIT = f'-init $LCLS_LATTICE/bmad/models/sc_sxr/tao.init {OPTIONS}'
tao = Tao(INIT)
tao.cmd('set ele BEGINNING:ENDCOL0 field_master=True')

#Short cut command for user readable output
def tc(cmd):
    [print(line) for line in tao.cmd(cmd)]

#Instantiate a modeling class with mod.BmadModeling(<beam path>, <'ACT','DES', or 'ARCHIVE'>
bm = mod.BmadModeling('sc_sxr', 'DES')
bm.date_time = '2024-04-02T09:00:00.000000-08:00'

#See ./lcls_tools/common/data_analysis/bmad_modeling/yaml/outkeys.yml 
#for list of outputs provided by get_output() 
output_design = mod.get_output(tao)

#Get a list of RF and QUADs PVs from lcls-live
rf_quads_pv_list = mod.get_rf_quads_pvlist(tao, bm.all_data_maps)

#The desired energy gain comes from LEM EDES pvs as stored in
# ./lcls_tools/common/data_analysis/bmad_modeling/yaml/energy_measurements.yml
energy_gain_pv_list = mod.get_energy_gain_pvlist(bm.beam_path)

#pvdata from Archive, DES or ACT
pvdata = mod.get_machine_values(bm.data_source, rf_quads_pv_list + energy_gain_pv_list)

#Use lcls-live datamaps to get tao_cmds, a list of commands to update the Bmad model
tao_cmds = mod.get_tao(pvdata, bm)

#Evaluate the tao_cmds to update Bmad model
output = mod.evaluate_tao(tao, tao_cmds)

#Plotting uses matplotlib
figs = outfn.plot_betas(output_design, output)
figs = outfn.plot_betas(output_design, output)

#Other output functions
outfn.show_twiss(tao, 'HTRUNDB', 'HTR')
outfn.quad_table(tao)
outfn.plot_twiss(tao, output_design)

expected_energy_gain = mod.get_expected_energy_gain(pvdata, 'L3', bm.beam_path)

#Calculate a fudge factor and update Lcavities to have the Bmad model energy match
mod.update_energy_gain_sc(tao, pvdata, 'L1', bm)
mod.update_energy_gain_sc(tao, pvdata, 'L2', bm)
mod.update_energy_gain_sc(tao, pvdata, 'L3', bm)
output = mod.get_output(tao)


# For developers:
#This is a way to reload your modules after edits without having to exit python
"""
import importlib
importlib.reload(mod)
importlib.reload(outfn)
"""
