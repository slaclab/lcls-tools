from unittest.mock import MagicMock

from lcls_tools.common.controls.pyepics.utils import EPICS_NO_ALARM_VAL


def make_mock_pv(
    pv_name: str = None, get_val=None, severity=EPICS_NO_ALARM_VAL
) -> MagicMock:
    return MagicMock(
        pvname=pv_name,
        put=MagicMock(return_value=1),
        get=MagicMock(return_value=get_val),
        severity=severity,
    )
