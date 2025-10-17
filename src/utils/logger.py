import logging
import sys
from datetime import datetime

def setup_logger(name: str = "pod_logger", level=logging.INFO) -> logging.Logger:
    """
    Sets up a logger that prints timestamped logs to stdout, suitable for pytest-html.
    """
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.setLevel(level)

    # Formatter with timestamp, level, and message
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # StreamHandler to print to console (pytest captures this)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger