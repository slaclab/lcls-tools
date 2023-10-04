from pydm import Display

from lcls_tools.superconducting import scLinac, sc_linac_utils as utils


class MagnetScreen(Display):
    def __init__(self, parent=None, args=None):
        super().__init__(parent, args)

    def ui_filename(self):
        return "magnet_template.ui"

    def connectSignals(self, magnet: scLinac.Magnet):
        self.ui.expertButton.macros = ["DEV={dev}".format(dev=magnet.pvprefix[:-1])]
        self.ui.magnetGroupBox.setTitle(
            "CM{cm} {magnettype}".format(
                cm=magnet.cryomodule.name, magnettype=magnet.name
            )
        )

        self.ui.interlockIndicator.channel = magnet.interlockPV.pvname
        self.ui.interlockLabel.channel = magnet.interlockPV.pvname

        self.ui.onButton.channel = magnet.controlPV.pvname
        self.ui.onButton.pressValue = utils.MAGNET_ON_VALUE

        self.ui.offButton.channel = magnet.controlPV.pvname
        self.ui.offButton.pressValue = utils.MAGNET_OFF_VALUE

        self.ui.resetButton.channel = magnet.controlPV.pvname
        self.ui.resetButton.pressValue = utils.MAGNET_RESET_VALUE

        self.ui.powerIndicator.channel = magnet.ps_statusPV.pvname
        self.ui.powerLabel.channel = magnet.ps_statusPV.pvname

        self.ui.degaussButton.channel = magnet.controlPV.pvname
        self.ui.degaussButton.pressValue = utils.MAGNET_DEGAUSS_VALUE

        self.ui.bdesLineEdit.channel = magnet.bdesPV.pvname
        self.ui.bdesLineEdit.returnPressed.connect(magnet.trim)
        self.ui.bactLabel.channel = magnet.bactPV.pvname

        self.ui.idesLineEdit.channel = magnet.idesPV.pvname
        self.ui.iactLabel.channel = magnet.iactPV.pvname
