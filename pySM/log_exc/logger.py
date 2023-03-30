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
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(log_level)
        stream_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(stream_handler)

    def log(self, message: str, level=logging.INFO):
        self.logger.log(msg=message, level=level)

    def info(self, message: str):
        self.logger.log(msg=message, level=logging.INFO)

    def debug(self, message: str):
        self.logger.log(msg=message, level=logging.DEBUG)

    def warning(self, message: str):
        self.logger.log(msg=message, level=logging.WARNING)

    def critical(self, message: str):
        self.logger.log(msg=message, level=logging.CRITICAL)
