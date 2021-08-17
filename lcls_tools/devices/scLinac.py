###########################################################
# Utility classes for superconduting linac
###########################################################


class Linac:
    def __init__(self, name, cryomoduleStringList):
    	# type: (str, List[str]) -> None
        '''
        Parameters
        ----------
        name: str name of Linac i.e. "L0B", "L1B", "L2B", "L3B"
        cryomoduleStringList: list of string names of cryomodules in the linac
        '''
        
        self.name = name
        self.cryomodules = {}
        for cryomoduleString in cryomoduleStringList:
            self.cryomodules[cryomoduleString] = self.Cryomodule(cryomoduleString, self)

    class Cryomodule:
        def __init__(self, cryoName, linacObject):
        	# type: (str, Linac) -> None
        	'''
            Parameters
            ----------
            cryoName: str name of Cryomodule i.e. "02", "03", "H1", "H2"
            linacObject: the linac object this cryomodule belongs to i.e. CM02 is in linac L1B
            '''

            self.name = cryoName
            self.linac = linacObject
            
            self.pvPrefix = "ACCL:{LINAC}:{CRYOMODULE}00:".format(LINAC=self.linac.name,
                                                                  CRYOMODULE=self.name)
            
            self.racks = {}
            self.racks["A"] = self.Rack("A", self)
            self.racks["B"] = self.Rack("B", self)

            self.cavities = dict(self.racks["A"].cavities, **self.racks["B"].cavities)

        class Rack:
            def __init__(self, rackName, cryoObject):
                # type: (str, Cryomodule) -> None
            	'''
                Parameters
                ----------
                rackName: str name of rack (always either "A" or "B")
                cryoObject: the cryomodule object this rack belongs to
                '''

                self.cryomodule = cryoObject
                self.rackName = rackName
                self.cavities = {}
                self.pvPrefix = self.cryomodule.pvPrefix

                if rackName == "A":
                    # rack A always has cavities 1 - 4
                    for cavityNum in range(1,5):
                        self.cavities[cavityNum] = self.Cavity(cavityNum, self)

                elif rackName == "B":
                    # rack B always has cavities 5 - 8
                    for cavityNum in range(5,9):
                        self.cavities[cavityNum] = self.Cavity(cavityNum, self)

                else:
                    raise("Bad rack name")
                        
        
            class Cavity:
                def __init__(self, cavityNum, rackObject):
                	# type: (int, Rack) -> None
                	'''
                    Parameters
                    ----------
                    cavityNum: int cavity number i.e. 1 - 8
                    rackObject: the rack object the cavities belong to
                    '''
                
                    self.number = cavityNum
                    self.rack = rackObject
                    self.cryomodule = self.rack.cryomodule
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

