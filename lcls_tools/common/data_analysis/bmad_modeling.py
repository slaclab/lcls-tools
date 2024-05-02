from dataclasses import dataclass
from pytao import Tao
import numpy as np
import pandas as pd
import json
import os
from contextlib import redirect_stdout
import matplotlib.pyplot as plt
import epics
from lcls_live.datamaps import get_datamaps
from lcls_live.archiver import lcls_archiver_restore
from lcls_live import data_dir

@dataclass
class BmadModel:
    """
    Bmad Modeling class for analysis and plotting. 
    Machine data from  EPICS DES, EPICS ACT or , Archive.

    Attributes
    ----------
    beam_path: 'cu_hxr', 'sc_sxr' and others. 
    LCLS lattice description: 
    https://www.slac.stanford.edu/grp/ad/model/lcls.html

    Methods
    ----------

    get_tao(self, pvdata):
        Returns tao commands, if data_source is DES, 
    calls use_klys_when_beam off
    --
     use_klys_when_beam_off(tao_cmds, pvdata, beam_code = '1'):
        Modifies tao_cmds, in_use set to 1 if station active on beam_code 
    --
     get_machine_values(self, pv_list):
        Returns pvdata, a dictionary with keys containing
        the PV name and values from Actual, Desired or Archive      
    --
     tc(self, tao, cmd):
        Prints result of tao.cmd() one line at a time
    --
     update_energy_gain(self, tao, pvdata, linac_region):
        Updates energy gain profile based on bending magnets, 
    calculates a fudge and 
        modifies cavity amplitudes and phases
    --
     get_rf_quads_pvlist(self):
        Returns pvlist for given beam_path
    --
     get_tao_cmds(self, pvdata, data_maps):
        Returns command lines to update the Bmad model with Tao
        where  element values come from pvdata
    --
     get_live(self,pvlist):
        Returns dictionary with PV names as keys and values of PVs
    --
     evaluate_tao(self, tao, tao_cmds):
        Evaluate set of tao command, toggles lattice_calculation OFF/ON 
        in between command list
    --
     kmod_to_bdes(self, tao, element, K = 0):
        Returns BDES given K1 in the Bmad model
    --
     bdes_to_kmod(self,tao, element, bdes):
        Returns K1 given BDES 
    --
     plot_betas(self, output1, output2, **kwargs):
        Generates two figures with betas X and Y for two output runs
    --
     get_output(self, tao):
        Returns dictionary of modeled parameters, including element name, 
    twiss and Rmats

    """
    beam_path: str
    data_source: str
    beam_code: str = '1'
    date_time: str = '2024-03-24T17:10:00.000000-08:00'

    def __post_init__(self):
        """Runs after dataclass init, updates data maps used by lcls-live"""
        if not 'LCLS_LATTICE' in os.environ:
            raise OSError('Environment variable LCLS_LATTICE needs to be defined')
        self.all_data_maps = get_datamaps(self.beam_path)
        if self.data_source == 'DES':
            use_pv = 'pvname'
        elif self.data_source == 'ACT':
            use_pv = 'pvname_rbv'
        elif self.data_source == 'ARCHIVE':
            use_pv = 'pvname'
        if 'sc' in self.beam_path:
            self.all_data_maps['cavities'].pvname = use_pv
        self.all_data_maps['quad'].pvname = use_pv


    def get_rf_quads_pvlist(self, tao):
        """Returns pvlist for given beam_path"""
        pvlist = set()
        for dm_key in self.all_data_maps.keys():
            if dm_key in ['bpms', 'correctors', 'quad_corrector', 'solenoid']:
                continue
            if dm_key in ['cavities', 'quad']:
                elements = self.all_data_maps[dm_key].data['bmad_name'].to_list()
                pvs = self.all_data_maps[dm_key].pvlist
                model_elements = []
                full_model_elements = tao.lat_list('*','ele.name')
                for mdl_ele in full_model_elements:
                    if '#2' in mdl_ele:
                        continue
                    elif '#1' in mdl_ele:
                        new_ele = mdl_ele.replace('#1','')
                    else:
                        new_ele = mdl_ele
                    model_elements.append(new_ele)
                for indx, ele in enumerate(elements):
                    if ele in model_elements:
                        pvlist.add(pvs[indx]) 
            else:
                for pv in self.all_data_maps[dm_key].pvlist:
                    if 'BEAMCODE' in pv:
                        pv = pv.replace('BEAMCODE2', f'BEAMCODE{self.beam_code}')
                    pvlist.add(pv)
        if 'sc' in self.beam_path:
            pvlist.update(['REFS:BC2B:500:EDES', 'REFS:BC1B:400:EDES', 'REFS:DMPS:400:EDES'])
        return list(pvlist)
        
    def get_tao(self, pvdata):
        """Returns tao commands, if data_source is DES, 
        calls use_klys_when_beam off"""
        lines_quads, lines_rf = [], []
        for dm_key in self.all_data_maps.keys():
            if dm_key in ['bpms' , 'correctors', 'quad_corrector', 'solenoid']:
                continue
            if dm_key[0] == 'K':
                acc_pv = self.all_data_maps[dm_key].accelerate_pvname
                if acc_pv == '':
                    continue
                acc_pv =f'{acc_pv[0:21]}{self.beam_code}{acc_pv[22:]}'
                self.all_data_maps[dm_key].accelerate_pvname = acc_pv
                lines_rf += self.all_data_maps[dm_key].as_tao(pvdata)
            elif dm_key == 'cavities':
                lines_rf = self.all_data_maps['cavities'].as_tao(pvdata)   
            else:
                lines_quads += self.all_data_maps[dm_key].as_tao(pvdata)
        if 'DES' in self.data_source and 'cu' in self.beam_path:
            new_lines = []
            for cmd in lines_rf:
                if 'in_use' in cmd:
                    if 'K21_1' in cmd or 'K21_2' in cmd:
                        new_lines.append(cmd)  # L1 always on Beam Code 1
                        continue
                    ele = cmd.split()[2]
                    [sector, station] = ele[1:].split('_')
                    pv = f'KLYS:LI{sector}:{station}1:BEAMCODE{self.beam_code}_STAT'
                    cmd_words = cmd.split()
                    cmd_words[-1] = str(pvdata[pv])
                    new_lines.append(' '.join(cmd_words))
                else:
                    new_lines.append(cmd)
            lines_rf = new_lines
        return lines_rf + lines_quads

    def use_klys_when_beam_off(self, tao_cmds, pvdata, beam_code = '1'):
        """Modifies tao_cmds, in_use set to 1 if station active on beam_code""" 
        #use = {}
        new_cmd = []
        for cmd in tao_cmds:
            if in_use in cmd:
                ele = cmd.split()[2]
                [sector, station] = ele[1:].split('_')
                pv = f'KLYS:LI{sector}:{station}1:BEAMCODE{beam_code}_STAT'
                #use[ele] = pvdata[pv]
                cmd_words = cmd.split()
                cmd_words[-1]=pvdata[pv]
                new_cmd.append(' '.join(cmd_words))
            else:
                new_cmd.append(cmd)
        return new_cmd

    def get_machine_values(self, pv_list):
        """ Returns pvdata, a dictionary with keys containing
        the PV name and values from Actual, Desired or Archive """     
        if self.data_source in ['DES', 'ACT']:
            pvdata = self.get_live(pv_list)
        elif 'ARCHIVE' in self.data_source:
            pvdata = lcls_archiver_restore(pv_list, self.date_time)
        return pvdata

    def tc(self, tao, cmd):
        """Prints result of tao.cmd() one line at a time"""
        result = tao.cmd(cmd)
        [print(l) for l in result]

    def update_energy_gain(self, tao, pvdata, region):
        """Updates energy gain profile based on bending magnets, 
        calculates a fudge and 
        modifies model's cavity amplitudes and phases"""
        
        if 'sc' in self.beam_path:
            cavities = tao.lat_list(f'LCAV::BEG{region}:END{region}','ele.name')
            for indx, cav in enumerate(cavities):
                cavities[indx] = cav.split('#')[0]
            cavities = list(set(cavities))
            devices = [tao.ele_head(element)['alias'] for element in cavities]
            if self.data_source == 'ACT':
                attr = 'ACTMEAN'
            elif self.data_source in ['DES', 'ARCHIVE']:
                attr = 'DES'
            ampl = [pvdata[dev + ':A' + attr] for dev in devices]   
            phas = [pvdata[dev + ':P' + attr] for dev in devices]
            amplNp = np.array(ampl)
            amplNp = np.where(amplNp < 0.5, 0, amplNp)
            phasNp = np.array(np.deg2rad(phas))
            gainMeasured  = amplNp * np.cos(phasNp)
            if region == 'L2B':
                #expected_gain = 1000*(epics.caget('REFS:BC2B:500:EDES') -  epics.caget('REFS:BC1B:400:EDES'))
                expected_gain = 1000 * (pvdata['REFS:BC2B:500:EDES'] -  pvdata['REFS:BC1B:400:EDES'])
            elif region == 'L3B':
                #expected_gain =  1000*(epics.caget('REFS:DMPS:400:EDES') - epics.caget('REFS:BC2B:500:EDES'))
                expected_gain =  1000*(pvdata['REFS:DMPS:400:EDES'] - pvdata['REFS:BC2B:500:EDES'])

            dF = (expected_gain - sum(gainMeasured)) / sum(ampl)
            fudge = 1 + dF
            complexGain = amplNp * np.exp(1j * phasNp)
            complexGainFudged = complexGain + amplNp * dF
            amplF = np.abs(complexGainFudged)
            phasF = np.degrees(np.angle(complexGainFudged))
            pvdata_fudge = dict()
            pvdata_reg = dict()
            for indx, pv in enumerate(devices):
                pvdata_fudge[f'{pv}:PACTMEAN'] = phasF[indx]
                pvdata_fudge[f'{pv}:AACTMEAN'] = amplF[indx]
                pvdata_reg[f'{pv}:P{attr}'] = phasF[indx]
                pvdata_reg[f'{pv}:A{attr}'] = amplF[indx]
            data_map = {'cavities': self.all_data_maps['cavities']}
            #datamap['quad'] =  self.all_data_maps['quad']}
            
            tao_cmds = self.get_tao_cmds(pvdata_reg, data_map)
            self.evaluate_tao(tao, tao_cmds)
            region_e_tot = tao.ele_gen_attribs(f'END{region}')['E_TOT']/1E9 
            print(region_e_tot)
            #return ampl, phas, amplF, phasF, pvdata_reg, tao_cmds, devices, data_map

        if 'cu' in self.beam_path:
            #tao.cmd(f'set dat BC1.energy[2]|meas ={pvdata["BEND:LI21:231:EDES"] * 1E9} ')
            #tao.cmd(f'set dat BC2.energy[2]|meas ={pvdata["BEND:LI24:790:EDES"] * 1E9} ')
            #tao.cmd(f'set dat L3[2]|meas ={pvdata["BEND:DMPH:400:EDES"] * 1E9} ')
            if region == 'L2':
                l2_edes = pvdata['BEND:LI24:790:EDES'] *1E9
                tao.cmd(f'set dat BC1.energy[2]|meas ={l2_edes} ')
                tao.cmds(['veto dat *', 'veto var *', 'use dat BC2.energy[1]', 
                'use var linac_fudge[2]'])
            if region == 'L3':
                if 'hxr' in self.beam_path:
                    l3_edes = pvdata['BEND:DMPH:400:EDES'] *1E9
                elif 'sxr' in self.beam_path:
                    l3_edes = pvdata['BEND:DMPS:400:EDES'] *1E9
                tao.cmd(f'set dat L3[2]|meas ={l3_edes} ')
                tao.cmds(['veto dat *', 'veto var *', 'use dat L3.energy[2]',
                'use var linac_fudge[3]'])
            r = tao.cmd('run')
            print(r)
            for line in tao.cmd('show merit'):
                print(line)

    def get_tao_cmds(self, pvdata, data_maps):
        """Returns command lines to update the Bmad model with Tao
        where element values come from pvdata"""
        lines = []
        for dm_key in data_maps.keys():
            lines +=  data_maps[dm_key].as_tao(pvdata)
        return lines

    def get_live(self,pvlist):
        """Returns dictionary with PV names as keys and values of PVs"""
        return dict(zip(pvlist, epics.caget_many(pvlist)))

    def evaluate_tao(self, tao, tao_cmds):
        """Evaluate set of tao command, toggles lattice_calculation OFF/ON 
        in between command list"""
        tao.cmd('set global lattice_calc_on = F')
        tao.cmds(tao_cmds)
        tao.cmd('set global lattice_calc_on = T')
        output = self.get_output(tao)
        return output

    def kmod_to_bdes(self, tao, element, K=0):
        """Returns BDES given K1 in the Bmad model"""
        ele = tao.ele_gen_attribs(element)
        bp = ele['E_TOT'] / 1E9 / 299.792458*1e4  # kG m
        return ele['K1'] * bp * ele['L'] 

    def bdes_to_kmod(self, tao, element, bdes):
        """Returns K1 given BDES"""
        ele = tao.ele_gen_attribs(element)
        bp = ele['E_TOT'] / 1E9  / 299.792458*1e4;  # kG m
        return bdes / ele['L'] / bp  # kG / m / kG m = 1/m^2

    def plot_betas(self, output1, output2, **kwargs):
        """Generates two figures with betas X and Y for two output runs"""
        self.plot_beta_options = {
            "title1":'',
            "title2":'',
            "label1":'Design',
            "label2":'Model',
            "figsize": (8,4)
            }
        self.plot_beta_options.update(kwargs)
        opt = self.plot_beta_options
        fig1, ax1 = plt.subplots(figsize=(8,4))
        ax1.plot(output1['ele.s'], output1['ele.a.beta'], label = opt['label1'], linestyle = '--')
        ax1.plot(output2['ele.s'], output2['ele.a.beta'], label = opt['label2'])
        plt.legend()
        # Add energy to the rhs
        ax12 = ax1.twinx()
        ax12.plot(output2['ele.s'], output2['ele.e_tot']/1e9, color='red')
        ax12.set_ylabel('Energy (GeV)')
        efinal = output2['ele.e_tot'][-1]/1e9
        plt.title(f'{opt["title1"]} Final energy: {efinal:.2f} GeV')
        ax1.set_xlabel('s (m)')
        ax1.set_ylabel('Twiss Beta X (m)')
        #itime = isotime()
        fig2, ax2 = plt.subplots(figsize=(8,4))    
        ax2.plot(output1['ele.s'], output1['ele.b.beta'], label = opt['label1'], linestyle = '--')
        ax2.plot(output2['ele.s'], output2['ele.b.beta'], label = opt['label2'])
        plt.legend()
        ax22 = ax2.twinx()
        ax22.plot(output2['ele.s'], output2['ele.e_tot']/1e9, color='red')
        ax22.set_ylabel('Energy (GeV)')
        plt.title(f'{opt["title2"]} Final energy: {efinal:.2f} GeV')
        ax2.set_xlabel('s (m)')
        ax2.set_ylabel('Twiss Beta Y (m)')
        axes_list = [ax1, ax12, ax2, ax22]
        fig1.show()
        fig2.show()
        return fig1, fig2, axes_list

    def get_output(self, tao):
        """Returns dictionary of modeled parameters, including element name, twiss and Rmats"""
        # Output collecting
        outkeys = [
        'ele.name',
        'ele.ix_ele',
        'ele.ix_branch',
        'ele.a.beta',
        'ele.a.alpha',
        'ele.a.eta',
        'ele.a.etap',
        'ele.a.gamma',
        'ele.a.phi',
        'ele.b.beta',
        'ele.b.alpha',
        'ele.b.eta',
        'ele.b.etap',
        'ele.b.gamma',
        'ele.b.phi',
        'ele.x.eta',
        'ele.x.etap',
        'ele.y.eta',
        'ele.y.etap',
        'ele.s',
        'ele.l',
        'ele.e_tot',
        'ele.p0c',
        'ele.mat6',
        'ele.vec0']
        output = {k:tao.lat_list('*', k) for k in outkeys}
        return output

    def get_element(self, tao,  datum):
        return tao.data_parameter(datum,'ele_name')[0].split(';')[1]

    def update_datum_meas(self, tao, datum, useDesing = True):
        """Updates datum with EPICS or design twiss values"""
        element = self.get_element(tao, datum) 
        TWISS =  ["beta_a" , "alpha_a", "beta_b", "alpha_b"]
        cmd = []
        if useDesing:
            ele_twiss = tao.ele_twiss(element,which='design')
            for ii, p in enumerate(TWISS):
                cmd.append(f'set dat {datum}[{ii+1}]|meas = {ele_twiss[p]}')          
        else:
            device = tao.ele_head(element)['alias']
            EPICS_ATTRIBUTE = ["BETA_X" , "ALPHA_X", "BETA_Y", "ALPHA_Y"]
            pvs = [device + ':' + twiss for twiss in EPICS_ATTRIBUTE]
            measured = self.get_live(pvs)
            for ii, pv in enumerate(pvs):
                cmd.append(f'set dat {datum}[{ii+1}]|meas = {measured[pvs[ii]]}')  
        tao.cmds(cmd)
        self.tc(tao, f'show dat {datum}')

    def match_twiss(self, tao,  variable, datum):
        match_cmds = ['veto var *', 'veto dat *@*', 'set global n_opti_cycles = 912']
        match_cmds.append(f'use var {variable}[1:4]')
        match_cmds.append(f'use dat {datum}[1:4]')
        tao.cmds(match_cmds)
        tao.cmd('run')
        element = self.get_element(tao, datum) 
        self.show_twiss(tao, element,[])

    def get_twiss(self, tao, element, which = 'design'):
        """Gets twiss for element, which can be model, desing or base"""
        result = tao.ele_twiss(element, which = which)
        return [result[p] for p in ['beta_a', 'alpha_a', 'beta_b', 'alpha_b']]

    def bmag(self, twiss, twiss_reference):
        """Calculates BMAG from imput twiss and reference twiss"""
        beta_a, alpha_a, beta_b, alpha_b = twiss
        beta_a_ref,  alpha_a_ref, beta_b_ref, alpha_b_ref = twiss_reference
        bmag_a = self.bmag_func(beta_a, alpha_a, beta_a_ref, alpha_a_ref)
        bmag_b = self.bmag_func(beta_b, alpha_b, beta_b_ref, alpha_b_ref)
        return (bmag_a, bmag_b)

    def bmag_func(self, bb,ab,bl,al):
        return 1/2 * (bl/bb + bb/bl + bb*bl*(ab/bb - al/bl)**2)

    def show_twiss(self, tao, element, datum=[]):
        parameters = ['beta_a', 'alpha_a', 'beta_b', 'alpha_b']
        if not datum == []:
            result_datum = tao.data_parameter(datum, 'meas_value')[0].split(';')[1:]
        twiss_model = self.get_twiss(tao, element, which = 'model')
        twiss_design = self.get_twiss(tao, element)
        bmag_a, bmag_b = self.bmag(twiss_model, twiss_design)
        print(f'\n{element} BMAG_X {bmag_a:3.2f}, BMAG_Y {bmag_b:3.2f} ')
        print(f'{" " * 12} Beta     Alpha   Beta   Alpha ')
        print(f'{" " * 12}  X       X       Y       Y')
        print(f'Desing:{" "} ', end='')
        for val in twiss_design:
            print(f'{val:8.2f}', end='')
        print('')
        print(f'Model:{" " *3}', end='')
        for val in twiss_model:
            print(f'{val:8.2f}', end='')
        print('')
        if not datum == []:
            print(f'Measured:{" " * 0}', end='')
            for val in result_datum:
                print(f'{float(val):8.2f}', end='')
        print('')
 
    def quad_table(self,tao, pct_lim = 1, show_energy = False):
        """Display table of quad elements BDES, BMOD, Bmad model BDES and  Bamd model energy.  Filter
        by pct_lim (BMOD - Bmad model)/ BMOD"""
        quads = tao.lat_list('quad::Q*','ele.name',flags='-no_slaves')
        if show_energy:
            print(f'Ele.    Device            EACT    EDES    E_TOT    ')
        else:
            print(f'Ele.    Device           BDES    BMOD    Bmad     %')
        for element in quads[1:]:
            device =  tao.ele_head(element)['alias']
            bmod = epics.caget(device + ':BMOD')
            bdes = epics.caget(device + ':BDES')
            eact = epics.caget(device + ':EACT')
            edes = epics.caget(device + ':EDES')
            e_tot = tao.ele_gen_attribs(element)['E_TOT']/1E9
            model_bdes = self.get_bmad_bdes(tao, element)
            if show_energy:
                print(f'{element:7s} {device:15s} {eact:7.3f} {e_tot:7.3f} {edes:7.3f}')
            else:
                percent = 100 * abs((bmod - model_bdes)/bmod) if bmod != 0 else 0
                if percent > pct_lim:
                    print(f'{element:7s} {device:15s} {bdes:7.3f} {bmod:7.3f} {model_bdes:7.3f} {percent:7.3}')

    def get_bmad_bdes(self, tao, element, b1_gradient=[]):
        """Returns BDES from Bmad B1_GRADIENT or given gradient"""
        ele_attr = tao.ele_gen_attribs(element)
        if not b1_gradient:
            b1_gradient = ele_attr['B1_GRADIENT']
        return -b1_gradient * ele_attr['L'] * 10

    def create_emitmeas_datum(self,tao, element):
        tao.cmd('set global lattice_calc_on = F')
        tao.data_d2_create(f'emitmeas{element}', 1, 'twiss^^1^^4')
        tao.datum_create(f'emitmeas{element}.twiss[1]','beta.a',ele_name= element, merit_type='target', weight=10)
        tao.datum_create(f'emitmeas{element}.twiss[2]','alpha.a',ele_name= element, merit_type='target', weight=10)
        tao.datum_create(f'emitmeas{element}.twiss[3]','beta.b',ele_name= element, merit_type='target', weight=10)
        tao.datum_create(f'emitmeas{element}.twiss[4]','alpha.b',ele_name= element, merit_type='target', weight=10)
        tao.data_set_design_value()
        tao.cmd('set global lattice_calc_on = T')

 
    def plot_twiss(self, tao, output, info='', xoff = 0):
        fig, ax = plt.subplots(figsize=(8,4))
        ax.plot(output['ele.s'], output['ele.a.beta'], label = r'$\beta_a$')
        ax.plot(output['ele.s'], output['ele.b.beta'], label = r'$\beta_b$')
        plt.legend()
        # Add energy to the rhs
        ax2 = ax.twinx()
        ax2.plot(output['ele.s'], output['ele.e_tot']/1e9, color='red')
        ax2.set_ylabel('Energy (GeV)')
        ax.set_xlabel('s (m)')
        ax.set_ylabel('Twiss Beta (m)')
        efinal = output['ele.e_tot'][-1]/1e9
        plt.title(f'{info} Final energy: {efinal:.2f} GeV')
        quads = tao.lat_list('quad::Q*','ele.name',flags='-no_slaves')
        for q in quads:
            plt.text(tao.ele_head(q)['s'], -30, q, rotation=90, ha='center', va='center',fontsize=8, transform=ax.transData)
        fig.show()
        return fig

"""

match_cmds = ['veto var *', 'veto dat *@*', f'set global n_opti_cycles = {n_opti_cycles}']
match_cmds.append(f'use var {variable}[1:4]')
match_cmds.append(f'use dat {datum}[1:4]')
tao.cmds(match_cmds)
tc('run')
element = self.get_element(datum) 

bm.print_twiss(tao, element,[])
if matchAt == 'OTR2':
    self.print_twiss(tao,'OTR2', 'OTR2.match_twiss')
if matchAt == 'BEGL3B':
    print_twiss(tao,'BEGL3B', 'BEGL3B')
O = get_output(tao)
figs = plot_betas(O_design, O)
figs[0].show()
figs[1].show()


"""
