import logging
import os
from typing import Optional


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def configure_logging(log_file: Optional[str] = None) -> None:
    log_format = "[%(filename)s:%(lineno)d] %(message)s"
    log_level = logging.INFO

    if log_file:
        logging.basicConfig(format=log_format, level=log_level, filename=log_file)
    else:
        logging.basicConfig(format=log_format, level=log_level)


log_file = os.environ.get("LOG_FILE")
configure_logging(log_file)
