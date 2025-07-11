import logging
import sys

FORMAT_STRING = (
    "%(asctime)s [%(levelname)s] [%(pathname)s:%(funcName)s:%(lineno)d] - %(message)s"
)


def custom_logger(name):
    """Configure log as we want it here, very basic.  Plan to write custom logger later"""
    root_logger = logging.getLogger(name)
    if not root_logger.handlers:
        root_logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter(FORMAT_STRING)

        # console
        out_handler = logging.StreamHandler(sys.stdout)
        out_handler.setLevel(logging.DEBUG)
        out_handler.setFormatter(formatter)

        root_logger.addHandler(out_handler)

    return root_logger
