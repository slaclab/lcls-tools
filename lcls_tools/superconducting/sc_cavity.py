from datetime import datetime
from time import sleep
from typing import Optional, Callable, TYPE_CHECKING

from lcls_tools.common.controls.epics import PV, EPICS_INVALID_VAL
from lcls_tools.superconducting import sc_linac_utils as utils

if TYPE_CHECKING:
    from lcls_tools.superconducting.sc_linac import Linac
    from lcls_tools.superconducting.sc_cryomodule import Cryomodule

    from lcls_tools.superconducting.sc_piezo import Piezo
    from lcls_tools.superconducting.sc_rack import Rack
    from lcls_tools.superconducting.sc_ssa import SSA
    from lcls_tools.superconducting.sc_stepper import StepperTuner


class Cavity(utils.SCLinacObject):
    """
    Python representation of LCLS II cavities. This class provides utility
    functions for commonly used tasks including powering on/off, changing RF mode,
    setting amplitude, characterizing, and tuning to resonance

    """

    def __init__(self, cavity_num: int, rack_object: "Rack"):
        """
        @param cavity_num: int cavity number i.e. 1 - 8
        @param rack_object: the rack object the cavities belong to
        """

        self.number: int = cavity_num
        self.rack: Rack = rack_object
        self.cryomodule: "Cryomodule" = self.rack.cryomodule
        self.linac: "Linac" = self.cryomodule.linac

        if self.cryomodule.is_harmonic_linearizer:
            self.length = 0.346
            self.frequency = 3.9e9
            self.loaded_q_lower_limit = utils.LOADED_Q_LOWER_LIMIT_HL
            self.loaded_q_upper_limit = utils.LOADED_Q_UPPER_LIMIT_HL
            self.scale_factor_lower_limit = utils.CAVITY_SCALE_LOWER_LIMIT_HL
            self.scale_factor_upper_limit = utils.CAVITY_SCALE_UPPER_LIMIT_HL
        else:
            self.length = 1.038
            self.frequency = 1.3e9
            self.loaded_q_lower_limit = utils.LOADED_Q_LOWER_LIMIT
            self.loaded_q_upper_limit = utils.LOADED_Q_UPPER_LIMIT
            self.scale_factor_lower_limit = utils.CAVITY_SCALE_LOWER_LIMIT
            self.scale_factor_upper_limit = utils.CAVITY_SCALE_UPPER_LIMIT

        self._pv_prefix = "ACCL:{LINAC}:{CRYOMODULE}{CAVITY}0:".format(
            LINAC=self.linac.name, CRYOMODULE=self.cryomodule.name, CAVITY=self.number
        )

        self.ctePrefix = "CTE:CM{cm}:1{cav}".format(
            cm=self.cryomodule.name, cav=self.number
        )

        self.chirp_prefix = self._pv_prefix + "CHIRP:"
        self.abort_flag: bool = False

        # These need to be created after all the base cavity properties are defined
        self.ssa: "SSA" = self.rack.ssa_class(cavity=self)
        self.stepper_tuner: "StepperTuner" = self.rack.stepper_class(cavity=self)
        self.piezo: "Piezo" = self.rack.piezo_class(cavity=self)

        self._calc_probe_q_pv_obj: Optional[PV] = None
        self.calc_probe_q_pv: str = self.pv_addr("QPROBE_CALC1.PROC")

        self._push_ssa_slope_pv_obj: Optional[PV] = None
        self.push_ssa_slope_pv: str = self.pv_addr("PUSH_SSA_SLOPE.PROC")

        self.save_ssa_slope_pv: str = self.pv_addr("SAVE_SSA_SLOPE.PROC")
        self._save_ssa_slope_pv_obj: Optional[PV] = None

        self.interlock_reset_pv: str = self.pv_addr("INTLK_RESET_ALL")
        self._interlock_reset_pv_obj: Optional[PV] = None

        self.drive_level_pv: str = self.pv_addr("SEL_ASET")
        self._drive_level_pv_obj: Optional[PV] = None

        self.characterization_start_pv: str = self.pv_addr("PROBECALSTRT")
        self._characterization_start_pv_obj: Optional[PV] = None

        self.characterization_status_pv: str = self.pv_addr("PROBECALSTS")
        self._characterization_status_pv_obj: Optional[PV] = None

        self.current_q_loaded_pv: str = self.pv_addr("QLOADED")

        self.measured_loaded_q_pv: str = self.pv_addr("QLOADED_NEW")
        self._measured_loaded_q_pv_obj: Optional[PV] = None

        self.push_loaded_q_pv: str = self.pv_addr("PUSH_QLOADED.PROC")
        self._push_loaded_q_pv_obj: Optional[PV] = None

        self.save_q_loaded_pv: str = self.pv_addr("SAVE_QLOADED.PROC")

        self.current_cavity_scale_pv: str = self.pv_addr("CAV:SCALER_SEL.B")

        self.measured_scale_factor_pv: str = self.pv_addr("CAV:CAL_SCALEB_NEW")
        self._measured_scale_factor_pv_obj: Optional[PV] = None

        self.push_scale_factor_pv: str = self.pv_addr("PUSH_CAV_SCALE.PROC")
        self._push_scale_factor_pv_obj: Optional[PV] = None

        self.save_cavity_scale_pv: str = self.pv_addr("SAVE_CAV_SCALE.PROC")

        self.ades_pv: str = self.pv_addr("ADES")
        self._ades_pv_obj: Optional[PV] = None

        self.acon_pv: str = self.pv_addr("ACON")
        self._acon_pv_obj: Optional[PV] = None

        self.aact_pv: str = self.pv_addr("AACTMEAN")
        self._aact_pv_obj: Optional[PV] = None

        self.ades_max_pv: str = self.pv_addr("ADES_MAX")
        self._ades_max_pv_obj: Optional[PV] = None

        self.rf_mode_ctrl_pv: str = self.pv_addr("RFMODECTRL")
        self._rf_mode_ctrl_pv_obj: Optional[PV] = None

        self.rf_mode_pv: str = self.pv_addr("RFMODE")
        self._rf_mode_pv_obj: Optional[PV] = None

        self.rf_state_pv: str = self.pv_addr("RFSTATE")
        self._rf_state_pv_obj: Optional[PV] = None

        self.rf_control_pv: str = self.pv_addr("RFCTRL")
        self._rf_control_pv_obj: Optional[PV] = None

        self.pulse_go_pv: str = self.pv_addr("PULSE_DIFF_SUM")
        self._pulse_go_pv_obj: Optional[PV] = None

        self.pulse_status_pv: str = self.pv_addr("PULSE_STATUS")
        self._pulse_status_pv_obj: Optional[PV] = None

        self.pulse_on_time_pv: str = self.pv_addr("PULSE_ONTIME")
        self._pulse_on_time_pv_obj: Optional[PV] = None

        self.rev_waveform_pv: str = self.pv_addr("REV:AWF")
        self.fwd_waveform_pv: str = self.pv_addr("FWD:AWF")
        self.cav_waveform_pv: str = self.pv_addr("CAV:AWF")

        self.stepper_temp_pv: str = self.pv_addr("STEPTEMP")

        self.detune_best_pv: str = self.pv_addr("DFBEST")
        self._detune_best_pv_obj: Optional[PV] = None

        self.detune_chirp_pv: str = self.pv_addr("CHIRP:DF")
        self._detune_chirp_pv_obj: Optional[PV] = None

        self.rf_permit_pv: str = self.pv_addr("RFPERMIT")
        self._rf_permit_pv_obj: Optional[PV] = None

        self.quench_latch_pv: str = self.pv_addr("QUENCH_LTCH")
        self._quench_latch_pv_obj: Optional[PV] = None

        self.quench_bypass_pv: str = self.pv_addr("QUENCH_BYP")

        self.cw_data_decimation_pv: str = self.pv_addr("ACQ_DECIM_SEL.A")
        self._cw_data_decim_pv_obj: Optional[PV] = None

        self.pulsed_data_decimation_pv: str = self.pv_addr("ACQ_DECIM_SEL.C")
        self._pulsed_data_decim_pv_obj: Optional[PV] = None

        self.tune_config_pv: str = self.pv_addr("TUNE_CONFIG")
        self._tune_config_pv_obj: Optional[PV] = None

        self.chirp_freq_start_pv: str = self.chirp_prefix + "FREQ_START"
        self._chirp_freq_start_pv_obj: Optional[PV] = None

        self.freq_stop_pv: str = self.chirp_prefix + "FREQ_STOP"
        self._freq_stop_pv_obj: Optional[PV] = None

        self.hw_mode_pv: str = self.pv_addr("HWMODE")
        self._hw_mode_pv_obj: Optional[PV] = None

        self.char_timestamp_pv: str = self.pv_addr("PROBECALTS")
        self._char_timestamp_pv_obj: Optional[PV] = None

    def __str__(self):
        return f"{self.linac.name} CM{self.cryomodule.name} Cavity {self.number}"

    @property
    def pv_prefix(self):
        return self._pv_prefix

    @property
    def microsteps_per_hz(self):
        return 1 / self.stepper_tuner.hz_per_microstep

    def start_characterization(self):
        if not self._characterization_start_pv_obj:
            self._characterization_start_pv_obj = PV(self.characterization_start_pv)
        self._characterization_start_pv_obj.put(1)

    @property
    def cw_data_decimation_pv_obj(self) -> PV:
        if not self._cw_data_decim_pv_obj:
            self._cw_data_decim_pv_obj = PV(self.cw_data_decimation_pv)
        return self._cw_data_decim_pv_obj

    @property
    def cw_data_decimation(self):
        return self.cw_data_decimation_pv_obj.get()

    @cw_data_decimation.setter
    def cw_data_decimation(self, value: float):
        self.cw_data_decimation_pv_obj.put(value)

    @property
    def pulsed_data_decimation_pv_obj(self) -> PV:
        if not self._pulsed_data_decim_pv_obj:
            self._pulsed_data_decim_pv_obj = PV(self.pulsed_data_decimation_pv)
        return self._pulsed_data_decim_pv_obj

    @property
    def pulsed_data_decimation(self):
        return self.pulsed_data_decimation_pv_obj.get()

    @pulsed_data_decimation.setter
    def pulsed_data_decimation(self, value):
        self.pulsed_data_decimation_pv_obj.put(value)

    @property
    def rf_control_pv_obj(self) -> PV:
        if not self._rf_control_pv_obj:
            self._rf_control_pv_obj = PV(self.rf_control_pv)
        return self._rf_control_pv_obj

    @property
    def rf_control(self):
        return self.rf_control_pv_obj.get()

    @rf_control.setter
    def rf_control(self, value):
        self.rf_control_pv_obj.put(value)

    @property
    def rf_mode(self):
        if not self._rf_mode_pv_obj:
            self._rf_mode_pv_obj = PV(self.rf_mode_pv)
        return self._rf_mode_pv_obj.get()

    @property
    def rf_mode_ctrl_pv_obj(self) -> PV:
        if not self._rf_mode_ctrl_pv_obj:
            self._rf_mode_ctrl_pv_obj = PV(self.rf_mode_ctrl_pv)
        return self._rf_mode_ctrl_pv_obj

    def set_chirp_mode(self):
        self.rf_mode_ctrl_pv_obj.put(utils.RF_MODE_CHIRP)

    def set_sel_mode(self):
        self.rf_mode_ctrl_pv_obj.put(utils.RF_MODE_SEL)

    def set_sela_mode(self):
        self.rf_mode_ctrl_pv_obj.put(utils.RF_MODE_SELA)

    def set_selap_mode(self):
        self.rf_mode_ctrl_pv_obj.put(utils.RF_MODE_SELAP, use_caput=False)

    @property
    def drive_level_pv_obj(self):
        if not self._drive_level_pv_obj:
            self._drive_level_pv_obj = PV(self.drive_level_pv)
        return self._drive_level_pv_obj

    @property
    def drive_level(self):
        return self.drive_level_pv_obj.get()

    @drive_level.setter
    def drive_level(self, value):
        self.drive_level_pv_obj.put(value)

    def push_ssa_slope(self):
        if not self._push_ssa_slope_pv_obj:
            self._push_ssa_slope_pv_obj = PV(self._pv_prefix + "PUSH_SSA_SLOPE.PROC")
        self._push_ssa_slope_pv_obj.put(1)

    def save_ssa_slope(self):
        if not self._save_ssa_slope_pv_obj:
            self._save_ssa_slope_pv_obj = PV(self.save_ssa_slope_pv)
        self._save_ssa_slope_pv_obj.put(1)

    @property
    def measured_loaded_q(self) -> float:
        if not self._measured_loaded_q_pv_obj:
            self._measured_loaded_q_pv_obj = PV(self.measured_loaded_q_pv)
        return self._measured_loaded_q_pv_obj.get()

    @property
    def measured_loaded_q_in_tolerance(self) -> bool:
        return (
            self.loaded_q_lower_limit
            <= self.measured_loaded_q
            <= self.loaded_q_upper_limit
        )

    def push_loaded_q(self):
        if not self._push_loaded_q_pv_obj:
            self._push_loaded_q_pv_obj = PV(self.push_loaded_q_pv)
        self._push_loaded_q_pv_obj.put(1)

    @property
    def measured_scale_factor(self) -> float:
        if not self._measured_scale_factor_pv_obj:
            self._measured_scale_factor_pv_obj = PV(self.measured_scale_factor_pv)
        return self._measured_scale_factor_pv_obj.get()

    @property
    def measured_scale_factor_in_tolerance(self) -> bool:
        return (
            self.scale_factor_lower_limit
            <= self.measured_scale_factor
            <= self.scale_factor_upper_limit
        )

    def push_scale_factor(self):
        if not self._push_scale_factor_pv_obj:
            self._push_scale_factor_pv_obj = PV(self.push_scale_factor_pv)
        self._push_scale_factor_pv_obj.put(1)

    @property
    def characterization_status(self):
        if not self._characterization_status_pv_obj:
            self._characterization_status_pv_obj = PV(self.characterization_status_pv)
        return self._characterization_status_pv_obj.get()

    @property
    def characterization_running(self) -> bool:
        return self.characterization_status == utils.CHARACTERIZATION_RUNNING_VALUE

    @property
    def characterization_crashed(self) -> bool:
        return self.characterization_status == utils.CHARACTERIZATION_CRASHED_VALUE

    @property
    def pulse_on_time(self):
        if not self._pulse_on_time_pv_obj:
            self._pulse_on_time_pv_obj = PV(self.pulse_on_time_pv)
        return self._pulse_on_time_pv_obj.get()

    @pulse_on_time.setter
    def pulse_on_time(self, value: int):
        if not self._pulse_on_time_pv_obj:
            self._pulse_on_time_pv_obj = PV(self.pulse_on_time_pv)
        self._pulse_on_time_pv_obj.put(value)

    @property
    def pulse_status(self):
        if not self._pulse_status_pv_obj:
            self._pulse_status_pv_obj = PV(self.pulse_status_pv)
        return self._pulse_status_pv_obj.get()

    @property
    def rf_permit(self):
        if not self._rf_permit_pv_obj:
            self._rf_permit_pv_obj = PV(self.rf_permit_pv)
        return self._rf_permit_pv_obj.get()

    @property
    def rf_inhibited(self) -> bool:
        return self.rf_permit == 0

    @property
    def ades(self):
        if not self._ades_pv_obj:
            self._ades_pv_obj = PV(self.ades_pv)
        return self._ades_pv_obj.get(use_caget=False)

    @ades.setter
    def ades(self, value: float):
        if not self._ades_pv_obj:
            self._ades_pv_obj = PV(self._pv_prefix + "ADES")
        self._ades_pv_obj.put(value)

    @property
    def acon(self):
        if not self._acon_pv_obj:
            self._acon_pv_obj = PV(self.acon_pv)
        return self._acon_pv_obj.get(use_caget=False)

    @acon.setter
    def acon(self, value: float):
        if not self._acon_pv_obj:
            self._acon_pv_obj = PV(self.acon_pv)
        self._acon_pv_obj.put(value)

    @property
    def aact(self):
        if not self._aact_pv_obj:
            self._aact_pv_obj = PV(self.aact_pv)
        return self._aact_pv_obj.get()

    @property
    def ades_max(self):
        if not self._ades_max_pv_obj:
            self._ades_max_pv_obj = PV(self.ades_max_pv)
        return self._ades_max_pv_obj.get()

    @property
    def edm_macro_string(self):
        rfs_map = {
            1: "1A",
            2: "1A",
            3: "2A",
            4: "2A",
            5: "1B",
            6: "1B",
            7: "2B",
            8: "2B",
        }

        rfs = rfs_map[self.number]

        r = self.rack.rack_name

        # need to remove trailing colon and zeroes to match needed format
        cm = self.cryomodule.pv_prefix[:-3]

        # "id" shadows built-in id, renaming
        macro_id = self.cryomodule.name

        ch = 2 if self.number in [2, 4] else 1

        return f"C={self.number},RFS={rfs},R={r},CM={cm},ID={macro_id},CH={ch}"

    @property
    def hw_mode(self):
        if not self._hw_mode_pv_obj:
            self._hw_mode_pv_obj = PV(self.hw_mode_pv)
        return self._hw_mode_pv_obj.get()

    @property
    def is_online(self) -> bool:
        return self.hw_mode == utils.HW_MODE_ONLINE_VALUE

    @property
    def is_offline(self) -> bool:
        return self.hw_mode == utils.HW_MODE_OFFLINE_VALUE

    @property
    def is_quenched(self) -> bool:
        if not self._quench_latch_pv_obj:
            self._quench_latch_pv_obj = PV(self.quench_latch_pv)
        return self._quench_latch_pv_obj.get() == 1

    @property
    def tune_config_pv_obj(self) -> PV:
        if not self._tune_config_pv_obj:
            self._tune_config_pv_obj = PV(self.tune_config_pv)
        return self._tune_config_pv_obj

    @property
    def chirp_freq_start_pv_obj(self) -> PV:
        if not self._chirp_freq_start_pv_obj:
            self._chirp_freq_start_pv_obj = PV(self.chirp_freq_start_pv)
        return self._chirp_freq_start_pv_obj

    @property
    def chirp_freq_start(self):
        return self.chirp_freq_start_pv_obj.get()

    @chirp_freq_start.setter
    def chirp_freq_start(self, value):
        self.chirp_freq_start_pv_obj.put(value)

    @property
    def freq_stop_pv_obj(self) -> PV:
        if not self._freq_stop_pv_obj:
            self._freq_stop_pv_obj = PV(self.freq_stop_pv)
        return self._freq_stop_pv_obj

    @property
    def chirp_freq_stop(self):
        return self.freq_stop_pv_obj.get()

    @chirp_freq_stop.setter
    def chirp_freq_stop(self, value):
        self.freq_stop_pv_obj.put(value)

    @property
    def calc_probe_q_pv_obj(self) -> PV:
        if not self._calc_probe_q_pv_obj:
            self._calc_probe_q_pv_obj = PV(self.calc_probe_q_pv)
        return self._calc_probe_q_pv_obj

    def calculate_probe_q(self):
        self.calc_probe_q_pv_obj.put(1)

    def set_chirp_range(self, offset: int):
        offset = abs(offset)
        print(f"Setting chirp range for {self} to +/- {offset} Hz")
        self.chirp_freq_start = -offset
        self.chirp_freq_stop = offset
        print(f"Chirp range set for {self}")

    @property
    def rf_state_pv_obj(self) -> PV:
        if not self._rf_state_pv_obj:
            self._rf_state_pv_obj = PV(self.rf_state_pv)
        return self._rf_state_pv_obj

    @property
    def rf_state(self):
        """This property is read only"""
        return self.rf_state_pv_obj.get()

    @property
    def is_on(self):
        return self.rf_state == 1

    def delta_piezo(self):
        delta_volts = self.piezo.voltage - utils.PIEZO_CENTER_VOLTAGE
        delta_hz = delta_volts * utils.PIEZO_HZ_PER_VOLT
        print(f"{self} piezo detune: {delta_hz}")
        return delta_hz if not self.cryomodule.is_harmonic_linearizer else -delta_hz

    def move_to_resonance(self, reset_signed_steps=False, use_sela=False):
        def delta_detune():
            return self.detune

        self.setup_tuning(use_sela=use_sela)
        print(f"Tuning {self} to resonance in " + ("SELA" if use_sela else "chirp"))
        self._auto_tune(
            delta_hz_func=delta_detune,
            tolerance=(500 if self.cryomodule.is_harmonic_linearizer else 50),
            reset_signed_steps=reset_signed_steps,
        )

        if use_sela:
            print(f"Centering {self} piezo")
            self._auto_tune(
                delta_hz_func=self.delta_piezo,
                tolerance=100,
                reset_signed_steps=False,
            )

        self.tune_config_pv_obj.put(utils.TUNE_CONFIG_RESONANCE_VALUE)

    @property
    def detune_best_pv_obj(self) -> PV:
        if not self._detune_best_pv_obj:
            self._detune_best_pv_obj = PV(self.detune_best_pv)
        return self._detune_best_pv_obj

    @property
    def detune_chirp_pv_obj(self) -> PV:
        if not self._detune_chirp_pv_obj:
            self._detune_chirp_pv_obj = PV(self.detune_chirp_pv)
        return self._detune_chirp_pv_obj

    @property
    def detune_best(self):
        return self.detune_best_pv_obj.get()

    @property
    def detune_chirp(self):
        return self.detune_chirp_pv_obj.get()

    @property
    def detune(self):
        if self.rf_mode == utils.RF_MODE_CHIRP:
            return self.detune_chirp
        else:
            return self.detune_best

    @property
    def detune_invalid(self) -> bool:
        if self.rf_mode == utils.RF_MODE_CHIRP:
            return self.detune_chirp_pv_obj.severity == EPICS_INVALID_VAL
        else:
            return self.detune_best_pv_obj.severity == EPICS_INVALID_VAL

    def _auto_tune(
        self,
        delta_hz_func: Callable,
        tolerance: int = 50,
        reset_signed_steps: bool = False,
    ):
        if self.detune_invalid:
            raise utils.DetuneError(f"Detune for {self} is invalid")

        delta_hz = delta_hz_func()
        expected_steps: int = abs(int(delta_hz * self.microsteps_per_hz))

        stepper_tol_factor = utils.stepper_tol_factor(expected_steps)

        steps_moved: int = 0

        if reset_signed_steps:
            self.stepper_tuner.reset_signed_steps()

        self.tune_config_pv_obj.put(utils.TUNE_CONFIG_OTHER_VALUE)

        while abs(delta_hz) > tolerance:
            self.check_abort()
            est_steps = int(0.9 * delta_hz * self.microsteps_per_hz)

            print(f"Moving stepper for {self} {est_steps} steps")

            self.stepper_tuner.move(
                est_steps,
                max_steps=int(abs(est_steps) * 1.1),
                speed=utils.MAX_STEPPER_SPEED,
            )

            steps_moved += abs(est_steps)

            if steps_moved > expected_steps * stepper_tol_factor:
                raise utils.DetuneError(f"{self} motor moved more steps than expected")

            # this should catch if the chirp range is wrong or if the cavity is off
            self.check_detune()

            delta_hz = delta_hz_func()

    def check_detune(self):
        if self.detune_invalid:
            if self.rf_mode == utils.RF_MODE_CHIRP:
                self.find_chirp_range(self.chirp_freq_start * 1.1)
            else:
                raise utils.DetuneError(
                    f"Cannot tune {self} in SELA with invalid detune"
                )

    def check_and_set_on_time(self):
        """
        In pulsed mode the cavity has a duty cycle determined by the on time and
        off time. We want the on time to be 70 ms or else the various cavity
        parameters calculated from the waveform (e.g. the RF gradient) won't be
        accurate.
        :return:
        """
        print("Checking RF Pulse On Time...")
        if self.pulse_on_time != utils.NOMINAL_PULSED_ONTIME:
            print(
                "Setting RF Pulse On Time to {ontime} ms".format(
                    ontime=utils.NOMINAL_PULSED_ONTIME
                )
            )
            self.pulse_on_time = utils.NOMINAL_PULSED_ONTIME
            self.push_go_button()

    @property
    def pulse_go_pv_obj(self) -> PV:
        if not self._pulse_go_pv_obj:
            self._pulse_go_pv_obj = PV(self._pv_prefix + "PULSE_DIFF_SUM")
        return self._pulse_go_pv_obj

    def push_go_button(self):
        """
        Many of the changes made to a cavity don't actually take effect until the
        go button is pressed
        :return:
        """
        self._pulse_go_pv_obj.put(1)
        while self.pulse_status < 2:
            self.check_abort()
            print("waiting for pulse state", datetime.now())
            sleep(1)
        if self.pulse_status > 2:
            raise utils.PulseError("Unable to pulse cavity")

    def turn_on(self):
        print(f"Turning {self} on")
        if self.is_online:
            self.ssa.turn_on()
            self.reset_interlocks()
            self.rf_control = 1

            while not self.is_on:
                self.check_abort()
                print(f"waiting for {self} to turn on", datetime.now())
                sleep(1)

            print(f"{self} on")
        else:
            raise utils.CavityHWModeError(f"{self} not online")

    def turn_off(self):
        print(f"turning {self} off")
        self.rf_control = 0
        while self.is_on:
            self.check_abort()
            print(f"waiting for {self} to turn off")
            sleep(1)
        print(f"{self} off")

    def setup_selap(self, des_amp: float = 5):
        self.setup_rf(des_amp)
        self.set_selap_mode()
        print(f"{self} set up in SELAP")

    def setup_sela(self, des_amp: float = 5):
        self.setup_rf(des_amp)
        self.set_sela_mode()
        print(f"{self} set up in SELA")

    def check_abort(self):
        if self.abort_flag:
            self.abort_flag = False
            self.turn_off()
            raise utils.CavityAbortError(f"Abort requested for {self}")

    def setup_rf(self, des_amp):
        if des_amp > self.ades_max:
            print(
                f"Requested amplitude for {self} too high - ramping up to AMAX instead"
            )
            des_amp = self.ades_max
        print(f"setting up {self}")
        self.turn_off()
        self.ssa.calibrate(self.ssa.drive_max)
        self.move_to_resonance()

        self.characterize()
        self.calculate_probe_q()

        self.check_abort()

        self.reset_data_decimation()

        self.check_abort()

        self.ades = min(5, des_amp)
        self.set_sel_mode()
        self.piezo.enable_feedback()
        self.set_sela_mode()

        self.check_abort()

        if des_amp <= 10:
            self.walk_amp(des_amp, 0.5)

        else:
            self.walk_amp(10, 0.5)
            self.walk_amp(des_amp, 0.1)

    def reset_data_decimation(self):
        print(f"Setting data decimation for {self}")
        self.cw_data_decimation = 255
        self.pulsed_data_decimation = 255

    def setup_tuning(self, chirp_range=50000, use_sela=False):
        self.piezo.enable()

        if not use_sela:
            self.piezo.disable_feedback()

            print(f"setting {self} piezo DC voltage offset to 0V")
            self.piezo.dc_setpoint = 0

            print(f"setting {self} drive level to {utils.SAFE_PULSED_DRIVE_LEVEL}")
            self.drive_level = utils.SAFE_PULSED_DRIVE_LEVEL

            print(f"setting {self} RF to chirp")
            self.set_chirp_mode()

            print(f"turning {self} RF on and waiting 5s for detune to catch up")
            self.turn_on()
            sleep(5)
            self.find_chirp_range(chirp_range)

        else:
            self.piezo.enable_feedback()
            self.set_sela_mode()
            self.turn_on()

    def find_chirp_range(self, chirp_range=50000):
        self.check_abort()
        self.set_chirp_range(chirp_range)
        sleep(1)
        if self.detune_invalid:
            if chirp_range < 400000:
                self.find_chirp_range(int(chirp_range * 1.1))
            else:
                raise utils.DetuneError(
                    f"{self}: No valid detune found within+/-400000Hz chirp range"
                )

    def reset_interlocks(self, wait: int = 3, attempt: int = 0):
        # TODO see if it makes more sense to implement this non-recursively
        print(f"Resetting interlocks for {self} and waiting {wait}s")

        if not self._interlock_reset_pv_obj:
            self._interlock_reset_pv_obj = PV(self.interlock_reset_pv)

        self._interlock_reset_pv_obj.put(1)
        sleep(wait)

        print(f"Checking {self} RF permit")
        if self.rf_inhibited:
            if attempt >= utils.INTERLOCK_RESET_ATTEMPTS:
                raise utils.CavityFaultError(
                    f"{self} still faulted after"
                    f" {utils.INTERLOCK_RESET_ATTEMPTS} "
                    f"reset attempts"
                )
            else:
                print(f"{self} reset {attempt} unsuccessful; retrying")
                self.reset_interlocks(wait=wait + 2, attempt=attempt + 1)
        else:
            print(f"{self} interlocks reset")

    @property
    def characterization_timestamp(self) -> datetime:
        if not self._char_timestamp_pv_obj:
            self._char_timestamp_pv_obj = PV(self.char_timestamp_pv)
        date_string = self._char_timestamp_pv_obj.get(use_caget=False)
        time_readback = datetime.strptime(date_string, "%Y-%m-%d-%H:%M:%S")
        print(f"{self} characterization time is {time_readback}")
        return time_readback

    def characterize(self):
        """
        Calibrates the cavity's RF probe so that the amplitude readback will be
        accurate. Also measures the loaded Q (quality factor) of the cavity power
        coupler
        :return:
        """

        self.reset_interlocks()

        print(f"setting {self} drive to {utils.SAFE_PULSED_DRIVE_LEVEL}")
        self.drive_level = utils.SAFE_PULSED_DRIVE_LEVEL

        if (datetime.now() - self.characterization_timestamp).total_seconds() < 60:
            if self.characterization_status == 1:
                print(
                    f"{self} successful characterization within the last minute,"
                    f" not starting a new one"
                )
                self.finish_characterization()
                return

        print(f"Starting {self} cavity characterization at {datetime.now()}")
        self.start_characterization()
        sleep(2)

        while self.characterization_running:
            self.check_abort()
            print(
                f"waiting for {self} characterization to stop running",
                datetime.now(),
            )
            sleep(1)

        if self.characterization_status == utils.CALIBRATION_COMPLETE_VALUE:
            if (datetime.now() - self.characterization_timestamp).total_seconds() > 300:
                raise utils.CavityCharacterizationError(
                    f"No valid {self} characterization within the last 5 min"
                )
            self.finish_characterization()

        if self.characterization_crashed:
            raise utils.CavityCharacterizationError(f"{self} characterization crashed")

    def finish_characterization(self):
        print(f"pushing {self} characterization results")
        if self.measured_loaded_q_in_tolerance:
            self.push_loaded_q()
        else:
            raise utils.CavityQLoadedCalibrationError(
                f"{self} loaded Q out of tolerance"
            )
        if self.measured_scale_factor_in_tolerance:
            self.push_scale_factor()
        else:
            raise utils.CavityScaleFactorCalibrationError(
                f"{self} scale factor out of tolerance"
            )

        self.reset_data_decimation()
        print(f"restoring {self} piezo feedback setpoint to 0")
        self.piezo.feedback_setpoint = 0

        print(f"{self} characterization successful")

    def walk_amp(self, des_amp, step_size):
        print(f"walking {self} to {des_amp} from {self.ades}")

        while self.ades <= (des_amp - step_size):
            self.check_abort()
            if self.is_quenched:
                raise utils.QuenchError(f"{self} quench detected, aborting RF ramp")
            self.ades = self.ades + step_size
            # to avoid tripping sensitive interlock
            sleep(0.1)

        if self.ades != des_amp:
            self.ades = des_amp

        print(f"{self} at {des_amp} MV")
