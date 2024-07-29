from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel, DirectoryPath


class Measurement(BaseModel, ABC):
    name: str
    save_data: bool = True
    save_location: Optional[DirectoryPath] = None

    @abstractmethod
    def measure(self, **kwargs) -> dict:
        """Implements a measurement and returns a dictionary with the results"""
        raise NotImplementedError
