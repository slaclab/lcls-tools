import abc
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from PyQt5.QtWidgets import QFormLayout
from pydm.widgets import PyDMArchiverTimePlot, PyDMLabel, PyDMWaveformPlot


@dataclass
class PyDMPlotParams:
    lineWidth: Optional[int] = None
    symbol: Optional[str] = None
    symbolSize: Optional[int] = None


@dataclass
class TimePlotParams(PyDMPlotParams):
    plot: PyDMArchiverTimePlot = None
    formLayout: Optional[QFormLayout] = None
    channels: Optional[List[str]] = None
    axes: Optional[List[str]] = None


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
        plotParams.plot.clearAxes()

        for xchannel, ychannel in newChannelPairs:
            plotParams.plot.addChannel(
                y_channel=ychannel,
                x_channel=xchannel,
                lineWidth=plotParams.lineWidth,
                symbol=plotParams.symbol,
                symbolSize=plotParams.symbolSize,
            )


class TimePlotUpdater(PyDMPlotUpdater):
    def __init__(self, timePlotParams: Dict[str, TimePlotParams]):
        self.plotParams: Dict[str, TimePlotParams] = timePlotParams

    def updateTimespans(self, timespan: int):
        for timeplotParam in self.plotParams.values():
            timeplotParam.plot.setTimeSpan(timespan)

    def clearLayout(self, layout: QFormLayout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clearLayout(item.layout())

    def clear_plot(self, key: str) -> TimePlotParams:
        timePlotParams = self.plotParams[key]
        timePlotParams.plot.clearCurves()

        if timePlotParams.formLayout is not None:
            self.clearLayout(timePlotParams.formLayout)

        return timePlotParams

    def clear_plots(self, key_list: List[str] = None):
        if key_list:
            for key in key_list:
                self.clear_plot(key)
        else:
            for key in self.plotParams.keys():
                self.clear_plot(key)

    def updatePlot(self, key: str, newChannels: List[Tuple[str]]):
        timePlotParams: TimePlotParams = self.clear_plot(key)

        if timePlotParams.formLayout is not None:
            for channel, _ in newChannels:
                pydm_label: PyDMLabel = PyDMLabel(init_channel=channel)
                pydm_label.showUnits = True
                timePlotParams.formLayout.addRow(channel, pydm_label)

        for channel, axis in newChannels:
            timePlotParams.plot.addYChannel(
                channel,
                lineWidth=timePlotParams.lineWidth,
                symbol=timePlotParams.symbol,
                symbolSize=timePlotParams.symbolSize,
                yAxisName=axis,
                useArchiveData=True,
            )

    def updatePlots(self, plotUpdateMap: Dict[str, List[Tuple[str, str]]]):
        for key, channelAxisTuple in plotUpdateMap.items():
            self.updatePlot(key, channelAxisTuple)
