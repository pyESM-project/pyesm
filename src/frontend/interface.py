from pathlib import Path
from typing import Dict

from src.log_exc.logger import Logger
from src.util.file_manager import FileManager
from src.backend.model import Model


class Interface:

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

        self.model = Model(
            logger=self.logger,
            files=self.files,
            settings=self.settings,
            database_name=self.settings['database']['name'],
            paths=self.paths,
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
        self.paths['database_dir'] = Path(
            settings['database']['dir_path'],
            settings['model']['name']
        )
        self.paths['input_data_dir'] = Path(
            self.paths['database_dir'],
            settings['database']['input_data_dir_name']
        )
        self.paths['sets_excel_file'] = Path(
            self.paths['database_dir'],
            settings['database']['sets_excel_file_name']
        )
        self.paths['sql_database'] = Path(
            self.paths['database_dir'],
            settings['database']['name']
        )

    def load_sets(self) -> None:
        self.model.load_model_sets(
            excel_file_name=self.settings['database']['sets_excel_file_name'],
            excel_file_dir_path=self.paths['database_dir'],
        )

    def generate_blank_sql_database(
            self,
            foreign_keys_on: bool = True,
    ) -> None:
        self.model.database.generate_blank_database(
            foreign_keys_on=foreign_keys_on)

    def generate_blank_data_input_files(self):
        self.model.database.generate_blank_data_input_files()

    def load_data_files_to_database(self):
        self.model.database.load_data_input_files()
