from dataclasses import dataclass
from typing import Dict, List, Optional

from pydm.widgets import PyDMTimePlot


@dataclass
class TimePlotParams:
    plot: PyDMTimePlot
    channels: Optional[List[str]] = None
    lineWidth: int = 2
    symbol: str = "o"
    symbolSize: int = 4


class TimePlotUpdater:
    def __init__(self, timePlotParams: Dict[str, TimePlotParams]):
        self.timePlotParams: Dict[str, TimePlotParams] = timePlotParams

    def updatePlot(self, key: str, newChannels: List[str]):
        timePlotParams = self.timePlotParams[key]
        timePlotParams.plot.clearCurves()
        for channel in newChannels:
            timePlotParams.plot.addYChannel(channel,
                                            lineWidth=timePlotParams.lineWidth,
                                            symbol=timePlotParams.symbol,
                                            symbolSize=timePlotParams.symbolSize)

    def updatePlots(self, plotUpdateMap: Dict[str, List[str]]):
        for key, channelList in plotUpdateMap.items():
            self.updatePlot(key, channelList)
