from pathlib import Path

from src.log_exc.logger import Logger
from src.log_exc.exceptions import *
from src.constants import constants
from src.support.file_manager import FileManager
from src.support.pbi_manager import PBIManager
from src.backend.core import Core


class Model:

    def __init__(
            self,
            model_dir_name: str,
            main_dir_path: str,
            log_level: str = 'debug',
            log_format: str = 'minimal',
    ) -> None:

        self.logger = Logger(
            logger_name=str(self),
            log_level=log_level.upper(),
            log_format=log_format,
        )

        self.logger.info(f"'{self}' object initialization...")

        self.files = FileManager(logger=self.logger)

        self.settings = None

        self.paths = {'model_dir': Path(main_dir_path) / model_dir_name}

        # self.check_model_dir()
        # self.load_settings()
        # self.load_paths()

        # self.core = Core(
        #     logger=self.logger,
        #     files=self.files,
        #     settings=self.settings,
        #     paths=self.paths,
        # )

        # self.pbi_tools = PBIManager(
        #     logger=self.logger,
        #     settings=self.settings,
        # )

        self.logger.info(f"'{self}' object initialized.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def check_model_dir(self) -> None:

        model_dir_exists = self.files.check_dir(
            dir_path=self.paths['model_dir'],
            files_names_list=constants._SETUP_FILES_LIST,
        )
        if model_dir_exists:
            self.logger.info('Model directory and required setup files exist.')
        else:
            msg = 'Model directory or required setup files are missing.'
            self.logger.error(msg)
            raise ModelFolderError(msg)

    def load_settings(self) -> None:
        """Load settings from a file, allowing users to overwrite existing
        settings if present.
        """
        if self.settings is not None:
            self.logger.warning('Settings already loaded.')
            user_input = input('Overwrite settings? (y/[n]): ')
            if user_input.lower() != 'y':
                self.logger.info('Settings not overwritten.')
                return
            else:
                self.logger.info('Updating settings.')
        else:
            self.logger.info('Loading settings.')

        self.settings = self.files.load_file(
            file_name=constants._SETTINGS_FILE_NAME,
            dir_path=self.paths['model_dir'],
        )

    def load_paths(self) -> None:

        self.logger.info('Loading paths from settings.')

        self.paths['input_data_dir'] = Path(
            self.paths['model_dir'],
            self.settings['input_data']['input_data_dir_name']
        )
        self.paths['sets_excel_file'] = Path(
            self.paths['model_dir'],
            self.settings['input_data']['sets_xlsx_file_name']
        )
        self.paths['sqlite_database'] = Path(
            self.paths['model_dir'],
            self.settings['sqlite_database']['name']
        )
        self.paths['pbi_report'] = Path(
            self.paths['model_dir'],
            self.settings['powerbi_report']['name']
        )

    # def load_model_coordinates(self) -> None:
    #     self.core.index.load_sets_to_index(
    #         excel_file_name=self.settings['database']['sets_excel_file_name'],
    #         excel_file_dir_path=self.paths['model_dir'])

    #     if self.settings['model']['use_existing_database']:
    #         self.logger.info(
    #             "Relying on existing SQL database "
    #             f"'{self.settings['database']['name']}'."
    #         )
    #     else:
    #         self.core.database.load_sets_to_database()

    #     self.core.index.load_vars_table_headers_to_index()
    #     self.core.index.load_vars_coordinates_to_index()
    #     self.core.index.load_sets_parsing_hierarchy()

    #     if self.settings['database']['foreign_keys']:
    #         self.core.index.load_foreign_keys_to_vars_index()

    # def generate_blank_database(self) -> None:
    #     if self.settings['model']['use_existing_database']:
    #         db_name = self.settings['database']['name']
    #         self.logger.info(f"Relying on existing SQL database '{db_name}'.")
    #     else:
    #         self.core.database.generate_blank_vars_sql_tables()
    #         self.core.database.generate_blank_vars_input_files()

    #     if self.settings['model']['generate_powerbi_report']:
    #         self.pbi_tools.generate_powerbi_report()

    # def load_data_files_to_database(
    #         self,
    #         operation: str = 'overwrite',
    # ) -> None:
    #     self.core.database.load_data_input_files_to_database(
    #         operation=operation)

    # def initialize_problem(self) -> None:
    #     self.core.initialize_problem_variables()
    #     self.core.data_to_cvxpy_exogenous_vars()

    # def load_results_to_database(
    #         self,
    #         operation: str = 'overwrite'
    # ) -> None:
    #     self.core.cvxpy_endogenous_data_to_database(operation=operation)

    # def erase_model(self) -> None:
    #     self.logger.warning(
    #         f"Erasing model {self.settings['model']['name']}.")
    #     self.files.erase_dir(self.paths['model_dir'])

    # def update_database_and_problem(self) -> None:
    #     self.load_data_files_to_database()
    #     self.initialize_problem()
