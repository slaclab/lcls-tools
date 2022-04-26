import abc
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from PyQt5.QtWidgets import QFormLayout
from pydm.widgets import PyDMLabel, PyDMTimePlot, PyDMWaveformPlot


@dataclass
class PyDMPlotParams:
    lineWidth: int = 2
    symbol: str = "o"
    symbolSize: int = 4


@dataclass
class TimePlotParams(PyDMPlotParams):
    plot: PyDMTimePlot = None
    formLayout: Optional[QFormLayout] = None
    channels: Optional[List[str]] = None


@dataclass
class WaveformPlotParams(PyDMPlotParams):
    plot: PyDMWaveformPlot = None
    channelPairs: Optional[List[Tuple[Optional[str], str]]] = None


class PyDMPlotUpdater:
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def updatePlot(self, **kwargs):
        return

    @abc.abstractmethod
    def updatePlots(self, **kwargs):
        return


class WaveformPlotUpdater(PyDMPlotUpdater):

    def __init__(self, waveformPlotParams: Dict[str, WaveformPlotParams]):
        self.plotParams: Dict[str, WaveformPlotParams] = waveformPlotParams

    def updatePlots(self, plotUpdateMap: Dict[str, List[Tuple[Optional[str], str]]]):
        for key, channelPairs in plotUpdateMap.items():
            self.updatePlot(key, channelPairs)

    def updatePlot(self, key: str, newChannelPairs: List[Tuple[Optional[str], str]]):
        plotParams = self.plotParams[key]
        plotParams.plot.clearCurves()

        for (xchannel, ychannel) in newChannelPairs:
            plotParams.plot.addChannel(y_channel=ychannel, x_channel=xchannel,
                                       lineWidth=plotParams.lineWidth,
                                       symbol=plotParams.symbol,
                                       symbolSize=plotParams.symbolSize)


class TimePlotUpdater(PyDMPlotUpdater):

    def __init__(self, timePlotParams: Dict[str, TimePlotParams]):
        self.plotParams: Dict[TimePlotParams] = timePlotParams

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
        timePlotParams = self.plotParams[key]
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
