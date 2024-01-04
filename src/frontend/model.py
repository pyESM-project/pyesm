from pathlib import Path
from typing import Dict

from src.log_exc.logger import Logger
from src.util.file_manager import FileManager
from src.util.pbi_manager import PBIManager
from src.backend.core import Core
from src.util.sql_manager import SQLManager, connection


class Model:

    def __init__(
            self,
            log_level: str = 'info',
            log_format: str = 'standard',
            log_file_name: str = 'log_model.log',
            file_settings_name: str = 'settings.yml',
            file_settings_dir_path: Path = Path(__file__).resolve().parent,
    ) -> None:

        self.logger = Logger(
            logger_name=str(self),
            log_level=log_level.upper(),
            log_file_path=Path(file_settings_dir_path) / log_file_name,
            log_format=log_format
        )

        self.logger.info(f"'{self}' object initialization...")

        self.files = FileManager(logger=self.logger)

        self.settings = None
        self.paths = None

        self.load_settings(file_settings_name, file_settings_dir_path)
        self.load_paths(self.settings)

        self.core = Core(
            logger=self.logger,
            files=self.files,
            settings=self.settings,
            database_name=self.settings['database']['name'],
            paths=self.paths,
        )

        self.pbi_tools = PBIManager(
            logger=self.logger,
            settings=self.settings,
        )

        self.logger.info(f"'{self}' object initialized.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def load_settings(
            self,
            file_settings_name: str,
            file_settings_dir_path: Path,
    ) -> None:
        """Load settings from a file, allowing users to overwrite existing 
        settings if present.

        Args:
            file_settings_name (str): The name of the settings file.
            file_settings_dir_path (Path): The directory path where the 
                settings file is located.
        """

        if self.settings is not None:
            self.logger.warning(f"'{self}' object: settings already loaded.")
            user_input = input("Overwrite settings? (y/[n]): ")
            if user_input.lower() != 'y':
                self.logger.info(f"'{self}' object: settings not overwritten.")
                return
            else:
                self.logger.info(f"'{self}' object: updating settings.")
        else:
            self.logger.info(f"'{self}' object: loading settings.")

        self.settings = self.files.load_file(
            file_name=file_settings_name,
            dir_path=file_settings_dir_path,
        )

    def load_paths(
            self,
            settings: Dict,
    ) -> None:
        self.logger.info(f"'{self}' object: loading paths from settings.")
        self.paths = {}
        self.paths['model_dir'] = Path(
            settings['model']['dir_path'],
            settings['model']['name']
        )
        self.paths['input_data_dir'] = Path(
            self.paths['model_dir'],
            settings['database']['input_data_dir_name']
        )
        self.paths['sets_excel_file'] = Path(
            self.paths['model_dir'],
            settings['database']['sets_excel_file_name']
        )
        self.paths['sql_database'] = Path(
            self.paths['model_dir'],
            settings['database']['name']
        )

    def load_model_coordinates(self) -> None:

        self.core.index.load_sets_to_index(
            excel_file_name=self.settings['database']['sets_excel_file_name'],
            excel_file_dir_path=self.paths['model_dir'])

        if self.settings['model']['use_existing_database']:
            self.logger.info(
                "Relying on existing SQL database "
                f"'{self.settings['database']['name']}'."
            )
        else:
            self.core.database.load_sets_to_database()

        self.core.index.load_vars_table_headers_to_index()
        self.core.index.load_vars_coordinates_to_index()
        self.core.index.load_sets_parsing_hierarchy()

        if self.settings['database']['foreign_keys']:
            self.core.index.load_foreign_keys_to_vars_index()

    def generate_blank_database(self) -> None:

        if self.settings['model']['use_existing_database']:
            db_name = self.settings['database']['name']
            self.logger.info(f"Relying on existing SQL database '{db_name}'.")
        else:
            self.core.database.generate_blank_vars_sql_tables()
            self.core.database.generate_blank_vars_input_files()

        if self.settings['model']['generate_powerbi_report']:
            self.pbi_tools.generate_powerbi_report()

    def load_data_files_to_database(
            self,
            overwrite_existing_data: bool = False,
    ) -> None:
        self.core.database.load_data_input_files_to_database(
            overwrite_existing_data=overwrite_existing_data)

    def initialize_problem(self) -> None:
        self.core.initialize_problem_variables()
        self.core.data_to_cvxpy_exogenous_vars()

    def erase_model(self) -> None:
        self.logger.warning(
            f"Erasing model {self.settings['model']['name']}.")
        self.files.erase_dir(self.paths['model_dir'])

    def update_database_and_problem(self) -> None:
        self.load_data_files_to_database(overwrite_existing_data=True)
        self.initialize_problem()
