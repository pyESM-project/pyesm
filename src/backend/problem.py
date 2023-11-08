from src.log_exc.logger import Logger
from src.util.file_manager import FileManager


class Problem:

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            problem_settings: dict,
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info(f"'{self}' object initialization...")

        self.files = files

        self.problem_settings = problem_settings

        self.logger.info(f"'{self}' object initialized.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'
