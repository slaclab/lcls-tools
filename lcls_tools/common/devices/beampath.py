from typing import (
    Dict,
    List,
    Union,
)

from lcls_tools.common.devices.area import (
    Area,
)


from pydantic import (
    BaseModel,
    SerializeAsAny,
)


class Beampath(BaseModel):
    """This class provides access to collections of machine areas
    in a beampath of LCLS/LCLS-II (for example: CU_SXR, or SC_HXR).
    The information for each collection is provided in YAML configuration
    files, where the areas are specified in the YAML file (beampaths.yaml).

    :cvar name: The name of the beampath
    :cvar areas: A collection of Areas as a Dict (keys are area names, values are Area objects)
    """

    name: str = None
    areas: Dict[str, SerializeAsAny[Area]] = None

    def __init__(
        self,
        name,
        *args,
        **kwargs,
    ):
        super(Beampath, self).__init__(
            name=name,
            *args,
            **kwargs,
        )

    @property
    def area_names(self) -> List[str]:
        """Get a list of area names from the beampath"""
        if self.areas:
            return list(
                self.areas.keys(),
            )
        else:
            print(
                "Beampath not configured, could not get area names.",
            )

    def contains_areas(
        self,
        search_areas: Union[str, List[str]] = None,
    ) -> Union[bool, Dict[str, bool]]:
        """Check if the areas exists within the configured beampath.
        :returns Dict[str,bool]: key = area, value = True/False
        """
        if self.areas:
            # we want to take both single and multiple areas to check
            if isinstance(search_areas, str):
                # convert str to list without splitting 'xyz' into ['x','y','z']
                areas = [search_areas]
            else:
                # just use list as provided
                areas = search_areas
            return {area: (area in self.areas) for area in areas}
        else:
            print(
                f"Beampath not configured, could not search for {search_areas}",
            )
            return False
