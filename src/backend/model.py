from typing import Dict
from pathlib import Path

from backend.database import Database
from backend.problem import Problem
from log_exc.logger import Logger
from util.file_manager import FileManager


class Model:

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            settings: Dict[str, str],
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info(f"Generation of '{self}' object.")

        self.files = files

        self.settings = settings

        self.model_dir_path = Path(
            self.settings['general']['model_data_dir_path'],
            self.settings['general']['model_name']
        )

        self.files.create_dir(self.model_dir_path)

        self.database = Database(
            logger=self.logger,
            files=self.files,
            database_dir_path=self.model_dir_path,
            database_settings=self.settings['database'],
        )

        self.problem = Problem(
            logger=self.logger,
            files=self.files,
            problem_settings=self.settings['problem'],
        )

        self.logger.info(f"'{self}' generated.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def model_cleanup(self):
        self.files.erase_dir(self.model_dir_path)
