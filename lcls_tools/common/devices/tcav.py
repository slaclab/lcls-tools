from pydantic import (
    NonNegativeFloat,
    SerializeAsAny,
    field_validator,
)
from typing import (
    Dict,
    Optional,
    List,
)
from lcls_tools.common.devices.device import (
    Device,
    ControlInformation,
    Metadata,
    PVSet,
)
from lcls_tools.common.controls.epics import PV


class TCAVPVSet(PVSet):
    amplitude: PV
    phase: PV
    rf_enable: PV
    amplitude_fbenb: PV
    phase_fbenb: PV
    amplitude_fbst: PV
    phase_fbst: PV
    mode_config: PV
    amplitude_wocho: PV
    phase_avgnt: PV

    @field_validator("*", mode="before")
    def validate_pv_fields(cls, v: str) -> PV:
        return PV(v)


class TCAVControlInformation(ControlInformation):
    PVs: SerializeAsAny[TCAVPVSet]
    _mode_config_options: SerializeAsAny[Optional[Dict[str, int]]] = dict()
    _amplitude_feedback_options: SerializeAsAny[Optional[Dict[str, int]]] = dict()
    _phase_feedback_options: SerializeAsAny[Optional[Dict[str, int]]] = dict()

    def model_post_init(self, __context) -> None:
        """
        Post-initialization hook for Pydantic models.
        Retrieves and stores all PV enum options immediately after model creation.
        Args:
            __context: Reserved for Pydantic internals. Must be present for compliance.
        Raises:
            TimeoutError: If any PV fails to return its control variables.
        """
        _ = __context  # avoid linter warning for unused variable
        self.set_mode_config_option()
        self.set_amplitude_feedback_options()
        self.setup_phase_feedback_option()

    def set_mode_config_option(self):
        """
        Fetches and stores the enumerated options for the mode configuration PV.
        This method calls `get_ctrlvars()` on the `mode_configs` PV to retrieve
        its enum string options and populates the `_mode_config_options` dictionary.
        Raises:
            TimeoutError: If the PV does not return control variables within the timeout period.
        """
        mode_config_options = self.PVs.mode_config.get_ctrlvars(timeout=2.5)
        if not mode_config_options:
            raise TimeoutError(
                "Timeout while retrieving control variables from mode_configs PV."
            )

        self._mode_config_options.update(
            {option: i for i, option in enumerate(mode_config_options["enum_strs"])}
        )

    def set_amplitude_feedback_options(self):
        """
        Fetches and stores the enumerated options for the amplitude feedback enable PV.
        Retrieves enum strings from the `amp_fbenb` PV using `get_ctrlvars()` and
        updates `_amplitude_feedback_options`.
        Raises:
            TimeoutError: If control variables are not returned within the timeout duration.
        """
        amplitude_feedback_options = self.PVs.amplitude_fbenb.get_ctrlvars(timeout=2.5)
        if not amplitude_feedback_options:
            raise TimeoutError(
                "Timeout while retrieving control variables from amp_fbenb PV."
            )

        self._amplitude_feedback_options.update(
            {
                option: i
                for i, option in enumerate(amplitude_feedback_options["enum_strs"])
            }
        )

    def setup_phase_feedback_option(self):
        """
        Fetches and stores the enumerated options for the phase feedback enable PV.
        Uses `get_ctrlvars()` on the `phase_fbenb` PV to retrieve available options
        and populates `_phase_feedback_options`.
        Raises:
            TimeoutError: If control variables are not available within the timeout window.
        """
        phase_feedback_option = self.PVs.phase_fbenb.get_ctrlvars(timeout=2.5)
        if not phase_feedback_option:
            raise TimeoutError(
                "Timeout while retrieving control variables from phase_fbenb PV."
            )

        self._phase_feedback_options.update(
            {option: i for i, option in enumerate(phase_feedback_option["enum_strs"])}
        )

    @property
    def mode_config_options(self):
        return self._mode_config_options

    @property
    def amplitude_feedback_options(self):
        return self._amplitude_feedback_options

    @property
    def phase_feedback_options(self):
        return self._phase_feedback_options


