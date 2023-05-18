from abc import ABC, abstractmethod

CHARACTERIZATION_CRASHED_VALUE = 0
CHARACTERIZATION_RUNNING_VALUE = 2

SSA_STATUS_ON_VALUE = 3
SSA_STATUS_FAULTED_VALUE = 1
SSA_STATUS_OFF_VALUE = 2
SSA_STATUS_RESETTING_FAULTS_VALUE = 4
SSA_STATUS_FAULT_RESET_FAILED_VALUE = 7
SSA_SLOPE_LOWER_LIMIT = 0.5
SSA_SLOPE_UPPER_LIMIT = 1.6
SSA_RESULT_GOOD_STATUS_VALUE = 0
SSA_FWD_PWR_LOWER_LIMIT = 3000
SSA_CALIBRATION_RUNNING_VALUE = 2
SSA_CALIBRATION_CRASHED_VALUE = 0

HL_SSA_MAP = {1: 1, 2: 2, 3: 3, 4: 4, 5: 1, 6: 2, 7: 3, 8: 4}

LOADED_Q_LOWER_LIMIT = 2.5e7
LOADED_Q_UPPER_LIMIT = 5.1e7
DESIGN_Q_LOADED = 4.1e7

LOADED_Q_LOWER_LIMIT_HL = 1.5e7
LOADED_Q_UPPER_LIMIT_HL = 3.5e7
DESIGN_Q_LOADED_HL = 2.5e7

CAVITY_SCALE_UPPER_LIMIT = 125
CAVITY_SCALE_LOWER_LIMIT = 10

RF_MODE_SELAP = 0
RF_MODE_SELA = 1
RF_MODE_SEL = 2
RF_MODE_SEL_RAW = 3
RF_MODE_PULSE = 4
RF_MODE_CHIRP = 5

SAFE_PULSED_DRIVE_LEVEL = 15
NOMINAL_PULSED_ONTIME = 70

STEPPER_TEMP_LIMIT = 70
DEFAULT_STEPPER_MAX_STEPS = 1000000
DEFAULT_STEPPER_SPEED = 20000
MAX_STEPPER_SPEED = 60000
STEPPER_ON_LIMIT_SWITCH_VALUE = 1

# these values are based on the list of enum states found by probing {Magnettype}:L{x}B:{cm}85:CTRL
MAGNET_RESET_VALUE = 10
MAGNET_ON_VALUE = 11
MAGNET_OFF_VALUE = 12
MAGNET_DEGAUSS_VALUE = 13
MAGNET_TRIM_VALUE = 1

PIEZO_ENABLE_VALUE = 1
PIEZO_DISABLE_VALUE = 0
PIEZO_MANUAL_VALUE = 0
PIEZO_FEEDBACK_VALUE = 1
PIEZO_SCRIPT_RUNNING_VALUE = 2
PIEZO_SCRIPT_COMPLETE_VALUE = 1
PIEZO_PRERF_CHECKOUT_PASS_VALUE = 0
PIEZO_WITH_RF_GRAD = 6.5

MICROSTEPS_PER_STEP = 256

HZ_PER_STEP = 1.4
HL_HZ_PER_STEP = 18.3

# These are very rough values obtained empirically
ESTIMATED_MICROSTEPS_PER_HZ = MICROSTEPS_PER_STEP / HZ_PER_STEP
ESTIMATED_MICROSTEPS_PER_HZ_HL = MICROSTEPS_PER_STEP / HL_HZ_PER_STEP

TUNE_CONFIG_RESONANCE_VALUE = 0
TUNE_CONFIG_COLD_VALUE = 1
TUNE_CONFIG_PARKED_VALUE = 2
TUNE_CONFIG_OTHER_VALUE = 3

HW_MODE_ONLINE_VALUE = 0
HW_MODE_MAINTENANCE_VALUE = 1
HW_MODE_OFFLINE_VALUE = 2
HW_MODE_MAIN_DONE_VALUE = 3
HW_MODE_READY_VALUE = 4

INTERLOCK_RESET_ATTEMPS = 3


class SCLinacObject(ABC, object):
    @property
    @abstractmethod
    def pv_prefix(self):
        raise NotImplementedError("SC Linac Objects should implement pv_prefix")
    
    def pv_addr(self, suffix: str):
        return self.pv_prefix + suffix


class PulseError(Exception):
    """
    Exception thrown during cavity SSA calibration
    """
    pass


class StepperError(Exception):
    """
    Exception thrown during cavity SSA calibration
    """
    pass


class SSACalibrationError(Exception):
    """
    Exception thrown during cavity SSA calibration
    """
    pass


class SSACalibrationToleranceError(Exception):
    """
    Exception thrown during cavity SSA calibration
    """
    pass


class CavityQLoadedCalibrationError(Exception):
    """
    Exception thrown during cavity loaded Q measurement
    """
    pass


class CavityScaleFactorCalibrationError(Exception):
    """
    Exception thrown during cavity scale factor calibration
    """
    pass


class SSAPowerError(Exception):
    """
    Exception thrown while trying to turn an SSA on or off
    """
    pass


class SSAFaultError(Exception):
    """
    Exception thrown while trying to turn an SSA on or off
    """
    pass


class DetuneError(Exception):
    """
    Exception thrown when the detune PV is out of tolerance or invalid
    """
    pass


class QuenchError(Exception):
    """
    Exception thrown when the quench fault is latched
    """
    pass


class StepperAbortError(Exception):
    pass


class CavityAbortError(Exception):
    pass


class CavityFaultError(Exception):
    pass


class CavityHWModeError(Exception):
    pass