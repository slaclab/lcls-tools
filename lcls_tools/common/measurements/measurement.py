from abc import ABC, abstractmethod
from typing import Optional

from pydantic import DirectoryPath

from lcls_tools.common.pydantic import LCLSBaseModel


class Measurement(LCLSBaseModel, ABC):
    name: str
    save_data: bool = True
    save_location: Optional[DirectoryPath] = None

    @abstractmethod
    def measure(self, **kwargs) -> dict:
        """Implements a measurement and returns a dictionary with the results"""
        raise NotImplementedError
