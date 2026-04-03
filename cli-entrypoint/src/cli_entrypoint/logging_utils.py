"""Custom logging handler that creates the log directory if it doesn't exist."""

import os
from logging.handlers import RotatingFileHandler


class MkdirRotatingFileHandler(RotatingFileHandler):
    """RotatingFileHandler that creates parent directories on first use."""

    def __init__(self, filename, mode="a", maxBytes=0, backupCount=0, encoding=None, delay=False):
        os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
        super().__init__(filename, mode, maxBytes, backupCount, encoding, delay)
