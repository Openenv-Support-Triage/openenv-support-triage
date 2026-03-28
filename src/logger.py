import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """Returns a logger with a consistent format for the given module name."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        # Force UTF-8 on Windows to avoid cp1252 encode errors
        stream = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1, closefd=False)
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
            datefmt="%H:%M:%S"
        ))
        logger.addHandler(handler)

    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    return logger
