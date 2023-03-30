import logging


class Logger:

    def __init__(
            self,
            logger_name: str,
            log_level: str,
            log_file_path: str) -> None:

        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(log_level)

        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
        )

        file_handler = None
        stream_handler = None

        for handler in self.logger.handlers:
            if isinstance(handler, logging.FileHandler):
                file_handler = handler
            elif isinstance(handler, logging.StreamHandler):
                stream_handler = handler

        if file_handler is None:
            file_handler = logging.FileHandler(log_file_path)
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            file_handler.propagate = False
            self.logger.addHandler(file_handler)

        if stream_handler is None:
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(log_level)
            stream_handler.setFormatter(formatter)
            stream_handler.propagate = False
            self.logger.addHandler(stream_handler)

    def getChild(self, name: str) -> 'Logger':
        """Return a child logger with the specified name."""
        child_logger = self.logger.getChild(name.split('.')[-1])

        new_logger = Logger(
            logger_name=child_logger.name,
            log_level=child_logger.level,
            log_file_path=self.logger.handlers[0].baseFilename)

        new_logger.logger.propagate = False
        return new_logger

    def log(self, message: str, level=logging.INFO):
        self.logger.log(msg=message, level=level)

    def info(self, message: str):
        self.logger.log(msg=message, level=logging.INFO)

    def debug(self, message: str):
        self.logger.log(msg=message, level=logging.DEBUG)

    def warning(self, message: str):
        self.logger.log(msg=message, level=logging.WARNING)

    def error(self, message: str):
        self.logger.log(msg=message, level=logging.ERROR)

    def critical(self, message: str):
        self.logger.log(msg=message, level=logging.CRITICAL)
