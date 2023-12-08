from typing import Dict
from pathlib import Path

from src.backend.database import Database
from src.backend.index import Index
from src.backend.problem import Problem
from src.log_exc.logger import Logger
from src.util.file_manager import FileManager
from src.util.sql_manager import SQLManager, connection


class Model:

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            settings: Dict[str, str],
            database_name: str,
            paths: Dict[str, Path],
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info(f"'{self}' object initialization...")

        self.files = files
        self.settings = settings
        self.paths = paths

        self.model_dir_generation()

        self.sqltools = SQLManager(
            logger=self.logger,
            database_dir_path=self.paths['database_dir'],
            database_name=database_name,
        )

        self.index = Index(
            logger=self.logger,
            files=self.files,
        )

        self.database = Database(
            logger=self.logger,
            files=self.files,
            sqltools=self.sqltools,
            settings=self.settings,
            database_dir_path=self.paths['database_dir'],
            index=self.index,
        )

        self.problem = Problem(
            logger=self.logger,
            files=self.files,
            settings=self.settings,
        )

        self.variables = None

        self.logger.info(f"'{self}' initialized.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def model_dir_generation(self) -> None:
        self.files.create_dir(self.paths['database_dir'])

    def model_dir_cleanup(self) -> None:
        self.files.erase_dir(self.paths['database_dir'])

    def load_model_sets(
            self,
            excel_file_name: str,
            excel_file_dir_path: Path,
    ) -> None:

        self.index.load_sets_to_index(
            excel_file_name=excel_file_name,
            excel_file_dir_path=excel_file_dir_path,
        )

        self.database.load_sets_to_database()
