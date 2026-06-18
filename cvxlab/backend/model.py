"""Module defining the Model class.

This module defines the Model class, the main object of the CVXLab package,
in charge of getting the main model settings and paths, and providing all the 
methods useful for the user to handle the model and its main functionalities.
The Model class integrates various components such as logging, file management,
and core functionalities, ensuring a cohesive workflow from numerical problem
conceptualization, database generation and data input, numerical problem generation
and solution, results export to database.
The Model class embeds the generation of the Core class, which provides the centralized
data indexing, functionalities for SQLite database management, problem formulation 
and solution through cvxpy package. 
"""
from pathlib import Path
from typing import Any, List, Optional

import pandas as pd

from cvxlab.defaults import Defaults
from cvxlab.backend.core import Core
from cvxlab.log_exc import exceptions as exc
from cvxlab.log_exc.logger import Logger
from cvxlab.support.dotdict import DotDict
from cvxlab.support.file_manager import FileManager
from cvxlab.support import util
from dataclasses import dataclass, field
import shutil


@dataclass
class sampling_settings_config:
    """Container for user-defined uncertainty analysis configuration.

    This dataclass stores the sampling configuration specified by the user
    through the `Model.sampling_settings()` method.b The stored configuration is
    used by `Model.run_uncertainty_analysis()` to generate samples and execute iterative model runs.

    Attributes:
        method (str): Sampling method name (e.g. 'lhs', 'sobol', 'morris').
        method_kwargs (dict[str, Any]): Keyword arguments required by the
            selected sampling method (e.g. N, seed, num_levels).
        save_samples (bool): Whether generated samples should be saved to file.
        file_format (str): Output file format for saving samples
            (e.g. 'xlsx', 'csv', 'parquet').
    """
    method: str
    method_kwargs: dict[str, Any] = field(default_factory=dict)
    groups: bool = False
    save_samples: bool = True
    save_measures: bool = True
    file_format: str = "xlsx"


@dataclass
class GSA_settings_config:
    """
    Container for user-defined GSA analysis configuration.
    """
    method: str
    method_kwargs: dict[str, Any] = field(default_factory=dict)
    measures: list[str] | None = None
    scenarios: list[str] | None = None
    save_analysis: bool = True
    file_format: str = "xlsx"


