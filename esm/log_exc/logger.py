"""
logging.py 

@author: Matteo V. Rocco
@institution: Politecnico di Milano

This module defines the Logger class, which is used for logging throughout the 
package. It supports multiple formats and custom configurations specific to 
the needs of the application.

The Logger class provides a simplified interface for creating and managing 
logs at various levels (INFO, DEBUG, WARNING, ERROR, CRITICAL). It includes a 
method to generate child loggers that inherit properties from a parent logger, 
ensuring consistent log behavior across different modules of the package.
"""

import logging


class Logger:
    """
    A customizable logging class for creating and managing logs in the application.

    The Logger provides facilities for logging messages with different importance 
    levels, ranging from debug messages to critical system messages. It is 
    designed to be easy to configure and use within a package, supporting 
    structured logging practices.

    Attributes:
        log_format (str): The format of the log messages. Choices are 'minimal' 
            or 'standard'.
        str_format (str): The string representation of the log format.
        logger (logging.Logger): The underlying logger instance from Python's 
            logging module.

    Args:
        logger_name (str): The name of the logger, defaults to 'default_logger'.
        log_level (str): The threshold for the logger, defaults to 'INFO'.
        log_format (str): The format used for log messages, defaults to 'minimal'.
    """

    def __init__(
            self,
            logger_name: str = 'default_logger',
            log_level: str = 'INFO',
            log_format: str = 'minimal',
    ) -> None:

        formats = {
            'standard': '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            'minimal': '%(levelname)s | %(name)s | %(message)s'
        }

        self.log_format = log_format
        self.str_format = formats[log_format]

        self.logger = logging.getLogger(logger_name)

        if not self.logger.handlers:
            self.logger.setLevel(log_level)
            formatter = logging.Formatter(self.str_format)
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(log_level)
            stream_handler.setFormatter(formatter)
            stream_handler.propagate = False
            self.logger.addHandler(stream_handler)

    def get_child(self, name: str) -> 'Logger':
        """
        Creates and returns a child Logger with a specified name, inheriting 
        properties from this Logger instance.

        Args:
            name (str): The name identifier for the child logger, typically 
                __name__ from the module where the logger is used.

        Returns:
            Logger: A new Logger instance configured as a child of this one.
        """
        child_logger = self.logger.getChild(name.split('.')[-1])

        new_logger = Logger(
            logger_name=child_logger.name,
            log_level=child_logger.level,
            log_format=self.log_format,
        )

        new_logger.logger.propagate = False
        return new_logger

    def log(self,
            message: str,
            level: str = logging.INFO):
        """Basic log message. 

        Args:
            message (str): message to be displayed.
            level (str, optional): level of the log message. Defaults 
                to logging.INFO.
        """
        self.logger.log(msg=message, level=level)

    def info(self, message: str):
        """INFO log message."""
        self.logger.log(msg=message, level=logging.INFO)

    def debug(self, message: str):
        """DEBUG log message."""
        self.logger.log(msg=message, level=logging.DEBUG)

    def warning(self, message: str):
        """WARNING log message."""
        self.logger.log(msg=message, level=logging.WARNING)

    def error(self, message: str):
        """ERROR log message."""
        self.logger.log(msg=message, level=logging.ERROR)

    def critical(self, message: str):
        """CRITICAL log message."""
        self.logger.log(msg=message, level=logging.CRITICAL)
