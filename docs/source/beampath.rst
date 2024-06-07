===========
Beam Paths
===========


Superconducting Beampaths
===========================

.. code-block:: python
    :linenos:

    '''' Example usage of creating the Superconducting Hard X-Ray beampath ''''
    from lcls-tools.superconducting.beampaths import SC_HXR
    # Setup the beampath object
    beampath = SC_HXR()
    print(beampath.name)
    # Check if the areas exist in the beampath
    check_areas = ['L0B', 'HTR', 'L2B']
    print(beampath.contains_areas(check_areas))
    # Get the Area object for L2B
    L0 = beampath.areas['L2B']
    # Get the magnets for L2B
    L0_magnets = beampath.areas['L2B'].magnets
    # Get the screens for L2B
    L0_screens = beampath.areas['L2B'].screens

.. automodule:: lcls_tools.superconducting.beampaths
    :members:

Below is the list of areas for each superconducting beampath

.. literalinclude:: ../../lcls_tools/common/devices/yaml/beampaths.yaml
   :lines: 1-62
   :language: yaml
   :linenos:


Normalconducting Beampaths
===========================

.. code-block:: python
    :linenos:

    '''' Example usage of creating the Normalconducting Hard X-Ray beampath ''''
    from lcls-tools.normalconducting.beampaths import CU_HXR
    # Setup the beampath object
    beampath = CU_HXR()
    print(beampath.name)
    # Check if the areas exist in the beampath
    check_areas = ['L0', 'L1', 'L2']
    print(beampath.contains_areas(check_areas))
    # Get the Area object for L0
    L0 = beampath.areas['L0']
    # Get the magnets for L0
    L0_magnets = beampath.areas['L0'].magnets
    # Get the screens for L0
    L0_screens = beampath.areas['L0'].screens


.. automodule:: lcls_tools.normalconducting.beampaths
    :members:

Below is the list of areas for each normalconducting beampath

.. literalinclude:: ../../lcls_tools/common/devices/yaml/beampaths.yaml
   :lines: 62-
   :language: yaml
   :linenos:



Beampath
==============

.. autoclass:: lcls_tools.common.devices.beampath.Beampath
    :members:
