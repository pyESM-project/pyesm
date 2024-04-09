from pathlib import Path
from typing import Any

from esm import constants
from esm.log_exc.logger import Logger
from esm.log_exc.exceptions import *
from esm.support.dotdict import DotDict
from esm.support.file_manager import FileManager
from esm.support.pbi_manager import PBIManager
from esm.base.core import Core


class Model:

    def __init__(
            self,
            model_dir_name: str,
            main_dir_path: str,
            use_existing_data: bool = False,
            multiple_input_files: bool = False,
            log_level: str = 'info',
            log_format: str = 'minimal',
            sets_xlsx_file: str = 'sets.xlsx',
            input_data_dir: str = 'input_data',
            input_data_file: str = 'input_data.xlsx',
            sqlite_database_file: str = 'database.db',
            sqlite_database_foreign_keys: bool = True,
            powerbi_report_file: str = 'dataset.pbix',
    ) -> None:

        self.logger = Logger(
            logger_name=str(self),
            log_level=log_level.upper(),
            log_format=log_format,
        )

        self.logger.debug(f"'{self}' object initialization...")
        self.logger.info(
            f"Generating '{model_dir_name}' pyESM model instance.")

        self.files = FileManager(logger=self.logger)

        self.settings = DotDict({
            'model_name': model_dir_name,
            'use_existing_data': use_existing_data,
            'multiple_input_files': multiple_input_files,
            'sets_xlsx_file': sets_xlsx_file,
            'input_data_dir': input_data_dir,
            'input_data_file': input_data_file,
            'sqlite_database_file': sqlite_database_file,
            'sqlite_database_foreign_keys': sqlite_database_foreign_keys,
            'powerbi_report_file': powerbi_report_file,
        })

        model_dir_path = Path(main_dir_path) / model_dir_name
        self.paths = DotDict({
            'model_dir': model_dir_path,
            'input_data_dir': model_dir_path / input_data_dir,
            'sets_excel_file': model_dir_path / sets_xlsx_file,
            'sqlite_database': model_dir_path / sqlite_database_file,
            'pbi_report': model_dir_path / powerbi_report_file,
        })

        self.validate_model_dir()

        self.core = Core(
            logger=self.logger,
            files=self.files,
            settings=self.settings,
            paths=self.paths,
        )

        if self.settings['use_existing_data']:
            self.load_model_coordinates()
            self.initialize_problems()

        self.pbi_tools = PBIManager(
            logger=self.logger,
            settings=self.settings,
            paths=self.paths,
        )

        self.logger.debug(f"'{self}' object initialized.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def validate_model_dir(self) -> None:
        """Check if model directory and all the required setup files exist.
        """
        # modify to check if all necessary items are there in case of use existing data
        if self.files.dir_files_check(
            dir_path=self.paths['model_dir'],
            files_names_list=constants._SETUP_FILES.values(),
        ):
            self.logger.info(
                'Model directory and required setup files validated.')

    def load_model_coordinates(self) -> None:

        if self.settings['use_existing_data']:
            self.logger.info(
                'Loading existing sets data and variable coordinates to Index.')
        else:
            self.logger.info(
                'Loading new sets data and variable coordinates to Index.')

        try:
            self.core.index.load_sets_data_to_index(
                excel_file_name=self.settings['sets_xlsx_file'],
                excel_file_dir_path=self.paths['model_dir'])
        except FileNotFoundError:
            msg = f"'{self.settings['sets_xlsx_file']}' file " \
                "missing. Set 'use_existing_data' to False to " \
                "generate a new settings file."
            self.logger.error(msg)
            raise SettingsError(msg)

        self.core.index.load_coordinates_to_data_index()
        self.core.index.load_coordinates_to_variables_index()
        self.core.index.map_vars_aggregated_dims()
        self.core.index.identify_child_variables()

        if self.settings['sqlite_database_foreign_keys']:
            self.core.index.fetch_foreign_keys_to_data_tables()

    def initialize_blank_data_structure(self) -> None:
        sqlite_db_name = self.settings['sqlite_database_file']

        if self.settings['use_existing_data']:
            self.logger.info(
                "Relying on existing SQLite database and input excel file/s.")
            return

        if Path(self.paths['sqlite_database']).exists():
            self.logger.info(f"Database '{sqlite_db_name}' already exists.")

            erased = self.files.erase_file(
                dir_path=self.paths['model_dir'],
                file_name=sqlite_db_name,
                force_erase=False,
                confirm=True,
            )

            if erased:
                self.logger.info(
                    f"Erasing SQLite database '{sqlite_db_name}'. Generating "
                    "new database and excel input file/s.")
            else:
                self.logger.info(
                    f"Relying on existing SQLite database '{sqlite_db_name}' "
                    "and on existing input excel file/s.")
                return
        else:
            self.logger.info(
                f"Generating new SQLite database '{sqlite_db_name}' and "
                "input excel file/s.")

        self.core.database.create_blank_sqlite_database()
        self.core.database.load_sets_to_sqlite_database()
        self.core.database.generate_blank_sqlite_data_tables()
        self.core.database.sets_data_to_vars_sql_tables()
        self.core.database.generate_blank_data_input_files()

    def load_exogenous_data_to_sqlite_database(
            self,
            operation: str = 'update',
            force_overwrite: bool = False,
    ) -> None:
        self.logger.info('Loading input data to SQLite database.')
        self.core.database.load_data_input_files_to_database(
            operation,
            force_overwrite
        )
        # to be completed by automatically filling data
        self.core.database.empty_data_completion(operation)

    def initialize_problems(
            self,
            force_overwrite: bool = False,
    ) -> None:
        self.logger.info(
            'Loading symbolic problem, initializing numerical problems.')
        self.core.initialize_problems_variables()
        self.core.data_to_cvxpy_exogenous_vars()
        self.core.define_numerical_problems(force_overwrite)

    def run_model(
            self,
            solver: str = 'GUROBI',
            verbose: bool = True,
            **kwargs: Any,
    ) -> None:
        self.logger.info('Running numerical model.')
        self.core.solve_numerical_problems(
            solver=solver,
            verbose=verbose,
            **kwargs
        )

    def load_results_to_database(
            self,
            operation: str = 'update'
    ) -> None:
        self.logger.info(
            'Exporting endogenous model results to SQLite database.')
        self.core.cvxpy_endogenous_data_to_database(operation)

    def update_database_and_problem(
            self,
            operation: str = 'update',
            force_overwrite: bool = False,
    ) -> None:
        self.logger.info(f"Updating SQLite database and initialize problems.")
        self.load_exogenous_data_to_sqlite_database(operation, force_overwrite)
        self.initialize_problems(force_overwrite)

    def generate_pbi_report(self) -> None:
        self.logger.info(
            "Generating PowerBI report "
            f"'{self.settings['powerbi_report_file']}'.")
        self.pbi_tools.generate_powerbi_report()

    def erase_model(self) -> None:
        self.logger.warning(f"Erasing model {self.settings['model_name']}.")
        self.files.erase_dir(self.paths['model_dir'])
