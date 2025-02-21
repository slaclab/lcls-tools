from abc import ABC, abstractmethod
from typing import Optional

from pydantic import DirectoryPath

import lcls_tools


class Measurement(LCLSBaseModel, ABC):
    name: str
    save_data: bool = True
    save_location: Optional[DirectoryPath] = None

    @abstractmethod
    def measure(self, **kwargs) -> dict:
        """Implements a measurement and returns a dictionary with the results"""
        raise NotImplementedError
