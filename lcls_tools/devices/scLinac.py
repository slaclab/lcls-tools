###########################################################
# Utility classes for superconduting linac
###########################################################

class Linac:
    def __init__(self, name, cryomoduleStringList):
    	# type: (str, List[str]) -> None
        self.name = name
        self.cryomodules = {}
        for cryomoduleString in cryomoduleStringList:
            self.cryomodules[cryomoduleString] = Cryomodule(cryomoduleString, self)

class Cryomodule:
    def __init__(self, cryoName, linacObject):
    	# type: (str, Linac) -> None
        self.name = cryoName
        self.linac = linacObject
        self.cavities = {}
		# Every cryomodule has 8 cavities, so this is hard coded
        for cavityNum in range(1, 9):
            self.cavities[cavityNum] = Cavity(cavityNum, self)

class Cavity:
    def __init__(self, cavityNum, cryoObject):
    	# type: (int, Cryomodule) -> None
        self.number = cavityNum
        self.cryomodule = cryoObject
        self.linac = self.cryomodule.linac
        self.pvPrefix = "ACCL:{LINAC}:{CRYOMODULE}{CAVITY}0:".format(LINAC=self.linac.name,
                                                                     CRYOMODULE=self.cryomodule.name,
                                                                     CAVITY=self.number)

# Global list of superconducting linac objects
LINACS = [Linac("L0B", ["01"]),
          Linac("L1B", ["02", "03", "H1", "H2"]),
          Linac("L2B", ["04", "05", "06", "07", "08", "09", "10", "11", "12",
                        "13", "14", "15"]),
          Linac("L3B", ["16", "17", "18", "19", "20", "21", "22", "23", "24",
                        "25", "26", "27", "28", "29", "30", "31", "32", "33",
                        "34", "35"])]