class TCAVMetadata(Metadata):
    l_eff: Optional[NonNegativeFloat] = None
    rf_freq: Optional[NonNegativeFloat] = None


class TCAV(Device):
    controls_information: SerializeAsAny[TCAVControlInformation]
    metadata: SerializeAsAny[TCAVMetadata]

    def __init__(self, *args, **kwargs):
        super(TCAV, self).__init__(*args, **kwargs)

    def scan(
        self,
        scan_settings: List[float],
        function: Optional[callable] = None,
    ) -> None:
        for setting in scan_settings:
            self.phase_set = setting
            function() if function else None

    @property
    def amplitude(self):
        """The amplitude set point of the TCAV"""
        return self.controls_information.PVs.amplitude.get(use_monitor=False)

    @amplitude.setter
    def amplitude(self, amplitude):
        if not isinstance(amplitude, float):
            return
        self.controls_information.PVs.amplitude.put(amplitude)

    @property
    def phase(self):
        """The phase set point of the TCAV"""
        return self.controls_information.PVs.phase.get(use_monitor=False)

    @phase.setter
    def phase(self, phase):
        if not isinstance(phase, float):
            return
        self.controls_information.PVs.phase.put(phase)

    @property
    def amplitude_fbenb(self):
        """The status of the amplitude set point feedback"""
        return self.controls_information.PVs.amplitude_fbenb.get()

    @amplitude_fbenb.setter
    def amplitude_fbenb(self, enum_str: str):
        field_options = self.controls_information.amplitude_feedback_options
        if not isinstance(enum_str, str):
            raise TypeError(f"{enum_str} is not of type: str")
        if enum_str not in field_options:
            raise ValueError(
                f"{enum_str} not in list of acceptable enumerate string PV values"
            )
        self.controls_information.PVs.amplitude_fbenb.put(field_options[enum_str])

    @property
    def phase_fbenb(self):
        """The status of the phase set point feedback"""
        return self.controls_information.PVs.phase_fbenb.get()

    @phase_fbenb.setter
    def phase_fbenb(self, enum_str: str):
        field_options = self.controls_information.phase_feedback_options
        if not isinstance(enum_str, str):
            raise TypeError(f"{enum_str} is not of type: str")
        if enum_str not in field_options:
            raise ValueError(
                f"{enum_str} not in list of acceptable enumerate string PV values"
            )
        self.controls_information.PVs.phase_fbenb.put(field_options[enum_str])

    @property
    def amplitude_fbst(self):
        """The state of the amplitude feedback"""
        return self.controls_information.PVs.amplitude_fbst.get()

    @property
    def phase_fbst(self):
        """The state of the phase feedback"""
        return self.controls_information.PVs.phase_fbst.get()

    @property
    def mode_config(self):
        """The current ATCA Trigger State"""
        return self.controls_information.PVs.mode_config.get(as_string=True)

    @mode_config.setter
    def mode_config(self, enum_str):
        field_options = self.controls_information.mode_config_options
        if not isinstance(enum_str, str):
            raise TypeError(f"{enum_str} is not of type: str")
        if enum_str not in field_options:
            raise ValueError(
                f"{enum_str} not in list of acceptable enumerate string PV values"
            )
        self.controls_information.PVs.mode_config.put(field_options[enum_str])

    @property
    def amplitude_wocho(self):
        return self.controls_information.PVs.amplitude_wocho.get()

    @property
    def phase_avgnt(self):
        """The state of the phase feedback"""
        return self.controls_information.PVs.phase_avgnt.get()

    @property
    def l_eff(self):
        """The effective length of the TCAV in meters"""
        return self.metadata.l_eff

    @l_eff.setter
    def l_eff(self, length):
        if not isinstance(length, float):
            return
        self.metadata.l_eff = length

    @property
    def rf_freq(self):
        """The Rf frequency of the TCAV in MHz"""
        return self.metadata.rf_freq