class Model():
    """Central class for generating and handling a CVXLab models.

    The Model class represents a modeling environment that handles SQLite data 
    generation and processing, database interactions, numerical optimization 
    model generation and handling with cvxpy package. 
    This class initializes with a configuration for managing directories, 
    logging, and file management for a specific model. It also sets up various
    components including a logger, file manager, and core functionalities.

    Attributes:

    - logger (Logger): Logger object for logging information, warnings, and errors.
    - files (FileManager): An instance of FileManager to manage file operations.
    - settings (DotDict): A dictionary-like object storing configurations such as \
        model name, file paths, and operational flags.
    - paths (DotDict): A dictionary-like object storing the paths for model \
        directories and associated files.
    - core (Core): An instance of Core that manages the core functionality of the \
        model (it embeds Index, Database and Problem instances).

    """

    def __init__(
            self,
            model_dir_name: str = 'model',
            main_dir_path: Optional[str] = None,
            uncertainty: bool = False,
            model_settings_from: Defaults.LiteralTypes.SettingsSource = 'xlsx',
            detailed_validation: bool = False,
            use_existing_data: bool = False,
            multiple_input_files: bool = False,
            input_data_files_type: Defaults.LiteralTypes.DataFileType = 'xlsx',
            log_level: Defaults.LiteralTypes.LogLevel = 'info',
            log_format: Defaults.LiteralTypes.LogFormat = 'standard',
    ):
        """Initialize the Model instance with specified configurations.

        This constructor sets up the Model instance by initializing logging,
        file management, and core functionalities. It also checks for the
        existence of the model directory and required setup files. If the
        'use_existing_data' flag is set to True, it loads existing sets data
        and variable coordinates to the Model.Index and initializes numerical
        problems (the configuration files and model database should have been
        already generated).

        Args:
            model_dir_name (str): The name of the model directory.
            main_dir_path (str): The main directory path where the model
                directory is located. If None, the current working directory is used.
            uncertainty (bool, optional): If True, enables uncertainty-related
                template settings.
                Defaults to False.
            model_settings_from (Defaults.LiteralTypes.SettingsSource, optional): 
                The format of the model settings file. Can be either 'yml' or 'xlsx'. 
                Defaults to 'xlsx'.
            detailed_validation (bool, optional): if True, performs detailed
                validation logging of data and model settings during initialization.
                Defaults to False.
            use_existing_data (bool, optional): if True, generation of Model
                instance is also loading model coordinates and initializing
                numerical problems. Note that setup files and model database should
                have been already generated. Defaults to False.
            multiple_input_files (bool, optional): if True, input data Excel files
                are generated as one file per data table. If False, all data tables
                are generated in a single Excel file with multiple tabs. Defaults 
                to False.
            input_data_files_type (Defaults.LiteralTypes.DataFileType, optional): 
                The format of the input data files. Can be either 'xlsx' or 'csv'. 
                Defaults to 'xlsx'.
            log_level (Defaults.LiteralTypes.LogLevel, optional):
                The logging level for the logger. Defaults to 'info'.
            log_format (Defaults.LiteralTypes.LogFormat, optional): The logging 
                format for the logger. Defaults to 'standard'.
        """
        config = Defaults.ConfigFiles

        if main_dir_path is None:
            main_dir_path = str(Path.cwd())

        model_dir_path = Path(main_dir_path) / model_dir_name

        self.logger = Logger(
            logger_name=str(self),
            log_level=log_level.upper(),
            log_format=log_format,
        )

        with self.logger.log_timing(
            message=f"Model instance generation...",
            level='info',
        ):
            self.files = FileManager(logger=self.logger)
            uncertainty_setting_key = Defaults.Labels.UNCERTAINTY_SETTING_KEY

            self.settings = DotDict({
                'log_level': log_level,
                'model_name': model_dir_name,
                uncertainty_setting_key: uncertainty,
                'model_settings_from': model_settings_from,
                'use_existing_data': use_existing_data,
                'multiple_input_files': multiple_input_files,
                'input_data_files_type': input_data_files_type,
                'detailed_validation': detailed_validation,
            })

            self.paths = DotDict({
                'model_dir': model_dir_path,
                'input_data_dir': model_dir_path / config.INPUT_DATA_DIR,
                'sets_excel_file': model_dir_path / config.SETS_FILE,
                'sqlite_database': model_dir_path / config.SQLITE_DATABASE_FILE,
            })

            self._check_model_dir()
            self._check_settings_consistency()
            self._import_custom_scripts()

            self.core = Core(
                logger=self.logger,
                files=self.files,
                settings=self.settings,
                paths=self.paths,
            )

            self._sampling_settings: sampling_settings_config | None = None
            self._GSA_settings: GSA_settings_config | None = None

            self.sampling_problem: dict[str, Any] | None = None
            self.uncertainty_samples: pd.DataFrame | None = None
            self.uncertainty_measures: pd.DataFrame | None = None
            self.par_mapping: pd.DataFrame | None = None
            self.gsa_results: pd.DataFrame | None = None

            if self.settings['use_existing_data']:
                self._load_model_coordinates()
                self._initialize_problems()

    @property
    def sets(self) -> List[str]:
        """List of sets names available in the model.

        Returns:
            List[str]: A list of set names.
        """
        return self.core.index.list_sets

    @property
    def data_tables(self) -> List[str]:
        """List of data tables names available in the model.

        Returns:
            List[str]: A list of data table names.
        """
        return self.core.index.list_data_tables

    @property
    def variables(self) -> List[str]:
        """List of variables names available in the model.

        Returns:
            List[str]: A list of variable names.
        """
        return self.core.index.list_variables

    @property
    def is_problem_solved(self) -> bool:
        """Status of the problem solution.

        Checks if the numerical problem has been solved (even if it has not 
        found a numerical solution).

        Returns:
            bool: True if the problem has been solved, False otherwise.
        """
        if self.core.problem.problem_status is None:
            return False
        else:
            return True

    @property
    def is_uncertainty_analysis(self) -> bool:
        return bool(self.settings.get(
            Defaults.Labels.UNCERTAINTY_SETTING_KEY,
            False,
        ))

    def _check_model_dir(self) -> None:
        """Validate the existence of the model directory and required files.

        This method checks if the model directory and all the required files exist.
        This method is called during the initialization of the Model instance, and 
        it is not meant to be called directly by the user.

        Depending on the 'use_existing_data' flag, the method checks for the existence
        of different files: if the flag is set to False, it checks for the existence
        of the basic model settings files (.yml or .xlsx). If the flag is set to 
        True, it also includes in the check the existence of the SQLite database file,
        the sets Excel file, and the input data directory.

        Raises:
            exc.SettingsError: If the 'model_settings_from' parameter is not recognized.
            exc.SettingsError: If the model directory or any of the required 
                setup files are missing.
        """
        files_type = self.settings['model_settings_from']
        model_dir_path = self.paths['model_dir']
        files_to_check = []
        subdir_to_check = []

        util.validate_selection(
            valid_selections=Defaults.ConfigFiles.AVAILABLE_SETUP_SOURCES,
            selection=files_type,
        )

        if files_type == 'yml':
            files_to_check += [
                file + '.yml'
                for file in Defaults.ConfigFiles.SETUP_INFO.values()
            ]
        elif files_type == 'xlsx':
            files_to_check += [Defaults.ConfigFiles.SETUP_XLSX_FILE]

        if self.settings['use_existing_data']:
            files_to_check += [
                Defaults.ConfigFiles.SETS_FILE,
                Defaults.ConfigFiles.SQLITE_DATABASE_FILE,
            ]
            subdir_to_check += [Defaults.ConfigFiles.INPUT_DATA_DIR]

        err_msg = []

        if not Path(model_dir_path).exists():
            self.logger.error(
                "Model directory validation | Model directory is missing."
            )
            raise exc.SettingsError("Model directory validation | Failed.")

        for subdir in subdir_to_check:
            if not Path(model_dir_path / subdir).exists():
                err_msg.append(
                    f"Model directory validation | '{subdir}' directory is missing."
                )

        for file in files_to_check:
            if not Path(model_dir_path / file).exists():
                err_msg.append(
                    f"Model directory validation | '{file}' file is missing."
                )

        if err_msg == []:
            self.logger.debug(
                f"Model directory validation | Success.")
        else:
            [self.logger.error(msg) for msg in err_msg]
            raise exc.SettingsError("Model directory validation | Failed.")

    def _check_settings_consistency(self) -> None:
        """Check consistency of model settings.

        This method checks the consistency of the model settings, ensuring that
        the configurations provided by the user are coherent.
        This method is called during the initialization of the Model instance, and 
        it is not meant to be called directly by the user.

        Raises:
            exc.SettingsError: If any inconsistency or invalid configuration 
                is found in the model settings.
        """
        err_msg = []

        # Check that input data csv files are only used for multiple input files
        if self.settings['input_data_files_type'] == 'csv' and not \
                self.settings['multiple_input_files']:
            err_msg.append(
                "Input data files of type 'csv' can only be used when "
                "'multiple_input_files' setting is True."
            )

        # Add further checks below...

        if err_msg == []:
            self.logger.debug(
                f"Model settings validation | Success.")
        else:
            [self.logger.error(msg) for msg in err_msg]
            raise exc.SettingsError("Model settings validation | Failed.")

    def _import_custom_scripts(self) -> None:
        """Import user-defined custom operators and constants.

        This method automatically imports user-defined custom operators and constants from
        the model directory if the corresponding files are present. No user flags required.

        Raises:
            FileNotFoundError: If the specified custom operators or constants 
                files are not found in the model directory.    
        """
        custom_scripts = {
            'operators': {
                'file_name': Defaults.ConfigFiles.CUSTOM_OPERATORS_FILE_NAME,
                'target_registry': Defaults.SymbolicDefinitions.ALLOWED_OPERATORS,
            },
            'constants': {
                'file_name': Defaults.ConfigFiles.CUSTOM_CONSTANTS_FILE_NAME,
                'target_registry': Defaults.SymbolicDefinitions.ALLOWED_CONSTANTS,
            }
        }

        for script_type, config in custom_scripts.items():

            custom_functions = self.files.load_functions_from_module(
                dir_path=self.paths['model_dir'],
                file_name=config['file_name'],
            )

            if not custom_functions:
                self.logger.debug(
                    f"Custom '{script_type}' import | Function(s) not defined "
                    f"or '{config['file_name']}' not found."
                )
                continue

            # register functions
            for function in custom_functions:
                function_name = function.__name__
                config['target_registry'][function_name] = function

            self.logger.debug(
                f"Custom '{script_type}' import | Imported "
                f"{len(custom_functions)} custom "
                f"function{'s' if len(custom_functions) != 1 else ''} "
                f"from '{config['file_name']}'."
            )

    def _load_model_coordinates(self) -> None:
        """Load sets data and define data tables/variables coordinates.

        This method fetches sets data from Excel to sets instances. It then 
        loads such data (referred as coordinates) to data tables and to variables. 
        Then, it filter variables coordinates based on user defined filters, and 
        checks variables coherence.
        If the 'use_existing_data' flag is set to True, this method is called 
        during the initialization of the Model instance, and it is not meant to
        be called directly by the user.
        If the 'use_existing_data' flag is set to False, this method is called 
        into Model.prepare_model_environment, after having defined model settings 
        (data tables, variables, symbolic problem), generated the model instance, 
        and having filled the sets Excel file with model coordinates.

        Raises:
            exc.SettingsError: If the sets Excel file specified in the settings 
                is missing.
        """
        with self.logger.log_timing(
            message=f"Loading sets and variables coordinates...",
            level='info',
        ):
            try:
                sets_xlsx_file = Defaults.ConfigFiles.SETS_FILE
                self.core.index.load_sets_data_to_index(
                    excel_file_name=sets_xlsx_file,
                    excel_file_dir_path=self.paths['model_dir']
                )
            except FileNotFoundError as e:
                msg = f"'{sets_xlsx_file}' file missing. Set 'use_existing_data' " \
                    "to False to generate a new settings file."
                self.logger.error(msg)
                raise exc.SettingsError(msg) from e

            self.core.index.load_coordinates_to_data_index()
            self.core.index.load_all_coordinates_to_variables_index()
            self.core.index.filter_coordinates_in_variables_index()
            self.core.index.check_variables_coherence()
            self.core.index.fetch_foreign_keys_to_data_tables()

    def _initialize_blank_data_structure(self) -> None:
        """Initialize blank data structure for the model.

        This method generates the fundamental blank data structure for the model.
        If the SQLite database already exists, it gives the option to erase it 
        and generate a new one, or to work with the existing SQLite database.
        Same for the input data directory.
        Specifically, the method creates:

        - A blank SQLite database with set tables and data tables, filling data 
            tables with sets information.
        - A blank Excel input data file/s with normalized data tables for getting
            exogenous variables data from the user. 

        """
        use_existing_data = self.settings['use_existing_data']
        sqlite_db_name = Defaults.ConfigFiles.SQLITE_DATABASE_FILE
        sqlite_db_path = Path(self.paths['sqlite_database'])
        input_files_dir_path = Path(self.paths['input_data_dir'])

        erased_db = False
        erased_input_dir = False

        if use_existing_data:
            self.logger.info(
                "Relying on existing SQLite database and input excel file/s.")
            return

        with self.logger.log_timing(
            message=f"Generation of blank data structures...",
            level='info',
        ):
            if sqlite_db_path.exists():
                erased_db = self.files.erase_file(
                    dir_path=self.paths['model_dir'],
                    file_name=sqlite_db_name,
                    force_erase=False,
                    confirm=True,
                )

            if erased_db:
                self.logger.info(
                    f"Existing SQLite database '{sqlite_db_name}' erased.")

            if erased_db or not sqlite_db_path.exists():
                self.logger.info(
                    f"Creating new blank SQLite database '{sqlite_db_name}'.")
                self.core.database.create_blank_sqlite_database()
                self.core.database.load_sets_to_sqlite_database()
                self.core.database.generate_blank_sqlite_data_tables()
                self.core.database.sets_data_to_sql_data_tables()
            else:
                self.logger.info(
                    f"Relying on existing SQLite database '{sqlite_db_name}' ")

            if input_files_dir_path.exists():
                erased_input_dir = self.files.erase_dir(
                    dir_path=input_files_dir_path,
                    force_erase=False,
                )

                if erased_input_dir:
                    self.logger.info("Existing input data directory erased.")

            if erased_input_dir or not input_files_dir_path.exists():
                self.logger.info(
                    "Generating new blank input data directory and related file/s.")
                self.core.database.generate_blank_data_input_files()
            else:
                self.logger.info("Relying on existing input data directory.")

    def _load_exogenous_data_to_sqlite_database(
            self,
            force_overwrite: bool = False,
            table_key_list: list[str] = [],
    ) -> None:
        """Load exogenous (input) data to the SQLite database.

        This method loads exogenous (input) data from Excel file/s to the
        SQLite database. It also fills NaN values in the database with Null
        values, to ensure proper handling of missing data in SQLite.
        This method is called directly by the user after having filled the
        input data Excel file/s with exogenous data.
        However, the method is also called within the 'update_database_and_problem'
        method, which can be used in case some changes in exogenous data have been
        made, so that the SQLite database and the problems can be updated without
        re-generating the Model instance.
        The user can choose to load data for all exogenous data tables, or for
        specific data tables (with the 'table_key_list' attribute).

        Args:
            force_overwrite (bool, optional): Whether to force overwrite existing 
                data without asking for user permission. Defaults to False.
            table_key_list (list[str], optional): A list of data table keys 
                for which to load exogenous data. If empty, all exogenous data
                tables are loaded. Defaults to [].
        """
        with self.logger.log_timing(
            message=f"Loading input data to SQLite database...",
            level='info',
        ):
            self.core.database.load_data_input_files_to_database(
                force_overwrite=force_overwrite,
                table_key_list=table_key_list,
            )

            self.core.database.fill_nan_values_in_database(
                force_overwrite=force_overwrite,
                table_key_list=table_key_list,
            )

    def load_data(
            self,
            force_overwrite: bool = False,
            table_key_list: list[str] = [],
    ) -> None:
        """Load exogenous input data into the SQLite database.

        This is the public interface for loading user-filled input data files into
        the model SQLite database. It wraps the internal data-loading routine, which
        imports exogenous data and normalizes missing values as SQLite NULL values.

        Args:
            force_overwrite (bool, optional): If True, overwrite existing table data
                without asking for user confirmation. Defaults to False.
            table_key_list (list[str], optional): List of exogenous data table keys
                to load. If empty, all exogenous input data tables are loaded.
                Defaults to [].
        """
        self._load_exogenous_data_to_sqlite_database(
            force_overwrite=force_overwrite,
            table_key_list=table_key_list,
        )

        if self.is_uncertainty_analysis:
            self.core.uncertainty.validate_uncertainty_data()

    def _initialize_problems(
            self,
            force_overwrite: bool = False,
            allow_none_values: bool = True,
    ) -> None:
        """Initialize numerical problems in the Model instance.

        This method intializes numerical problems in the Model instance. 
        Specifically, the method loads and validates symbolic mathematical problems,
        checks if all exogenous data have coherently defined by user, and finally
        generates numercal problem (i.e. initializes variables, feeds data to 
        exogenous variables, and generates cvxpy problem/s).

        Args:
            force_overwrite (bool, optional): If True, forces the overwrite 
                of existing numerical problems without asking for user 
                permission. Used for testing purposes. Defaults to False.
            allow_none_values (bool, optional): If True, allows None values in
                the exogenous data. Defaults to True.
        """
        with self.logger.log_timing(
            message=f"Numerical model generation...",
            level='info',
        ):
            self.core.load_and_validate_symbolic_problem(force_overwrite)
            self.core.check_exogenous_data_coherence()
            self.core.generate_numerical_problem(
                allow_none_values, force_overwrite)

    def initialize_model_environment(self) -> None:
        """Initialize the model environment for problem generation and solution.

        This method prepares the model environment by loading sets data and 
        coordinates, and initializing blank data structures (SQLite database and
        input data files). This method is typically called after having generated
        the Model instance, and before generating numerical problems and solving them.
        If the 'use_existing_data' flag is set to True, this method is not meant to be 
        called, since sets data and coordinates are already loaded, and blank data 
        structures are not generated relying on existing ones.

        Raises:
            exc.SettingsError: If the sets Excel file specified in the settings 
                is missing when loading model coordinates.
        """
        if self.settings['use_existing_data']:
            self.logger.info(
                "Relying on existing model environment (sets coordinates, "
                "SQLite database, input data files)."
            )
            return

        self._load_model_coordinates()

        if self.settings[Defaults.Labels.UNCERTAINTY_SETTING_KEY]:
            self.core.uncertainty.check_uncertainty_measure_variables_are_scalar()

        self._initialize_blank_data_structure()

    def refresh_database_and_initialize_problem(
            self,
            table_key_list: list[str] = [],
            force_overwrite: bool = False,
    ) -> None:
        """Update SQLite database with exogenous data and initialize problems.

        This method loads the SQLite database exogenous data, and then initializes 
        numerical problems. 
        This method can be used for both initialization of the model environment, 
        after having generated the Model instance, and for updating the model 
        environment and the problems in case some changes in input data have been 
        made, without the need of re-generating the Model instance. 

        Args:
            table_key_list (list[str], optional): A list of data table keys 
                for which to load exogenous data. If empty, all exogenous data
                tables are loaded. Defaults to [].
            force_overwrite (bool, optional): Whether to overwrite/update 
                existing data without asking user permission. Defaults to False.
        """
        sqlite_db_file = Defaults.ConfigFiles.SQLITE_DATABASE_FILE

        self.logger.info(
            f"Loading exogenous data into SQLite database '{sqlite_db_file}' "
            "and initializing problems.")

        self._load_exogenous_data_to_sqlite_database(
            force_overwrite, table_key_list)

        self._initialize_problems(force_overwrite)

    def run_model(
        self,
        force_overwrite: bool = False,
        integrated_problems: bool = False,
        convergence_monitoring: bool = True,
        solver: Optional[str] = None,
        solver_verbose: bool = False,
        solver_settings: Optional[dict[str, Any]] = None,
        convergence_norm: Defaults.LiteralTypes.NormType = 'l2',
        convergence_tables_to_check: Defaults.LiteralTypes.ConvergenceTables | List[
            str] = 'all_endogenous',
        convergence_tables_to_skip: Optional[List[str]] = None,
        relative_tolerance: Optional[float] = None,
        maximum_iterations: Optional[int] = None,
        keep_previous_iteration_db: bool = False,
        **kwargs: Any,
    ) -> None:
        """Solve numerical problems defined by the model instance.

        This method first performs some coherence checks (if solver is supported,
        if numerical problems are defined, if integrated problems are possible).
        Then, it solves the numerical problems, either independently or in an
        integrated manner, based on the 'integrated_problems' flag.
        Finally, it logs a summary of the problems status.

        Args:
            force_overwrite (bool, optional): If True, overwrites existing results. 
                Defaults to False.
            integrated_problems (bool, optional): If True, solve problems iteratively 
                using a block Gauss-Seidel (alternating optimization) scheme, where 
                updated endogenous variables are exchanged until convergence. 
                Defaults to False.
            convergence_monitoring (bool, optional): If True, enables convergence
                monitoring during the solving of integrated problems. Defaults to True.
            solver (str, optional): The solver to use for solving numerical 
                problems. Defaults to None, in which case the default solver 
                specified in 'Defaults.NumericalSettings.CVXPY_DEFAULT_SETTINGS' is used.
            solver_verbose (bool, optional): If True, logs verbose output related to 
                numerical solver operation during the model run. Defaults to False.
            solver_settings (dict[str, Any], optional): Additional settings
                for the solver passed as key-value pairs. Defaults to None.
            convergence_norm (Defaults.LiteralTypes.NormType, optional):
                The norm type to use for convergence monitoring in integrated
                problems. Defaults to 'l2' (Euclidean Norm).
            convergence_tables_to_check (Defaults.LiteralTypes.ConvergenceTables | 
                List[str], optional): The data tables to consider for convergence 
                monitoring in integrated problems. Can be 'all_endogenous', 
                'hybrid_only', or a list of specific data table keys. Defaults 
                to 'all_endogenous'.
            convergence_tables_to_skip (Optional[List[str]], optional): List of data table
                keys to skip for convergence checking in integrated problems. If None,
                no tables are skipped. Defaults to None.
            relative_tolerance (float, optional): Numerical tolerance for verifying
                maximum relative change between iterations in integrated problems for 
                each data table. Overrides 'Defaults.NumericalSettings.MODEL_COUPLING_SETTINGS'.
            maximum_iterations (int, optional): The maximum number of iterations 
                for solving integrated problems. Overrides 
                'Defaults.NumericalSettings.MODEL_COUPLING_SETTINGS'.
            keep_previous_iteration_db (bool, optional): Whether keep or not the database 
                generated during the last-1 iteration. For debugging purpose. Default to 
                False.
            **kwargs: Additional keyword arguments to be passed to the solver. Useful 
                for setting solver-specific options.

        Raises:
            exc.SettingsError: In case solver is not supported by current cvxpy version.
            exc.SettingsError: If no numerical problems are found, or if integrated
                problems are requested but only one problem is found.
        """
        cvxpy_defaults = Defaults.NumericalSettings.CVXPY_DEFAULT_SETTINGS
        cvxpy_allowed_solvers = Defaults.NumericalSettings.ALLOWED_SOLVERS
        sub_problems = self.core.problem.number_of_sub_problems
        problem_scenarios = len(self.core.index.scenarios_info)

        # Merge order: defaults < solver_settings < kwargs < explicit 'solver' arg
        solver_config = {
            **cvxpy_defaults,
            **(solver_settings or {}),
            **kwargs,
        }

        if solver is not None:
            solver_config['solver'] = solver

        selected_solver = solver_config.get('solver', cvxpy_defaults['solver'])

        if selected_solver not in cvxpy_allowed_solvers:
            msg = f"Solver '{selected_solver}' not supported by current CVXPY " \
                f"version. Available solvers: {cvxpy_allowed_solvers}"
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        solver_settings = solver_config.copy()
        solver_settings['solver'] = selected_solver
        solver_settings['verbose'] = solver_verbose

        if sub_problems == 0:
            msg = "Numerical problem not found. Initialize problem first."
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        if integrated_problems and sub_problems == 1:
            msg = "Only one problem found. Integrated problems not possible."
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        if integrated_problems and sub_problems > 1:
            solution_type = 'integrated'
        else:
            solution_type = 'independent'

        problem_count = '1' if sub_problems == 1 else f'{sub_problems}'

        self.logger.info(
            f"Model run | Solution mode: {solution_type}' | Solver: '{solver}' | "
            f"Problems: {problem_count} | Scenarios: {problem_scenarios}")

        if solver_verbose:
            self.logger.info("Model run | CVXPY logs below")

        with self.logger.log_timing(
            message=f"Solving numerical problems...",
            level='info',
        ):
            self.core.solve_numerical_problems(
                force_overwrite=force_overwrite,
                integrated_problems=integrated_problems,
                convergence_monitoring=convergence_monitoring,
                convergence_norm=convergence_norm,
                convergence_tables_to_check=convergence_tables_to_check,
                convergence_tables_to_skip=convergence_tables_to_skip,
                relative_tolerance=relative_tolerance,
                maximum_iterations=maximum_iterations,
                keep_previous_iteration_db=keep_previous_iteration_db,
                **solver_settings,
            )

        msg = "Numerical problems status report:"
        self.logger.info("="*len(msg))
        self.logger.info(msg)

        for info, status in self.core.problem.problem_status.items():
            self.logger.info(
                f"{info}: {status}" if info else f"{status}"
            )

    def load_results_to_database(
        self,
        scenarios_idx: Optional[List[int] | int] = None,
        force_overwrite: bool = False,
        suppress_warnings: bool = False,
    ) -> None:
        """Export model results to the SQLite database.

        This method exports the results of the numerical problems to the SQLite
        database. It can export results for all scenarios or for specific scenarios
        (defined as the linear combinations of inter-problem sets that identify 
        independent numerical problems), based on the 'scenarios_idx' attribute 

        Args:
            scenarios_idx (Optional[List[int] | int], optional): A list of
                scenario indices or a single scenario index for which to export
                results. If None, results for all scenarios are exported. Defaults
                to None.
            force_overwrite (bool, optional): Whether to overwrite/update 
                existing data without asking user permission. Defaults to False.
            suppress_warnings (bool, optional): Whether to suppress warnings 
                during the data loading process. Defaults to False.
        """
        with self.logger.log_timing(
            message=f"Exporting endogenous model results to SQLite database...",
            level='info',
        ):
            if not self.is_problem_solved:
                self.logger.warning(
                    "Numerical problem has not solved yet and results "
                    "cannot be exported.")
                return

            self.core.cvxpy_endogenous_data_to_database(
                scenarios_idx=scenarios_idx,
                force_overwrite=force_overwrite,
                suppress_warnings=suppress_warnings
            )

    def generate_input_data_files(
            self,
            table_key_list: List[str] = [],
            values_cleanup: bool = True,
    ) -> None:
        """Generate blank Excel files for data input.

        This method generates blank Excel files for data input, based on the
        data tables defined in the model. If the input data directory already
        exists, it gives the option to erase it and generate a new one, or to
        work with the existing input data directory.
        This method is called within the 'initialize_blank_data_structure'
        method. However, the user can call it directly to regenerate input
        data file/s, for all or for specific data tables (with the 'table_key_list'
        attribute). This is especially useful in adjusting the input data without 
        regenerating the whole blank data structure. This feature works also in
        case of one single Excel file, since it can overwrite only the tabs
        related to the specified data tables.

        Args:
            table_key_list (List[str], optional): A list of data table keys 
                for which to generate input data files. If empty, all data 
                tables are generated. Defaults to [].
            values_cleanup (bool, optional): Whether to clean up values of 
                database tables before generating input data files. Defaults 
                to True.

        Raises:
            exc.SettingsError: If the input data directory is missing.
            exc.SettingsError: If any of the specified table keys are invalid 
                (i.e., not exogenous data tables).
        """
        input_files_dir_path = Path(self.paths['input_data_dir'])

        if not input_files_dir_path.exists():
            msg = "Input data directory missing. Initialize blank data " \
                "structure first."
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        if table_key_list != [] and not util.items_in_list(
            table_key_list,
            self.core.index.list_exogenous_data_tables
        ):
            msg = "Invalid table key/s provided. Only exogenous data tables " \
                "can be exported to input data files."
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        if table_key_list != []:
            msg = f"Generating input data files for tables: '{table_key_list}'..."
        else:
            msg = "Generating all input data files..."

        with self.logger.log_timing(
            message=msg,
            level='info',
        ):
            self.core.database.generate_blank_data_input_files(
                table_key_list=table_key_list,
                values_cleanup=values_cleanup,
            )

    def reinitialize_sqlite_database(
            self,
            force_overwrite: bool = False
    ) -> None:
        """Reinitialize SQLite database tables and reimport input data.

        This method reinitializes endogenous tables in SQLite database to Null 
        values, and reimports input data to exogenous tables.

        Args:
            force_overwrite (bool, optional): Whether to force overwrite 
                existing data. Used for testing purposes. Defaults to False.
        """
        sqlite_db_file = Defaults.ConfigFiles.SQLITE_DATABASE_FILE

        self.logger.info(
            f"Reinitializing SQLite database '{sqlite_db_file}' "
            "endogenous tables.")

        self.core.database.reinit_sqlite_endogenous_tables(force_overwrite)
        self._load_exogenous_data_to_sqlite_database(force_overwrite)

    def check_model_results(
            self,
            other_db_dir_path: Optional[Path | str] = None,
            other_db_name: Optional[str] = None,
            numerical_tolerance: Optional[float] = None,
    ) -> None:
        """Compare model SQLite database with another SQLite reference database.

        This method compares the results of the model's SQLite database with those
        of another SQLite database, typically for testing purposes. It uses the
        'check_results_as_expected' method to compare the current model's computations
        with the expected results. The expected results can be stored in a specific
        database (identified by directory path and name), or stored in a test database
        specified by the SQLite test database default name and located in the model
        directory.
        Both 'other_db_dir_path' and 'other_db_name' must be provided together, or both
        must be None. If not provided, defaults are used.

        Args:
            other_db_dir_path (Optional[Path | str], optional): The directory path
                where the other SQLite database is located. If None, it defaults
                to the model directory. Defaults to None.
            other_db_name (Optional[str], optional): The name of the other SQLite
                database file. If None, it defaults to the SQLite test database
                default name. Defaults to None.
            numerical_tolerance (float, optional): The relative difference 
                (non-percentage) tolerance for comparing numerical values in 
                different databases. If None, it is set to
                'Defaults.NumericalSettings.TOLERANCE_TESTS_RESULTS_CHECK'.
        """
        if (other_db_dir_path is None) != (other_db_name is None):
            msg = "Both 'other_db_dir_path' and 'other_db_name' parameters must " \
                "be defined together, or both must be None."
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        if other_db_dir_path is None:
            other_db_dir_path = self.paths['model_dir']

        if other_db_name is None:
            other_db_name = Defaults.ConfigFiles.SQLITE_DATABASE_FILE_TEST

        if not numerical_tolerance:
            numerical_tolerance = \
                Defaults.NumericalSettings.TOLERANCE_TESTS_RESULTS_CHECK

        with self.logger.log_timing(
            message=f"Check model results...",
            level='info',
        ):
            self.core.compare_databases(
                values_relative_diff_tolerance=numerical_tolerance,
                other_db_dir_path=other_db_dir_path,
                other_db_name=other_db_name,
            )

    def update_sets_tables(
            self,
            set_keys_list: List[str] = [],
            update_mode: Defaults.LiteralTypes.SetUpdateMode = 'all',
    ) -> None:
        """Update sets tables in the SQLite database.

        This method updates sets tables in the SQLite database. The user can choose
        to update all sets, or only specific sets (with the 'set_keys_list' attribute).
        Additionally, the user can specify the update mode, which can be 'all',
        'filters', or 'aggregations'.

        Args:
            set_keys_list (List[str], optional): A list of set keys to update.
                If empty, all sets are updated. Defaults to [].
            update_mode (Defaults.LiteralTypes.SetUpdateMode, optional):
                The update mode. Can be 'all' (update all set data), 'filters'
                (update only filters), or 'aggregations' (update only aggregations).
                Defaults to 'all'.
        """
        self.core.database.update_sets_in_sqlite_database(
            set_keys_list=set_keys_list,
            update_mode=update_mode,
        )

    def variable(
            self,
            name: str,
            scenario_key: Optional[int] = None,
            intra_problem_key: Optional[int] = None,
            if_hybrid_var: Defaults.LiteralTypes.HybridVarType = 'endogenous',
    ) -> Optional[pd.DataFrame]:
        """Fetch variable data.

        This method retrieves the data for a specified variable based on optional 
        inter-problem and intra-problem sets cardinality, supporting the data 
        inspection process after a model has run, but before data has exported to the 
        database. This is particularly useful in case multiple runs of the model, 
        to facilitate the control of the numerical data from the user.
        In case a variable is defined as both endogeous and exogenous, depending on 
        the numerical problem, the user can specify the one to inspect (default 
        as the endogenous one).
        If the variable is specified for multiple inter- and intra-problem sets,
        scenario_key defines the cardinality of inter-problem sets, while 
        intra_problem_key defines the cardinality of intra-problem sets.

        Args:
            name (str): The key of the variable in the variables dictionary.
            scenario_key (Optional[int]): Defines the cardinality of inter-problem 
                sets. Default to None.
            intra_problem_key (Optional[int]): Defines the cardinality of intra-problem
                sets. Default to None.
            if_hybrid_var (Defaults.LiteralTypes.HybridVarType): Defines the type 
                of variable data to inspect in case variable type depends on the 
                problem.

        Returns:
            Optional[pd.DataFrame]: The data for the specified variable.
        """
        return self.core.index.fetch_variable_data(
            var_key=name,
            scenario_key=scenario_key,
            intra_problem_key=intra_problem_key,
            if_hybrid_var=if_hybrid_var,
        )

    def set(self, name: str) -> Optional[pd.DataFrame]:
        """Fetch set data.

        Useful for inspecting variables data during model generation and debugging.

        Args:
            name (str): The name of the set.

        Returns:
            Optional[pd.DataFrame]: The data for the specified set.
        """
        return self.core.index.fetch_set_data(set_key=name)

    def __repr__(self):
        """Return a string representation of the Model instance."""
        class_name = type(self).__name__
        return f'{class_name}'

    def _sample_data(
        self,
        method: str,
        groups: bool,
        **kwargs: Any,
    ) -> pd.DataFrame:

        mapping_df, sample_problem = (
            self.core.uncertainty.create_sampling_problem(
                groups=groups
            )
        )

        samples_df = (
            self.core.uncertainty.sample_data(
                method=method,
                problem=sample_problem,
                **kwargs
            )
        )

        self.sampling_problem = sample_problem
        self.uncertainty_samples = samples_df
        self.par_mapping = mapping_df

        return samples_df

    def sampling_settings(
        self,
        method: str,
        groups: bool = False,
        save_samples: bool = True,
        save_measures: bool = True,
        file_format: str = "xlsx",
        **method_kwargs: Any,
    ) -> sampling_settings_config:

        if not self.is_uncertainty_analysis:
            raise ValueError(
                "Uncertainty analysis is not enabled. "
                f"Create the model with "
                f"{Defaults.Labels.UNCERTAINTY_SETTING_KEY}=True."
            )

        if not save_samples and file_format is not None:
            self.logger.warning(
                "Uncertainty analysis | 'file_format' specified but "
                "'save_samples=False'. Samples will not be saved."
            )
        if not save_measures and file_format is not None:
            self.logger.warning(
                "Uncertainty analysis | 'file_format' specified but "
                "'save_measures=False'. Measures will not be saved."
            )

        method = method.lower()

        self.core.uncertainty.validate_sampling_config(
            method=method,
            groups=groups,
            kwargs=method_kwargs)

        self._sampling_settings = sampling_settings_config(
            method=method,
            groups=groups,
            method_kwargs=method_kwargs,
            save_samples=save_samples,
            save_measures=save_measures,
            file_format=file_format,
        )

        # return self._sampling_settings

    def GSA_settings(
        self,
        method: str,
        save_analysis: bool = True,
        measures: list[str] | str | None = None,
        scenarios: list[str] | str | None = None,
        file_format: str = "xlsx",
        **method_kwargs: Any,
    ) -> GSA_settings_config:

        if not self.is_uncertainty_analysis:
            raise ValueError(
                "Uncertainty analysis is not enabled. "
                f"Create the model with "
                f"{Defaults.Labels.UNCERTAINTY_SETTING_KEY}=True."
            )

        if not save_analysis and file_format is not None:
            self.logger.warning(
                "Uncertainty analysis | 'file_format' specified but "
                "'save_samples=False'. Samples will not be saved."
            )

        if isinstance(measures, str):
            measures = [measures]

        if measures is not None and not isinstance(measures, list):
            raise TypeError(
                "'measures' must be a string, a list of strings, or None."
            )

        if isinstance(scenarios, str):
            scenarios = [scenarios]

        if scenarios is not None and not isinstance(scenarios, list):
            raise TypeError(
                "'scenarios' must be a string, a list of strings, or None."
            )

        method = method.lower()

        self.core.uncertainty.validate_analysis_config(
            method=method,
            kwargs=method_kwargs
        )

        self.core.uncertainty.validate_sampling_analysis_compatibility(
            sampling_method=self._sampling_settings.method,
            analysis_method=method
        )

        self._GSA_settings = GSA_settings_config(
            method=method,
            method_kwargs=method_kwargs,
            measures=measures,
            scenarios=scenarios,
            save_analysis=save_analysis,
            file_format=file_format,
        )

    def _validate_uncertainty_run_configuration(self) -> None:
        """Validate that uncertainty analysis can be executed."""

        if not self.is_uncertainty_analysis:
            raise ValueError(
                "Uncertainty analysis is not enabled. "
                f"Create the model with "
                f"{Defaults.Labels.UNCERTAINTY_SETTING_KEY}=True."
            )

        if self._sampling_settings is None:
            raise ValueError(
                "No uncertainty analysis configured. "
                "Call model.sampling_settings(...) before model.run_uncertainty()."
            )

        uncertainty_measures = (
            self.core.uncertainty.get_uncertainty_measure_vars_list()
        )

        if not uncertainty_measures:
            raise exc.SettingsError(
                "Uncertainty analysis configuration invalid | "
                "No uncertainty measures are defined. "
                "At least one endogenous scalar variable must be marked with "
                f"'{Defaults.UncertaintySettings.UNCERTAINTY_MEASURE_KEY}=True'."
            )

    def _generate_uncertainty_samples(
            self,
            uncertainty_cfg: sampling_settings_config,
    ) -> pd.DataFrame:
        """Generate uncertainty samples."""

        self._sample_data(
            method=uncertainty_cfg.method,
            groups=uncertainty_cfg.groups,
            **uncertainty_cfg.method_kwargs,
        )

        samples_df = self.uncertainty_samples

        if samples_df is None or samples_df.empty:
            raise ValueError(
                "Uncertainty analysis failed | "
                "No uncertainty samples were generated."
            )

        return samples_df

    def _sort_variables(
        self,
    ) -> list[str]:

        fully_deterministic_tables = (
            self.core.uncertainty.get_deterministic_tables()
        )

        uncertainty_hybrid_tables = (
            self.core.uncertainty.get_uncertain_tables()
        )

        fully_deterministic_vars = (
            self.core.uncertainty.get_vars_in_tables_list(
                fully_deterministic_tables
            )
        )

        uncertainty_hybrid_vars = (
            self.core.uncertainty.get_vars_in_tables_list(
                uncertainty_hybrid_tables
            )
        )

        return fully_deterministic_vars, uncertainty_hybrid_vars

    def _initialize_problem_structure(
            self,
            force_overwrite: bool = False,
    ) -> None:
        """Load symbolic problem, validate uncertain exogenous data, and initialize CVXPY structures."""

        self.core.load_and_validate_symbolic_problem(
            force_overwrite=force_overwrite,
        )

        self.core.check_exogenous_data_coherence(
            is_uncertain=True,
        )

        self.core.initialize_problems_variables()

    def run_uncertainty(
            self,
            force_overwrite: bool = False,
            integrated_problems: bool = False,
            convergence_monitoring: bool = True,
            solver: Optional[str] = None,
            solver_verbose: bool = False,
            solver_settings: Optional[dict[str, Any]] = None,
            convergence_norm: Defaults.LiteralTypes.NormType = 'l2',
            convergence_tables_to_check: (
                Defaults.LiteralTypes.ConvergenceTables | List[str]
            ) = 'all_endogenous',
            convergence_tables_to_skip: Optional[List[str]] = None,
            relative_tolerance: Optional[float] = None,
            maximum_iterations: Optional[int] = None,
            keep_previous_iteration_db: bool = False,
            **kwargs: Any,
    ) -> None:
        """Run uncertainty analysis over sampled uncertain input values.

        The method samples uncertain parameters, executes one model run per sampled
        input vector, collects scalar uncertainty-measure outputs, and stores the
        resulting dataframe in `self.uncertainty_measures`.

        If one or more scenario-runs are infeasible or unbounded, their uncertainty
        measures are kept as NaN. These NaNs can then be dropped target-by-target
        before GSA analysis.
        """

        run_id_col = Defaults.UncertaintySettings.RUN_ID

        self._validate_uncertainty_run_configuration()

        # 1. Generate uncertainty samples.
        uncertainty_cfg = self._sampling_settings

        samples_df = self._generate_uncertainty_samples(
            uncertainty_cfg=uncertainty_cfg,
        )

        if uncertainty_cfg.save_samples:
            self.core.uncertainty.save_dataframe(
                dataframe=samples_df,
                file_name=Defaults.UncertaintySettings.UNCERTAINTY_SAMPLES_FILE_NAME,
                folder_name=Defaults.UncertaintySettings.RESULTS_DIR,
                file_format=uncertainty_cfg.file_format,
            )

        # 2. Initialize problem structure

        self._initialize_problem_structure(force_overwrite=True)

        deterministic_tables_vars, uncertainty_tables_vars = (
            self._sort_variables(
            )
        )

        # 3. Load deterministic exogenous values only once.
        self.core.data_to_cvxpy_exogenous_vars(
            allow_none_values=False,
            var_list_to_update=deterministic_tables_vars,
        )
        # 5. Run one model instance for each sampled run_id.

        uncertainty_measure_records = []
        failed_runs_report: dict[int, dict] = {}

        for run_id in samples_df[run_id_col]:

            self.core.data_to_cvxpy_exogenous_vars(
                allow_none_values=False,
                var_list_to_update=uncertainty_tables_vars,
                is_hybrid=True,
                samples_df=samples_df,
                run_id=run_id,
            )

            self.core.logger.info(
                f"Running uncertainty-analysis run {run_id}."
            )

            self.core.problem.generate_numerical_problems(force_overwrite=True)

            self.run_model(
                force_overwrite=force_overwrite,
                integrated_problems=integrated_problems,
                convergence_monitoring=convergence_monitoring,
                solver=solver,
                solver_verbose=solver_verbose,
                solver_settings=solver_settings,
                convergence_norm=convergence_norm,
                convergence_tables_to_check=convergence_tables_to_check,
                convergence_tables_to_skip=convergence_tables_to_skip,
                relative_tolerance=relative_tolerance,
                maximum_iterations=maximum_iterations,
                keep_previous_iteration_db=keep_previous_iteration_db,
            )

            statuses_by_scenario = self.core.get_current_problem_status_by_scenario()

            solved_scenarios = [
                scenario_key
                for scenario_key, status in statuses_by_scenario.items()
                if status == "optimal"
            ]

            failed_scenarios = {
                scenario_key: status
                for scenario_key, status in statuses_by_scenario.items()
                if status != "optimal"
            }

            if solved_scenarios:
                solved_records = self.core.uncertainty.collect_uncertainty_measures_for_run(
                    run_id=run_id,
                    scenarios_to_collect=solved_scenarios,
                )
                uncertainty_measure_records.append(solved_records)

            if failed_scenarios:

                failed_records = self.core.uncertainty.create_failed_measure_records_for_run(
                    run_id=run_id,
                    failed_scenarios=failed_scenarios,
                )

                uncertainty_measure_records.append(failed_records)

                failed_runs_report[run_id] = failed_scenarios

        uncertainty_measures_df = pd.concat(
            uncertainty_measure_records,
            ignore_index=True,
        )

        self.uncertainty_measures = uncertainty_measures_df

        if uncertainty_cfg.save_measures:
            self.core.uncertainty.save_dataframe(
                dataframe=uncertainty_measures_df,
                file_name=Defaults.UncertaintySettings.UNCERTAINTY_MEASURES_FILE_NAME,
                folder_name=Defaults.UncertaintySettings.RESULTS_DIR,
                file_format=uncertainty_cfg.file_format,
            )

        # 7. Final warning on failed scenario-runs.
        if failed_runs_report:
            self._warn_failed_model_runs(failed_runs_report)

    def _warn_failed_model_runs(
        self,
        failed_runs_report: dict[int, dict],
    ) -> None:
        """Log a summary warning for infeasible uncertainty-analysis runs."""

        if not failed_runs_report:
            return

        has_scenarios = bool(self.core.index.sets_split_problem_dict)

        if not has_scenarios:
            failed_run_ids = list(failed_runs_report.keys())

            self.logger.warning(
                "Uncertainty analysis | Failde runs detected. "
                f"Failed run_id values: {failed_run_ids}."
            )

            return

        warning_lines = [
            "Uncertainty analysis | Failed scenario-runs detected."
        ]

        for run_id, failed_scenarios in failed_runs_report.items():
            scenario_info = []

            for scenario_key, status in failed_scenarios.items():
                scenario_name = self.core.uncertainty._get_scenario_name(
                    scenario_key
                )

                if scenario_name in [None, ""]:
                    scenario_name = scenario_key

                scenario_info.append(f"{scenario_name}: {status}")

            warning_lines.append(
                f"run_id={run_id} | failed scenarios: "
                + "; ".join(scenario_info)
            )

        self.logger.warning("\n".join(warning_lines))

    def analyze(
        self,
        method: Optional[str] = None,
        **analysis_kwargs: Any,
    ) -> pd.DataFrame:
        """Run GSA analysis on the latest stored uncertainty-analysis run.

        The method uses samples and uncertainty-measure outputs produced by
        `run_uncertainty_analysis()`. The user is therefore not required to pass
        the run results manually.
        """

        if not self.is_uncertainty_analysis:
            raise ValueError(
                "Uncertainty analysis is not enabled. "
                "Create the model with Uncertainty=True."
            )

        if self._GSA_settings is None:
            raise ValueError(
                "No uncertainty analysis configured. "
                "Call model.GSA_settings(...) before analyze_uncertainty()."
            )

        if self.sampling_problem is None:
            raise ValueError(
                "No SALib problem found. "
                "Call model.run_uncertainty_analysis() before analyze_uncertainty()."
            )

        if self.uncertainty_samples is None:
            raise ValueError(
                "No uncertainty samples found. "
                "Call model.run_uncertainty_analysis() before analyze_uncertainty()."
            )

        if self.uncertainty_measures is None:
            raise ValueError(
                "No uncertainty-measure outputs found. "
                "Call model.run_uncertainty_analysis() before analyze_uncertainty()."
            )

        if method is None:
            method = self._sampling_settings.method

        method = method.lower()

        gsa_cfg = self._GSA_settings

        method = gsa_cfg.method

        kwargs = {
            **gsa_cfg.method_kwargs,
            **analysis_kwargs,
        }

        analysis_df = self.core.uncertainty.analyze_results(
            method=method,
            problem=self.sampling_problem,
            samples_df=self.uncertainty_samples,
            mapping_df=self.par_mapping,
            uncertainty_measures_df=self.uncertainty_measures,
            measures=gsa_cfg.measures,
            scenarios=gsa_cfg.scenarios,
            **kwargs,
        )

        if gsa_cfg.save_analysis:
            self.core.uncertainty.save_dataframe(
                dataframe=analysis_df,
                file_name=Defaults.UncertaintySettings.GSA_FILE_NAME,
                folder_name=Defaults.UncertaintySettings.RESULTS_DIR,
                file_format=gsa_cfg.file_format,
            )

        self.gsa_results = analysis_df

    # def model_single_run(
    #     self,
    #     run_id: int,
    #     samples_df: Optional[pd.DataFrame] = None,
    #     force_overwrite: bool = False,
    #     integrated_problems: bool = False,
    #     convergence_monitoring: bool = True,
    #     solver: Optional[str] = None,
    #     solver_verbose: bool = False,
    #     solver_settings: Optional[dict[str, Any]] = None,
    #     convergence_norm: Defaults.LiteralTypes.NormType = "l2",
    #     convergence_tables_to_check: (
    #         Defaults.LiteralTypes.ConvergenceTables | List[str]
    #     ) = "all_endogenous",
    #     convergence_tables_to_skip: Optional[List[str]] = None,
    #     relative_tolerance: Optional[float] = None,
    #     maximum_iterations: Optional[int] = None,
    #     keep_previous_iteration_db: bool = False,
    #     db_name: Optional[str] = None,
    # ) -> Path:

    #     if not self.is_uncertainty_analysis:
    #         raise ValueError(
    #             "Uncertainty analysis is not enabled. "
    #             f"Create the model with "
    #             f"{Defaults.Labels.UNCERTAINTY_SETTING_KEY}=True."
    #         )

    #     if samples_df is None:
    #         samples_df = self.uncertainty_samples

    #     if samples_df is None:
    #         raise ValueError(
    #             "No uncertainty samples found. "
    #             "Pass samples_df explicitly or run the uncertainty sampling first."
    #         )

    #     run_id_col = Defaults.UncertaintySettings.RUN_ID

    #     if run_id_col not in samples_df.columns:
    #         raise ValueError(
    #             f"Samples dataframe must include column '{run_id_col}'."
    #         )

    #     available_run_ids = set(samples_df[run_id_col].tolist())

    #     if run_id not in available_run_ids:
    #         raise ValueError(
    #             f"Invalid run_id '{run_id}'. "
    #             f"Available run_id values: {sorted(available_run_ids)}."
    #         )

    #     self.core.load_and_validate_symbolic_problem(
    #         force_overwrite=force_overwrite,
    #     )

    #     self.core.check_exogenous_data_coherence(is_uncertain=True)

    #     self.core.initialize_problems_variables()

    #     fully_deterministic_tables = (
    #         self.core.uncertainty.get_fully_deterministic_tables_list()
    #     )

    #     uncertainty_hybrid_tables = (
    #         self.core.uncertainty.get_uncertainty_hybrid_tables_list()
    #     )

    #     fully_deterministic_vars = self.core.uncertainty.get_vars_in_tables_list(
    #         fully_deterministic_tables
    #     )

    #     uncertainty_hybrid_vars = self.core.uncertainty.get_vars_in_tables_list(
    #         uncertainty_hybrid_tables
    #     )

    #     self.core.data_to_cvxpy_exogenous_vars(
    #         allow_none_values=False,
    #         var_list_to_update=fully_deterministic_vars,
    #     )

    #     self.core.data_to_cvxpy_exogenous_vars(
    #         allow_none_values=False,
    #         var_list_to_update=uncertainty_hybrid_vars,
    #         is_hybrid=True,
    #         samples_df=samples_df,
    #         run_id=run_id,
    #     )

    #     self.core.logger.info(
    #         f"Running model for uncertainty-analysis run {run_id}."
    #     )

    #     self.core.problem.generate_numerical_problems(force_overwrite=True)

    #     self.run_model(
    #         force_overwrite=force_overwrite,
    #         integrated_problems=integrated_problems,
    #         convergence_monitoring=convergence_monitoring,
    #         solver=solver,
    #         solver_verbose=solver_verbose,
    #         solver_settings=solver_settings,
    #         convergence_norm=convergence_norm,
    #         convergence_tables_to_check=convergence_tables_to_check,
    #         convergence_tables_to_skip=convergence_tables_to_skip,
    #         relative_tolerance=relative_tolerance,
    #         maximum_iterations=maximum_iterations,
    #         keep_previous_iteration_db=keep_previous_iteration_db,
    #     )

    #     self.load_results_to_database(
    #         force_overwrite=True,
    #         suppress_warnings=True,
    #     )

    #     if db_name is None:
    #         db_name = f"database_id{run_id}.db"

    #     if not db_name.endswith(".db"):
    #         db_name = f"{db_name}.db"

    #     source_db_path = self.paths["sqlite_database"]
    #     destination_db_path = self.paths["model_dir"] / db_name

    #     if destination_db_path.exists() and not force_overwrite:
    #         raise FileExistsError(
    #             f"Database file '{destination_db_path.name}' already exists. "
    #             "Set force_overwrite=True to overwrite it."
    #         )

    #     shutil.copy2(source_db_path, destination_db_path)

    #     self.logger.info(
    #         f"Run-specific database saved as '{destination_db_path.name}'."
    #     )

    #     return destination_db_path
