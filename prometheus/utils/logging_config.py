"""
Logging Configuration for Prometheus

Provides structured logging across all modules with different levels
for development vs production.

Usage:
    from prometheus.utils.logging_config import get_logger

    logger = get_logger(__name__)
    logger.info("Training started")
    logger.error("Training failed", exc_info=True)
"""

import logging
import sys
from pathlib import Path
from typing import Optional
import os


# Color codes for terminal output
class LogColors:
    """ANSI color codes for log levels."""
    DEBUG = '\033[36m'      # Cyan
    INFO = '\033[32m'       # Green
    WARNING = '\033[33m'    # Yellow
    ERROR = '\033[31m'      # Red
    CRITICAL = '\033[35m'   # Magenta
    RESET = '\033[0m'       # Reset


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output."""

    FORMATS = {
        logging.DEBUG: LogColors.DEBUG + '%(levelname)-8s' + LogColors.RESET + ' %(name)s: %(message)s',
        logging.INFO: LogColors.INFO + '%(levelname)-8s' + LogColors.RESET + ' %(message)s',
        logging.WARNING: LogColors.WARNING + '%(levelname)-8s' + LogColors.RESET + ' %(message)s',
        logging.ERROR: LogColors.ERROR + '%(levelname)-8s' + LogColors.RESET + ' %(name)s: %(message)s',
        logging.CRITICAL: LogColors.CRITICAL + '%(levelname)-8s' + LogColors.RESET + ' %(name)s: %(message)s',
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)


class FileFormatter(logging.Formatter):
    """Detailed formatter for file output."""

    def __init__(self):
        super().__init__(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


def setup_logging(
    level: str = 'INFO',
    log_file: Optional[str] = None,
    log_dir: Optional[str] = None,
    console: bool = True
) -> None:
    """
    Setup logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file name
        log_dir: Directory for log files (default: logs/)
        console: Enable console logging
    """
    # Convert level string to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Get root logger
    root_logger = logging.getLogger('prometheus')
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    root_logger.handlers = []

    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(ColoredFormatter())
        root_logger.addHandler(console_handler)

    # File handler
    if log_file or log_dir:
        if log_dir is None:
            log_dir = 'logs'

        # Create log directory
        Path(log_dir).mkdir(parents=True, exist_ok=True)

        if log_file is None:
            log_file = 'prometheus.log'

        file_path = Path(log_dir) / log_file
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(logging.DEBUG)  # File gets everything
        file_handler.setFormatter(FileFormatter())
        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a module.

    Args:
        name: Module name (use __name__)

    Returns:
        Configured logger instance
    """
    # Ensure logging is setup
    if not logging.getLogger('prometheus').handlers:
        # Auto-setup with defaults
        level = os.environ.get('PROMETHEUS_LOG_LEVEL', 'INFO')
        setup_logging(level=level, console=True)

    return logging.getLogger(f'prometheus.{name}')


# Default setup when imported
if not logging.getLogger('prometheus').handlers:
    level = os.environ.get('PROMETHEUS_LOG_LEVEL', 'INFO')
    setup_logging(level=level, console=True)


# Convenience functions
def set_log_level(level: str):
    """Set global log level."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.getLogger('prometheus').setLevel(numeric_level)


def enable_debug():
    """Enable debug logging."""
    set_log_level('DEBUG')


def disable_console_logging():
    """Disable console output (file only)."""
    logger = logging.getLogger('prometheus')
    for handler in logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
            logger.removeHandler(handler)


# Example usage
if __name__ == '__main__':
    # Setup logging
    setup_logging(level='DEBUG', log_file='test.log', console=True)

    # Get logger
    logger = get_logger(__name__)

    # Test all levels
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")

    # Test with exception
    try:
        1 / 0
    except Exception:
        logger.error("An error occurred", exc_info=True)
