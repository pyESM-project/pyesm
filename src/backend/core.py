from typing import Dict
from pathlib import Path

from src.backend.database import Database
from src.backend.index import Index
from src.backend.problem import Problem
from src.log_exc.logger import Logger
from src.util.file_manager import FileManager
from src.util.sql_manager import SQLManager


class Core:

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
            database_dir_path=self.paths['model_dir'],
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
            database_dir_path=self.paths['model_dir'],
            index=self.index,
        )

        self.problem = Problem(
            logger=self.logger,
            files=self.files,
            settings=self.settings,
            index=self.index
        )

        self.variables = None

        self.logger.info(f"'{self}' initialized.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def model_dir_generation(self) -> None:
        if self.settings['model']['use_existing_database']:
            self.logger.info("Skipping model directory generation.")
        else:
            self.files.create_dir(self.paths['model_dir'])

    # slice database and put exogeous data into the index.data cvxpy vars
    def initialize_model_variables(self):
        self.logger.info("Initialize dataframes of variables.")
