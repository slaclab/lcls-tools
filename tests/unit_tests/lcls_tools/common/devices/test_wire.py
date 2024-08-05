#!/usr/local/lcls/package/python/current/bin/python

# Built in
# import datetime
from unittest import TestCase
from unittest.mock import Mock, patch  # , PropertyMock
# import inspect

# Local imports
from lcls_tools.common.devices.reader import create_wire
# from lcls_tools.common.devices.wire import WireCollection


class WireTest(TestCase):
    def setUp(self) -> None:
        # Set up some mocks that are needed for all test-cases.
        self.options_and_getter_function = {
            # "MOTR.VELO": None,
            # "MOTR.RBV": None,
            "MOTR_INIT": None,
            "MOTR_INIT_STS": None,
            "MOTR_RETRACT": None,
            "STARTSCAN": None,
            "USEXWIRE": None,
            "USEYWIRE": None,
            "USEUWIRE": None,
            "XWIREINNER": None,
            "XWIREOUTER": None,
            "YWIREINNER": None,
            "YWIREOUTER": None,
            "UWIREINNER": None,
            "UWIREOUTER": None,
            "MOTR_ENABLED_STS": None,
            "MOTR_HOMED_STS": None,
        }
        # set up patch so that each magnet is constructured with ALL ctrl options
        self.ctrl_options_patch = patch("epics.PV.get_ctrlvars", new_callable=Mock)
        self.mock_ctrl_options = self.ctrl_options_patch.start()
        self.mock_ctrl_options.return_value = {
            "enum_strs": tuple(self.options_and_getter_function.keys())
        }
        # create the WSBP2 wire with all possible ctrl options
        self.wire = create_wire(
            area="BYP",
            name="WSBP2",
        )
