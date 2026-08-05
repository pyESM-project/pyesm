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
from cvxlab.backend.model_settings import ModelSettings, ModelPaths
from cvxlab.backend.run_settings import RunSettings
from cvxlab.log_exc import exceptions as exc
from cvxlab.log_exc.logger import Logger
from cvxlab.support.file_manager import FileManager
from cvxlab.backward_compat import BackwardCompat


class Model:
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
    - settings (ModelSettings): Validated container storing model configurations such as \
        model name, settings source, and operational flags.
    - paths (ModelPaths): Validated container storing the paths for model \
        directories and associated files.
    - core (Core): An instance of Core that manages the core functionality of the \
        model (it embeds Index, Database and Problem instances).

    """

    def __init__(
            self,
            model_dir_name: str = 'model',
            main_dir_path: Optional[str] = None,
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
        if main_dir_path is None:
            main_dir_path = str(Path.cwd())

        model_dir_path = Path(main_dir_path) / model_dir_name

        self.logger = Logger(
            logger_name=str(self),
            log_level=log_level.upper(),
            log_format=log_format,
        )

        with self.logger.log_timing(
            message="Model instance generation...",
            level='info',
        ):
            self.files = FileManager(logger=self.logger)

            self.settings = ModelSettings(
                logger=self.logger,
                log_level=log_level,
                model_name=model_dir_name,
                model_settings_from=model_settings_from,
                use_existing_data=use_existing_data,
                multiple_input_files=multiple_input_files,
                input_data_files_type=input_data_files_type,
                detailed_validation=detailed_validation,
            )

            self.paths = ModelPaths(
                logger=self.logger,
                model_dir_path=model_dir_path,
                model_settings_from=model_settings_from,
                use_existing_data=use_existing_data,
            )
            self._import_custom_scripts()

            self.core = Core(
                logger=self.logger,
                files=self.files,
                settings=self.settings,
                paths=self.paths,
            )

            if self.settings.use_existing_data:
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
    def scenarios(self) -> Optional[pd.DataFrame]:
        """DataFrame of scenarios available in the model.

        Each row represents a scenario, identified by a unique combination of
        inter-problem set values. The DataFrame index is used as the scenario
        index in methods that accept a ``scenario_idx`` parameter (e.g.
        :meth:`run_model`, :meth:`load_results_to_database`).

        Returns:
            Optional[pd.DataFrame]: A DataFrame with one row per scenario and
                one column per inter-problem set, or None if no inter-problem
                sets are defined.
        """
        return self.core.index.scenarios_info

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

    def _setting_table_keys(
            self,
            table_key_list: Optional[List[str]],
            valid_table_keys: List[str],
    ) -> List[str]:
        """Resolve and validate table keys received by the public API.

        Args:
            table_key_list (Optional[List[str]]): Table keys requested by the
                user. If None or empty, all valid table keys are selected.
            valid_table_keys (List[str]): Table keys allowed by the calling
                method.

        Returns:
            List[str]: A copy of the resolved and validated table keys.

        Raises:
            TypeError: If table_key_list is not a list or contains non-string
                items.
            exc.SettingsError: If table_key_list contains invalid table keys.
        """
        if table_key_list is None or table_key_list == []:
            return list(valid_table_keys)

        if not isinstance(table_key_list, list):
            msg = "'table_key_list' must be a list of strings or None."
            self.logger.error(msg)
            raise TypeError(msg)

        invalid_type_items = [
            item for item in table_key_list
            if not isinstance(item, str)
        ]
        if invalid_type_items:
            msg = (
                "'table_key_list' must contain only strings. "
                f"Invalid item(s): {invalid_type_items!r}."
            )
            self.logger.error(msg)
            raise TypeError(msg)

        invalid_keys = [
            key for key in table_key_list
            if key not in valid_table_keys
        ]
        if invalid_keys:
            msg = f"Invalid table key(s): {invalid_keys!r}."
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        return list(table_key_list)

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
                dir_path=self.paths.model_dir,
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
        self.core.index._coordinates_loaded = False

        with self.logger.log_timing(
            message="Loading sets and variables coordinates...",
            level='info',
        ):
            try:
                sets_xlsx_file = Defaults.ConfigFiles.SETS_FILE
                self.core.index.load_sets_data_to_index(
                    excel_file_name=sets_xlsx_file,
                    excel_file_dir_path=self.paths.model_dir
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

        self.core.index._coordinates_loaded = True

    def _initialize_blank_data_structure(self) -> None:
        """Initialize blank data structure for the model.

        This method generates the fundamental blank data structure for the model.
        If the SQLite database already exists, it gives the option to erase it
        and generate a new one, or to work with the existing SQLite database.
        Same for the input data directory.
        Specifically, the method creates:

        - A blank SQLite database with set tables and data tables, filling data
            tables with sets information.
        - A blank Excel/CSV input data file/s with normalized data tables for getting
            exogenous variables data from the user.

        """
        use_existing_data = self.settings.use_existing_data
        sqlite_db_name = Defaults.ConfigFiles.SQLITE_DATABASE_FILE
        sqlite_db_path = Path(self.paths.sqlite_database)
        input_files_dir_path = Path(self.paths.input_data_dir)

        erased_db = False
        erased_input_dir = False

        if use_existing_data:
            self.logger.info(
                "Relying on existing SQLite database and input excel file/s.")
            return

        with self.logger.log_timing(
            message="Generation of blank data structures...",
            level='info',
        ):
            if sqlite_db_path.exists():
                erased_db = self.files.erase_file(
                    dir_path=self.paths.model_dir,
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
                self.core.database.generate_blank_data_input_files(
                    table_key_list=self.core.index.list_exogenous_data_tables,
                )
            else:
                self.logger.info("Relying on existing input data directory.")

    def _load_exogenous_data_to_sqlite_database(
            self,
            table_key_list: List[str],
            force_overwrite: bool = False,
    ) -> None:
        """Load exogenous (input) data to the SQLite database.

        This method loads exogenous (input) data from Excel file/s to the
        SQLite database. It also fills NaN values in the database with Null
        values, to ensure proper handling of missing data in SQLite.
        It is an internal workflow called by public Model methods after the
        user's table selection has been resolved and validated.

        Args:
            table_key_list (List[str]): Validated list of exogenous data table
                keys for which input data will be loaded.
            force_overwrite (bool, optional): Whether to force overwrite existing
                data without asking for user permission. Defaults to False.
        """
        with self.logger.log_timing(
            message="Loading input data to SQLite database...",
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
            message="Numerical model generation...",
            level='info',
        ):
            self.core.load_and_validate_symbolic_problem(force_overwrite)
            self.core.check_exogenous_data_coherence()
            self.core.generate_numerical_problem(
                force_overwrite=force_overwrite,
                allow_none_values=allow_none_values
            )

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
        if self.settings.use_existing_data:
            self.logger.info(
                "Relying on existing model environment (sets coordinates, "
                "SQLite database, input data files)."
            )
            return

        self._load_model_coordinates()
        self._initialize_blank_data_structure()

    def refresh_database_and_initialize_problem(
            self,
            force_overwrite: bool = False,
            table_key_list: Optional[list[str]] = None,
    ) -> None:
        """Update SQLite database with exogenous data and initialize problems.

        This method loads the SQLite database exogenous data, and then initializes
        numerical problems.
        This method can be used for both initialization of the model environment,
        after having generated the Model instance, and for updating the model
        environment and the problems in case some changes in input data have been
        made, without the need of re-generating the Model instance.

        Args:
            force_overwrite (bool, optional): Whether to overwrite/update
                existing data without asking user permission. Defaults to False.
            table_key_list (Optional[list[str]], optional): A list of data table keys
                for which to load exogenous data. If None or empty, all
                exogenous data tables are loaded. Defaults to None.
        """
        sqlite_db_file = Defaults.ConfigFiles.SQLITE_DATABASE_FILE

        self.logger.info(
            f"Loading exogenous data into SQLite database '{sqlite_db_file}' "
            "and initializing problems.")

        if not self.core.index._coordinates_loaded:
            msg = "Model coordinates have not been loaded. Call " \
                "'initialize_model_environment()' before " \
                "'refresh_database_and_initialize_problem()'."
            self.logger.error(msg)
            raise exc.MissingDataError(msg)

        table_key_list = self._setting_table_keys(
            table_key_list=table_key_list,
            valid_table_keys=self.core.index.list_exogenous_data_tables,
        )

        self._load_exogenous_data_to_sqlite_database(
            table_key_list=table_key_list,
            force_overwrite=force_overwrite,
        )

        self._initialize_problems(force_overwrite)

    def run_model(
        self,
        force_overwrite: bool = False,
        solution_mode: Defaults.LiteralTypes.SolutionMode = 'parallel',
        scenarios_idx: Optional[List[int] | int] = None,
        # arguments for solver settings
        solver: Optional[str | dict[str, str]] = None,
        solver_verbose: bool | dict[str, bool] = False,
        solver_settings: Optional[
            dict[str, Any] |
            dict[str, dict[str, Any]]
        ] = None,
        # arguments for sequential solution mode
        sequential_solution_chain: Optional[List[str | int]] = None,
        # arguments for integrated solution mode
        convergence_monitoring: bool = True,
        convergence_norm: Defaults.LiteralTypes.NormType = 'l2',
        convergence_tables_to_check:
            Defaults.LiteralTypes.ConvergenceTables |
            List[str] = 'all_endogenous',
        convergence_tables_to_skip: Optional[List[str]] = None,
        relative_tolerance: Optional[float] = None,
        maximum_iterations: Optional[int] = None,
        keep_previous_iteration_db: bool = False,
        **kwargs: Any,
    ) -> None:
        """Solve numerical problems defined by the model instance.

        Central method to solve numerical problems. First, it performs coherence
        checks and define a dictionary with solution strategy information. Then,
        it solves the numerical problems accordingly. Finally, it logs a summary
        of the problems/sceanarios solution status.

        Args:
            force_overwrite (bool, optional): If True, overwrites existing results.
                Defaults to False.
            solution_mode (Defaults.LiteralTypes.SolutionMode, optional): The solution
                mode to use. Defaults to 'parallel'.
            scenarios_idx (Optional[List[int] | int], optional): An optional list
                of indices specifying which scenarios to solve. Indices must
                correspond to the index of the :attr:`scenarios` DataFrame
                (inspect it to identify valid values). If None, all scenarios
                are solved. If an integer is provided, it will be treated as a
                single scenario index. Defaults to None.
            solver (str | dict[str, str], optional): The solver to use for
                solving numerical problems. When multiple sub-problems are
                available, a dictionary keyed by problem key can be used to
                define one solver per sub-problem. Defaults to None, in which
                case the default solver specified in
                'Defaults.NumericalSettings.CVXPY_DEFAULT_SETTINGS' is used.
            solver_verbose (bool | dict[str, bool], optional): If True, logs
                verbose output related to numerical solver operation during the
                model run. When multiple sub-problems are available, a
                dictionary keyed by problem key can be used to define verbosity
                per sub-problem. Defaults to False.
            solver_settings (dict[str, Any] | dict[str, dict[str, Any]], optional):
                Additional solver settings. When multiple sub-problems are
                available, a dictionary keyed by problem key can be used to
                define dedicated settings per sub-problem. Defaults to None.
            sequential_solution_chain (Optional[List[str | int]], optional): An
                optional list of problem keys specifying the order in which to 
                solve the problems. If None, problems are solved in the order as 
                specified by model settings files. Defaults to None.
            convergence_monitoring (bool, optional): If True, enables convergence
                monitoring during the solving of integrated problems. Defaults to True.
            convergence_norm (Defaults.LiteralTypes.NormType, optional):
                The norm type to use for convergence monitoring in integrated
                problems. Defaults to 'l2' (Euclidean Norm).
            convergence_tables_to_check (Defaults.LiteralTypes.ConvergenceTables |
                List[str], optional): The data tables to consider for convergence
                monitoring in integrated problems. Can be 'all_endogenous',
                'hybrid_only', or a list of specific data table keys. Defaults
                to 'all_endogenous'.
            convergence_tables_to_skip (Optional[List[str]], optional): List of
                data table keys to skip for convergence checking in integrated
                problems. If None, no tables are skipped. Defaults to None.
            relative_tolerance (float, optional): Numerical tolerance for verifying
                maximum relative change between iterations in integrated problems for
                each data table. Overrides 'Defaults.NumericalSettings.MODEL_COUPLING_SETTINGS'.
            maximum_iterations (int, optional): The maximum number of iterations
                for solving integrated problems. Overrides
                'Defaults.NumericalSettings.MODEL_COUPLING_SETTINGS'.
            keep_previous_iteration_db (bool, optional): Whether keep or not the
                database generated during the last-1 iteration. For debugging purpose.
                Default to False.
            **kwargs: Additional keyword arguments for backward compatibility.
        """
        if not self.core.index._coordinates_loaded:
            msg = "Model coordinates have not been loaded. Call " \
                "'initialize_model_environment()' before 'run_model()'."
            self.logger.error(msg)
            raise exc.MissingDataError(msg)

        # Normalize deprecated arguments (keeps Model.run_model body clean)
        solution_mode = BackwardCompat.run_model_params(
            solution_mode=solution_mode, kwargs=kwargs, logger=self.logger
        )

        run_settings: RunSettings = RunSettings(
            # context primitives from the model's Problem and Index
            problems_keys=self.core.problem.problems_keys,
            number_of_sub_problems=self.core.problem.number_of_sub_problems,
            all_scenarios_idx=list(self.core.index.scenarios_info.index),
            # user-provided arguments
            solution_mode=solution_mode,
            scenarios_idx=scenarios_idx,
            solver=solver,
            solver_verbose=solver_verbose,
            solver_settings=solver_settings,
            # arguments for sequential solution mode
            sequential_solution_chain=sequential_solution_chain,
            # arguments for integrated solution mode
            convergence_monitoring=convergence_monitoring,
            convergence_norm=convergence_norm,
            convergence_tables_to_check=convergence_tables_to_check,
            convergence_tables_to_skip=convergence_tables_to_skip,
            relative_tolerance=relative_tolerance,
            maximum_iterations=maximum_iterations,
            keep_previous_iteration_db=keep_previous_iteration_db,
            logger=self.logger,
        )

        msg = f"Model run | Solution mode: '{run_settings.solution_mode}' "

        if self.core.problem.problems_keys:
            msg += f"| Problems count: {len(self.core.problem.problems_keys)}"

        if self.core.index.scenarios_info.index is not None:
            msg += f"| Scenarios count: {len(self.core.index.scenarios_info.index)}"

        self.logger.info(msg)

        with self.logger.log_timing(
            message="Solving numerical problems...",
            level='info',
        ):
            self.core.solve_numerical_problems(
                force_overwrite=force_overwrite,
                run_settings=run_settings,
            )

        # deve essere rivisto in base al solution mode:
        # se è parallel o sequential, va bene il problem status (e per ogni scenario)
        # se è integrated, i problemi hanno girato più volte, ha senso solo per ogni scenario
        # msg = "Numerical problems status report:"
        # self.logger.info("="*len(msg))
        # self.logger.info(msg)

        # for info, status in self.core.problem.problem_status.items():
        #     self.logger.info(
        #         f"{info}: {status}" if info else f"{status}"
        #     )

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
                results. Indices must correspond to the index of the
                :attr:`scenarios` DataFrame (inspect it to identify valid
                values). If None, results for all scenarios are exported.
                Defaults to None.
            force_overwrite (bool, optional): Whether to overwrite/update
                existing data without asking user permission. Defaults to False.
            suppress_warnings (bool, optional): Whether to suppress warnings
                during the data loading process. Defaults to False.
        """
        with self.logger.log_timing(
            message="Exporting endogenous model results to SQLite database...",
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
            table_key_list: Optional[List[str]] = None,
            values_cleanup: bool = True,
            force_overwrite: bool = False,
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
            table_key_list (Optional[List[str]], optional): A list of data table keys
                for which to generate input data files. If None or empty, all
                exogenous data tables are generated. Defaults to None.
            values_cleanup (bool, optional): Whether to clean up values of
                database tables before generating input data files. Defaults
                to True.
            force_overwrite (bool, optional): Whether to overwrite existing
                input data files or sheets without asking for confirmation.
                Defaults to False.

        Raises:
            exc.SettingsError: If the input data directory is missing.
            exc.SettingsError: If any of the specified table keys are invalid
                (i.e., not exogenous data tables).
        """
        input_files_dir_path = Path(self.paths.input_data_dir)

        if not input_files_dir_path.exists():
            msg = "Input data directory missing. Initialize blank data structure first."
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        select_all_tables = table_key_list is None or table_key_list == []
        table_key_list = self._setting_table_keys(
            table_key_list=table_key_list,
            valid_table_keys=self.core.index.list_exogenous_data_tables,
        )

        if select_all_tables:
            msg = "Generating all input data files..."
        else:
            msg = f"Generating input data files for tables: '{table_key_list}'..."

        with self.logger.log_timing(
            message=msg,
            level='info',
        ):
            self.core.database.generate_blank_data_input_files(
                table_key_list=table_key_list,
                values_cleanup=values_cleanup,
                force_overwrite=force_overwrite,
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
        self._load_exogenous_data_to_sqlite_database(
            table_key_list=self.core.index.list_exogenous_data_tables,
            force_overwrite=force_overwrite,
        )

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
            msg = (
                "Both 'other_db_dir_path' and 'other_db_name' parameters must "
                "be defined together, or both must be None."
            )
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        if other_db_dir_path is None:
            other_db_dir_path = self.paths.model_dir

        if other_db_name is None:
            other_db_name = Defaults.ConfigFiles.SQLITE_DATABASE_FILE_TEST

        if not numerical_tolerance:
            numerical_tolerance = Defaults.NumericalSettings.TOLERANCE_TESTS_RESULTS_CHECK

        with self.logger.log_timing(
            message="Check model results...",
            level='info',
        ):
            self.core.database.compare_databases(
                values_relative_diff_tolerance=numerical_tolerance,
                other_db_dir_path=other_db_dir_path,
                other_db_name=other_db_name,
            )

    def update_sets_tables(
            self,
            set_keys_list: Optional[List[str]] = None,
            update_mode: Defaults.LiteralTypes.SetUpdateMode = 'all',
    ) -> None:
        """Update sets tables in the SQLite database.

        This method updates sets tables in the SQLite database. The user can choose
        to update all sets, or only specific sets (with the 'set_keys_list' attribute).
        Additionally, the user can specify the update mode, which can be 'all',
        'filters', or 'aggregations'.

        Args:
            set_keys_list (Optional[List[str]], optional): A list of set keys to update.
                If empty, all sets are updated. Defaults to None.
            update_mode (Defaults.LiteralTypes.SetUpdateMode, optional):
                The update mode. Can be 'all' (update all set data), 'filters'
                (update only filters), or 'aggregations' (update only aggregations).
                Defaults to 'all'.
        """
        if set_keys_list is None:
            set_keys_list = []

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

    def show_model_summary(self) -> None:
        """Print a summary of the model structure and solution state."""
        print(f"Sets: {self.sets}")
        print(f"Data tables: {self.data_tables}")
        print(f"Variables: {self.variables}")
        print(f"Scenarios:\n{self.scenarios}")
        print(f"Problem solved: {self.is_problem_solved}")

    def __repr__(self):
        """Return a string representation of the Model instance."""
        class_name = type(self).__name__
        return f'{class_name}'
