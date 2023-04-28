from pySM.log_exc.logger import Logger
from pySM.src.file_manager import FileManager


class Problem:

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            problem_settings: dict,
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info(f"Generation of '{str(self)}' object.")

        self.files = files

        self.logger.info(f"'{str(self)}' object generated.")

        self.problem_settings = problem_settings

    def __str__(self):
        class_name = type(self).__name__
        return f'{class_name}'


if __name__ == '__main__':
    pass
