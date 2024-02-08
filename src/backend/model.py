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

        self.paths = {
            'model_dir': Path(main_dir_path) / model_dir_name
        }

        self.check_model_dir()
        self.load_settings()
        self.load_paths()

        self.core = Core(
            logger=self.logger,
            files=self.files,
            settings=self.settings,
            paths=self.paths,
        )

        if self.settings['model']['use_existing_data']:
            self.load_model_coordinates()
            self.initialize_problem()

        self.pbi_tools = PBIManager(
            logger=self.logger,
            settings=self.settings,
        )

        self.logger.info(f"'{self}' object initialized.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def check_model_dir(self) -> None:
        """Check if model directory and all the required setup files exist.
        """
        if self.files.dir_files_check(
            dir_path=self.paths['model_dir'],
            files_names_list=constants._SETUP_FILES.values(),
        ):
            self.logger.info('Model directory and required setup files exist.')

    def load_settings(self) -> None:
        """Load settings from settings.yml, allowing users to overwrite 
        existing settings if present.
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
            file_name=constants._SETUP_FILES['settings'],
            dir_path=self.paths['model_dir'],
        )

    def load_paths(self) -> None:

        self.logger.info('Loading paths from settings.')

        self.paths['input_data_dir'] = Path(
            self.paths['model_dir'],
            self.settings['input_data']['input_data_dir']
        )
        self.paths['sets_excel_file'] = Path(
            self.paths['model_dir'],
            self.settings['input_data']['sets_xlsx_file']
        )
        self.paths['sqlite_database'] = Path(
            self.paths['model_dir'],
            self.settings['sqlite_database']['name']
        )
        self.paths['pbi_report'] = Path(
            self.paths['model_dir'],
            self.settings['powerbi_report']['name']
        )

    def load_model_coordinates(self) -> None:

        if self.settings['model']['use_existing_data']:
            self.logger.info(
                'Loading existing sets data and variable coordinates.')
        else:
            self.logger.info(
                'Loading new sets data and variable coordinates.')

        self.core.index.load_sets_to_index(
            excel_file_name=self.settings['input_data']['sets_xlsx_file'],
            excel_file_dir_path=self.paths['model_dir'])

        self.core.index.load_vars_coordinates_to_index()

        if self.settings['sqlite_database']['foreign_keys']:
            self.core.index.load_foreign_keys_to_vars_index()

    def initialize_blank_database(self) -> None:

        if self.settings['model']['use_existing_data']:
            self.logger.info(
                "Relying on existing SQL database "
                f"'{self.settings['sqlite_database']['name']}'.")
            return

        self.logger.info(
            'Generating blank SQLite database and excel input files.')

        self.core.database.load_sets_to_database()
        self.core.database.generate_blank_vars_sql_tables()
        self.core.database.generate_blank_vars_input_files()

    def load_data_files_to_database(
            self,
            operation: str = 'overwrite',
    ) -> None:

        self.logger.info('Loading input data to SQLite database.')
        self.core.database.load_data_input_files_to_database(operation)

    def initialize_problem(self) -> None:

        self.logger.info('Initializing numerical problem.')
        self.core.initialize_problem_variables()
        self.core.data_to_cvxpy_exogenous_vars()

        # provide a model.core.problem attribute with technical specs of the problem

    def solve_problem(self) -> None:

        self.logger.info('Solving numerical problem.')

    def load_results_to_database(
            self,
            operation: str = 'overwrite'
    ) -> None:

        self.core.cvxpy_endogenous_data_to_database(operation)

    def update_database_and_problem(self) -> None:

        self.logger.info(f"Updating ")
        self.load_data_files_to_database()
        self.initialize_problem()

    def generate_pbi_report(self) -> None:

        self.pbi_tools.generate_powerbi_report()

    def erase_model(self) -> None:

        self.logger.warning(
            f"Erasing model {self.settings['model']['name']}.")
        self.files.erase_dir(self.paths['model_dir'])
