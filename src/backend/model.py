from typing import Dict
from pathlib import Path

from src.backend.database import Database
from src.backend.problem import Problem
from src.log_exc.logger import Logger
from src.util.file_manager import FileManager


class Model:

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            settings: Dict[str, str],
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info(f"'{self}' object initialization...")

        self.files = files

        self.settings = settings

        self.model_dir_path = Path(
            self.settings['general']['model_data_dir_path'],
            self.settings['general']['model_name']
        )

        self.model_dir_generation()

        self.database = Database(
            logger=self.logger,
            files=self.files,
            database_settings=self.settings['database'],
            database_dir_path=self.model_dir_path
        )

        self.problem = Problem(
            logger=self.logger,
            files=self.files,
            problem_settings=self.settings['problem'],
        )

        self.variables = None

        self.logger.info(f"'{self}' initialized.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def model_dir_generation(self) -> None:
        self.files.create_dir(self.model_dir_path)

    def model_dir_cleanup(self) -> None:
        self.files.erase_dir(self.model_dir_path)

    def variables_generation(self) -> None:
        if self.variables is not None:
            self.logger.warning(
                "Dictionary of variables data already "
                f"initialized in '{self}' object."
            )
            user_input = input(
                "Overwrite dictionary of variables? (y/[n]): ")
            if user_input.lower() != 'y':
                self.logger.info(
                    "Original dictionary of variables not overwritten.")
                return

        self.variables = self.database.generate_variables_data_dict()
