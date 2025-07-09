import sys
import logging


FORMAT_STRING = "%(asctime)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%H:%M:%S"


def custom_logger(log_file=None, name=__name__, level=logging.INFO):
    logger = logging.getLogger(name)
    logger.handlers.clear()
    logger.setLevel(level)

    def make_handler(handler, use_date_format=False):
        formatter = logging.Formatter(
            FORMAT_STRING, datefmt=DATE_FORMAT if use_date_format else None
        )
        handler.setFormatter(formatter)
        return handler

    # File handler
    if log_file is not None:
        logger.addHandler(make_handler(logging.FileHandler(log_file)))

    # Console handler
    logger.addHandler(make_handler(logging.StreamHandler(), use_date_format=True))

    # Exception hook
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.error(
            "Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback)
        )

    sys.excepthook = handle_exception

    return logger
