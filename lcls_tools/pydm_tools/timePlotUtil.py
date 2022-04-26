from dataclasses import dataclass
from typing import Dict, List, Optional

from PyQt5.QtWidgets import QFormLayout
from pydm.widgets import PyDMLabel, PyDMTimePlot


@dataclass
class TimePlotParams:
    plot: PyDMTimePlot
    formLayout: Optional[QFormLayout] = None
    channels: Optional[List[str]] = None
    lineWidth: int = 2
    symbol: str = "o"
    symbolSize: int = 4


class TimePlotUpdater:
    def __init__(self, timePlotParams: Dict[str, TimePlotParams]):
        self.timePlotParams: Dict[str, TimePlotParams] = timePlotParams

    def clearLayout(self, layout: QFormLayout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clearLayout(item.layout())

    def updatePlot(self, key: str, newChannels: List[str]):
        timePlotParams = self.timePlotParams[key]
        timePlotParams.plot.clearCurves()

        if timePlotParams.formLayout is not None:
            self.clearLayout(timePlotParams.formLayout)

            for channel in newChannels:
                timePlotParams.formLayout.addRow(channel, PyDMLabel(init_channel=channel))

        for channel in newChannels:
            timePlotParams.plot.addYChannel(channel,
                                            lineWidth=timePlotParams.lineWidth,
                                            symbol=timePlotParams.symbol,
                                            symbolSize=timePlotParams.symbolSize)

    def updatePlots(self, plotUpdateMap: Dict[str, List[str]]):
        for key, channelList in plotUpdateMap.items():
            self.updatePlot(key, channelList)
