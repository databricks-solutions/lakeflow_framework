import logging
import sys

def set_logger(logger_name: str, log_level: str = "INFO") -> logging.Logger:
    """Set up and return a logger with a specified name and log level."""
    logger = logging.getLogger(logger_name)
    log_level = getattr(logging, log_level, logging.INFO)
    logger.setLevel(log_level)

    # Clear existing handlers to avoid duplicate logging
    if logger.hasHandlers():
        logger.handlers.clear()

    # Add a new handler
    console_output_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_output_handler.setFormatter(formatter)
    logger.addHandler(console_output_handler)

    return logger