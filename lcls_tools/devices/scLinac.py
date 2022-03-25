################################################################################
# Utility classes for superconduting linac
# NOTE: For some reason, using python 3 style type annotations causes circular
#       import issues, so leaving as python 2 style for now
################################################################################

from typing import Dict, List, Type


class Cavity:
    def __init__(self, cavityNum, rackObject):
        # type: (int, Rack) -> None
        """
        Parameters
        ----------
        cavityNum: int cavity number i.e. 1 - 8
        rackObject: the rack object the cavities belong to
        """

        self.number = cavityNum
        self.rack = rackObject
        self.cryomodule = self.rack.cryomodule
        self.linac = self.cryomodule.linac
        self.pvPrefix = "ACCL:{LINAC}:{CRYOMODULE}{CAVITY}0:".format(LINAC=self.linac.name,
                                                                     CRYOMODULE=self.cryomodule.name,
                                                                     CAVITY=self.number)


class Cryomodule:
    def __init__(self, cryoName, linacObject, cavityClass=Cavity):
        # type: (str, Linac, Type[Cavity]) -> None
        """
        Parameters
        ----------
        cryoName: str name of Cryomodule i.e. "02", "03", "H1", "H2"
        linacObject: the linac object this cryomodule belongs to i.e. CM02 is in linac L1B
        cavityClass: cavity object
        """

        self.name = cryoName
        self.linac = linacObject

        self.pvPrefix = "ACCL:{LINAC}:{CRYOMODULE}00:".format(LINAC=self.linac.name,
                                                              CRYOMODULE=self.name)

        self.racks = {"A": Rack("A", self, cavityClass),
                      "B": Rack("B", self, cavityClass)}

        self.cavities: Dict[int, cavityClass] = {}
        self.cavities.update(self.racks["A"].cavities)
        self.cavities.update(self.racks["B"].cavities)


class Linac:
    def __init__(self, linacName, cryomoduleStringList, cavityClass=Cavity, cryomoduleClass=Cryomodule):
        # type: (str, List[str], Type[Cavity], Type[Cryomodule]) -> None
        """
        Parameters
        ----------
        linacName: str name of Linac i.e. "L0B", "L1B", "L2B", "L3B"
        cryomoduleStringList: list of string names of cryomodules in the linac
        cavityClass: cavity object
        """

        self.name = linacName
        self.cryomodules: Dict[str, cryomoduleClass] = {}
        for cryomoduleString in cryomoduleStringList:
            self.cryomodules[cryomoduleString] = cryomoduleClass(cryomoduleString, self, cavityClass)


class Rack:
    def __init__(self, rackName, cryoObject, cavityClass=Cavity):
        # type: (str, Cryomodule, Type[Cavity]) -> None
        """
        Parameters
        ----------
        rackName: str name of rack (always either "A" or "B")
        cryoObject: the cryomodule object this rack belongs to
        cavityClass: cavity object
        """

        self.cryomodule = cryoObject
        self.rackName = rackName
        self.cavities = {}
        self.pvPrefix = self.cryomodule.pvPrefix + "RACK{RACK}:".format(RACK=self.rackName)

        if rackName == "A":
            # rack A always has cavities 1 - 4
            for cavityNum in range(1, 5):
                self.cavities[cavityNum] = cavityClass(cavityNum, self)

        elif rackName == "B":
            # rack B always has cavities 5 - 8
            for cavityNum in range(5, 9):
                self.cavities[cavityNum] = cavityClass(cavityNum, self)

        else:
            raise Exception("Bad rack name")


# Global list of superconducting linac objects
L0B = ["01"]
L1B = ["02", "03", "H1", "H2"]
L2B = ["04", "05", "06", "07", "08", "09", "10", "11", "12", "13", "14", "15"]
L3B = ["16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27",
       "28", "29", "30", "31", "32", "33", "34", "35"]

LINAC_TUPLES = [("L0B", L0B), ("L1B", L1B), ("L2B", L2B), ("L3B", L3B)]

# Utility list of linacs
LINAC_OBJECTS: List[Linac] = []

# Utility dictionary to map cryomodule name strings to cryomodule objects
CRYOMODULE_OBJECTS: Dict[str, Cryomodule] = {}

for idx, (name, cryomoduleList) in enumerate(LINAC_TUPLES):
    linac = Linac(name, cryomoduleList)
    LINAC_OBJECTS.append(linac)
    CRYOMODULE_OBJECTS.update(linac.cryomodules)
