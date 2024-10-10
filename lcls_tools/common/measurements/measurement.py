from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel, DirectoryPath


class Measurement(BaseModel, ABC):
    """
    Base abstract class for all meaurements, which serves as the bare minimum skeleton code needed.
    Should be used only as a parent class to all performable measurements.
    ---------------------------
    Arguments:
    name: str (name of measurement performed)
    save_data: bool = True (specifies whether or not to dump data and meta data to h5py file)
    save_location: Optional[DirectoryPath] = None
    (optional argument that is a path to the directory you wish to save the data)
    ---------------------------
    Methods:
    measure: abstractmethod to be implemented in all children classes wear measurement is performed
    """

    name: str
    save_data: bool = True
    save_location: Optional[DirectoryPath] = None

    @abstractmethod
    def measure(self, **kwargs) -> dict:
        """Implements a measurement and returns a dictionary with the results"""
        raise NotImplementedError
