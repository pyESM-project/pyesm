from pySM.log_exc.logger import Logger
from pySM.util.file_manager import FileManager


class Problem:

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            problem_settings: dict,
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info(f"Generation of '{self}' object.")

        self.files = files

        self.problem_settings = problem_settings

        self.logger.info(f"'{self}' object generated.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'
