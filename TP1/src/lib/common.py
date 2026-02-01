from enum import Enum
import logging

MSS = 1400
H_SIZE = 12
CHUNK_SIZE = MSS - H_SIZE
INITIAL_RTT = 1
TIMEOUT_COEFFICIENT = 2
MAX_FILE_SIZE = 5242880  # 5 MB
CONNECTION_TIMEOUT = 5
WINDOW_SIZE = 8
GBN_ALPHA = 0.125
GBN_BETA = 0.25
GBN_MIN_TIMEO = 0.1
END_MAX_RETRIES = 5
MAX_WAIT_PACKETS = 5
MAX_WINDOWS_RETRIES = 5
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")


class Action(Enum):
    UPLOAD = "UPLOAD"
    DOWNLOAD = "DOWNLOAD"


def log(msg, level, verbosity):
    threshold_by_mode = {
        "quiet": logging.ERROR,
        "normal": logging.INFO,
        "verbose": logging.DEBUG,
    }

    threshold = threshold_by_mode.get(verbosity, logging.INFO)

    if level >= threshold:
        logging.log(level, msg)
