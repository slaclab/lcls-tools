==========
Areas
==========



Area Class
==========

Area classes are generated using yaml configuration files.
To make their usage easier, lcls-tools has a function for generating configured Areas.
Please see the example usage below:

.. code-block:: python
    :linenos:

    """Example usage for creating areas """
    from lcls_tools.common.devices.reader import create_area
    # Generate area for L1B
    L1B = create_area('L1B')

    # After creation, we can access devices collections and print their names
    # and perform group operations on subsets of the area devices
    magnet_collection = L1B.magnet_collection
    print(magnet_collection.device_names)

    # If we want to directly access individual devices, we can do this:
    magnets = L1B.magnets
    print(magnets['QCM02'].name)
    print(magnets['QCM02'].bdes)
    print(magnets['QCM02'].bact)

    # After creation, we can access devices collections and print their names
    # and perform group operations on subsets of the area devices
    DOG = create_area('DOG')
    screen_collection = DOG.screen_collection
    print(screen_collection.device_names)

    # If we want to directly access individual devices, we can do this:
    screens = DOG.screens
    print('Name: ', screens['OTRDOG'].name)
    print(f'Dimensions: ({screens['OTRDOG'].n_rows}, {screens['OTRDOG'].n_cols}).')
    print(f'Resolution: {screens['OTRDOG'].resolution)




.. autoclass:: lcls_tools.common.devices.area.Area
    :members:
