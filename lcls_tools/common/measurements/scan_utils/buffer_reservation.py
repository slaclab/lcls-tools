import edef
import logging
import os


class BufferError(Exception):
    pass


DEST_MODE_MAP = {
    "Disable": 0,
    "Exclusion": 1,
    "Inclusion": 2
}


def reserve_buffer(
        name: str,
        beampath: str,
        n_measurements: int,
        destination_mode: str = "Disable",
        logger: logging.Logger = None):
    user = os.getlogin()
    if logger:
        logging.info("Reserving buffer...")

    if beampath.startswith("SC"):
        if destination_mode not in DEST_MODE_MAP:
            raise BufferError(f"Invalid destination mode: {destination_mode}")

        buf = edef.BSABuffer(name=name, user=user)
        buf.n_measurements = n_measurements
        buf.destination_mode = DEST_MODE_MAP[destination_mode]
        buf.clear_masks()
        buf.destination_masks = [beampath]
        if logger:
            logger.info("Reserved BSA Buffer %s.", buf.number)
        return buf

    elif beampath.startswith("CU"):
        buf = edef.EventDefinition(name=name, user=user)
        buf.n_measurements = n_measurements
        if logger:
            logger.info("Reserved eDef Buffer %s.", buf.number)
        return buf
    else:
        raise BufferError(f"Unrecognized beampath: {beampath}")
