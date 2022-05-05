from PyQt5.QtWidgets import QWidget
from qtpy.QtCore import Slot


@Slot()
def showDisplay(display: QWidget):
    display.show()

    # brings the display to the front
    display.raise_()

    # gives the display focus
    display.activateWindow()
