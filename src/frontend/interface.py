from pathlib import Path

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
        self.load_settings(file_settings_name, file_settings_dir_path)

        self.model = Model(
            logger=self.logger,
            files=self.files,
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
            self.logger.warning(f"Settings already loaded in '{self}' object.")
            user_input = input("Overwrite settings? (y/[n]): ")
            if user_input.lower() != 'y':
                self.logger.info("Settings not overwritten.")
                return
            else:
                self.logger.info("Updating settings.")
        else:
            self.logger.info("Loading settings.")

        self.settings = self.files.load_file(
            file_name=file_settings_name,
            dir_path=file_settings_dir_path,
        )

    def warm_start_for_debug(self):
        """Use for debugging: do not overwrite sets and input data
        """
        self.model.database.load_sets()
        self.model.database.load_variables_coordinates()
