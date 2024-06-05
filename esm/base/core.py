"""
core.py

@author: Matteo V. Rocco
@institution: Politecnico di Milano

This module embeds the generation of main classes of the package, allowing to 
operate across them. 
It facilitates interactions among data tables, databases, problems, and 
logging mechanisms, enabling comprehensive management and operations within 
the modeling environment.
"""

import os
from typing import Any, Dict, Optional
from pathlib import Path

from esm.base.data_table import DataTable
from esm.base.database import Database
from esm.base.index import Index, Variable
from esm.base.problem import Problem
from esm.log_exc import exceptions as exc
from esm.log_exc.logger import Logger
from esm.constants import Constants
from esm.support import util
from esm.support.file_manager import FileManager
from esm.support.sql_manager import SQLManager, db_handler


class Core:
    """
    Core class defines the interactions among various components of the package, 
    such as data tables, databases, and problem-solving mechanisms. It serves 
    as the central management point for initializing, processing, and 
    executing model operations.

    Attributes:
        logger (Logger): Logger object for logging information.
        files (FileManager): FileManager object for file operations.
        settings (Dict[str, str]): Settings for various file paths and configurations.
        paths (Dict[str, Path]): Paths to various directories and files used in the model.
        sqltools (SQLManager): SQLManager object for database interactions.
        index (Index): Index object for managing data table and variable indices.
        database (Database): Database object for database operations.
        problem (Problem): Problem object for problem definitions and operations.

    Args:
        logger (Logger): Logger object for logging information.
        files (FileManager): FileManager object for file operations.
        settings (Dict[str, str]): Settings dictionary containing configuration details.
        paths (Dict[str, Path]): Paths dictionary containing paths used in the model.
    """

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            settings: Dict[str, str],
            paths: Dict[str, Path],
    ) -> None:

        self.logger = logger.get_child(__name__)
        self.logger.debug(f"'{self}' object initialization...")

        self.files = files
        self.settings = settings
        self.paths = paths

        self.sqltools = SQLManager(
            logger=self.logger,
            database_path=self.paths['sqlite_database'],
            database_name=self.settings['sqlite_database_file'],
        )

        self.index = Index(
            logger=self.logger,
            files=self.files,
            paths=self.paths,
        )

        self.database = Database(
            logger=self.logger,
            files=self.files,
            paths=self.paths,
            sqltools=self.sqltools,
            settings=self.settings,
            index=self.index,
        )

        self.problem = Problem(
            logger=self.logger,
            files=self.files,
            paths=self.paths,
            settings=self.settings,
            index=self.index
        )

        self.logger.debug(f"'{self}' initialized.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def initialize_problems_variables(self) -> None:
        """
        Initializes and generates data structures for handling problem variables. 
        This includes generating DataFrame variables structures with related 
        variables coordinates, data filters, cvxpy objects.

        Returns:
            None
        """
        self.logger.debug(
            "Generating data structures for endogenous data tables "
            "(cvxpy objects, filters dict for data tables).")

        # generate dataframes and cvxpy var for endogenous data tables
        # and for variables whth type defined by problem linking logic
        for data_table_key, data_table in self.index.data.items():

            if data_table.type == 'endogenous' or \
                    isinstance(data_table.type, dict):

                self.logger.debug(
                    "Generating variable dataframe and cvxpy variable "
                    f"for endogenous data table '{data_table_key}'.")

                data_table.generate_coordinates_dataframe()
                data_table.cvxpy_var = self.problem.create_cvxpy_variable(
                    var_type='endogenous',
                    shape=(data_table.table_length, 1),
                    name=data_table_key,
                )

        # generating variables dataframes with cvxpy var and filters dictionary
        # (endogenous vars will be sliced from existing cvxpy var in data table)
        self.logger.debug(
            "Generating data structures for all variables and constants.")

        for var_key, variable in self.index.variables.items():

            # for constants, values are directly generated (no dataframes needed)
            if variable.type == 'constant':
                variable.data = self.problem.generate_constant_data(
                    variable_name=var_key,
                    variable=variable
                )

            # for variable whose type is univocally defined, only one dataframe
            # is generated and stored in variable.data
            elif variable.type in ['exogenous', 'endogenous']:
                variable.data = self.problem.generate_vars_dataframe(
                    variable_name=var_key,
                    variable=variable
                )

            # for variable whose type varies depending on the problem, both
            # endogenous/exogenous variable dataframes are stored in
            # variable.data defined as a dictionary
            elif isinstance(variable.type, dict):
                variable.data = {}

                for problem_key, problem_var_type in variable.type.items():
                    variable.data[problem_key] = self.problem.generate_vars_dataframe(
                        variable_name=var_key,
                        variable=variable,
                        variable_type=problem_var_type,
                    )

            else:
                setup_file = Constants.get('_SETUP_FILES')[1]
                msg = f"Variable type '{variable.type}' not allowed. Check " \
                    "definition of variable types in the model configuration " \
                    f"file '{setup_file}'."
                self.logger.error(msg)
                raise exc.SettingsError(msg)

    def define_mathematical_problems(
            self,
            force_overwrite: bool = False,
    ) -> None:
        """
        Defines and initializes numerical problems based on the loaded symbolic 
        definitions. This can optionally overwrite existing problem definitions.

        Args:
            force_overwrite (bool): If True, forces the redefinition of problems 
                even if they already exist. Default to False.

        Returns:
            None
        """
        self.logger.debug(
            "Load symbolic problem, initialize dataframes with cvxpy problem.")

        self.problem.load_symbolic_problem_from_file(force_overwrite)
        self.problem.generate_numerical_problems(force_overwrite)

    def solve_numerical_problems(
            self,
            solver: str,
            verbose: bool,
            integrated_problems: bool,
            force_overwrite: bool,
            maximum_iterations: Optional[int] = None,
            numerical_tolerance: Optional[float] = None,
            **kwargs: Any,
    ) -> None:
        """
        Solves all defined numerical problems using the specified solver and 
        verbosity settings.

        Args:
            solver (str): The solver to use for solving the problems.
            verbose (bool): If True, enables verbose output during problem solving.
            **kwargs: Additional keyword arguments to pass to the solver.

        Returns:
            None
        """
        if self.problem.numerical_problems is None:
            msg = "Numerical problems must be defined first."
            self.logger.warning(msg)
            raise exc.OperationalError(msg)

        if self.problem.status == 'optimal':
            if not force_overwrite:
                self.logger.warning("Numeric problems already solved.")
                user_input = input("Solve again numeric problems? (y/[n]): ")

                if user_input.lower() != 'y':
                    self.logger.info(
                        "Numeric problem NOT solved.")
                    return

            self.logger.info(
                "Solving numeric problem and overwriting existing "
                "variables numerical values.")

        if not integrated_problems:
            self.problem.solve_problems(
                solver=solver,
                verbose=verbose,
                **kwargs
            )
        else:
            self.solve_integrated_problems(
                solver=solver,
                verbose=verbose,
                numerical_tolerance=numerical_tolerance,
                maximum_iterations=maximum_iterations,
                **kwargs,
            )

        self.problem.fetch_problem_status()

    def data_to_cvxpy_exogenous_vars(self) -> None:
        """
        Fetches data from the SQLite database and assigns it to cvxpy 
        exogenous variables only.

        Returns:
            None
        """
        self.logger.debug(
            f"Fetching data from '{self.settings['sqlite_database_file']}' "
            "to cvxpy exogenous variables.")

        with db_handler(self.sqltools):
            for var_key, variable in self.index.variables.items():

                if not isinstance(variable, Variable):
                    msg = "Passed item is not a 'Variable' class instance."
                    self.logger.error(msg)
                    raise TypeError(msg)

                if variable.type in ['endogenous', 'constant']:
                    continue

                self.logger.debug(
                    f"Fetching data from table '{var_key}' "
                    "to cvxpy exogenous variable.")

                filter_header = Constants.get('_FILTER_DICT_HEADER')
                cvxpy_var_header = Constants.get('_CVXPY_VAR_HEADER')
                values_header = Constants.get('_STD_VALUES_FIELD')['values'][0]
                id_header = Constants.get('_STD_ID_FIELD')['id'][0]
                allowed_values_types = Constants.get('_ALLOWED_VALUES_TYPES')

                err_msg = []

                if variable.data is None:
                    err_msg.append(
                        f"No data defined for variable '{var_key}'.")

                if variable.related_table is None:
                    err_msg.append(
                        f"No related table defined for variable '{var_key}'.")

                if err_msg:
                    self.logger.error("\n".join(err_msg))
                    raise exc.MissingDataError("\n".join(err_msg))

                # for variables whose type is defined by the problem,
                # fetch exogenous variable data.
                if isinstance(variable.data, dict):
                    problem_key = util.find_dict_key_corresponding_to_value(
                        variable.type, 'exogenous')
                    variable_data = variable.data[problem_key]
                else:
                    variable_data = variable.data

                for row in variable_data.index:
                    # get raw data from database
                    raw_data = self.database.sqltools.filtered_table_to_dataframe(
                        table_name=variable.related_table,
                        filters_dict=variable_data[filter_header][row])

                    # check if variable data are int or float
                    non_numeric_ids = util.find_non_allowed_types(
                        dataframe=raw_data,
                        allowed_types=allowed_values_types,
                        target_col_header=values_header,
                        return_col_header=id_header,
                    )

                    if non_numeric_ids:
                        msg = f"Data for variable '{var_key}' in table " \
                            f"'{variable.related_table}' contains " \
                            f"non-allowed values types in rows: " \
                            f"{non_numeric_ids}."
                        self.logger.error(msg)
                        raise exc.MissingDataError(msg)

                    # pivoting and reshaping data to fit variables
                    pivoted_data = variable.reshaping_sqlite_table_data(
                        data=raw_data
                    )

                    self.problem.data_to_cvxpy_variable(
                        cvxpy_var=variable_data[cvxpy_var_header][row],
                        data=pivoted_data
                    )

    def cvxpy_endogenous_data_to_database(self, operation: str) -> None:
        """
        Exports data from cvxpy endogenous variables back to data tables into 
        the SQLite database.

        Args:
            operation (str): Specifies the type of database operation to 
                perform (e.g., 'update', 'insert').
        """
        self.logger.debug(
            "Exporting data from cvxpy endogenous variable (in data table) "
            f"to SQLite database '{self.settings['sqlite_database_file']}' ")

        with db_handler(self.sqltools):
            for data_table_key, data_table in self.index.data.items():

                if not isinstance(data_table, DataTable):
                    msg = "Passed item is not a 'DataTable' class instance."
                    self.logger.error(msg)
                    raise TypeError(msg)

                if data_table.type in ['exogenous', 'constant']:
                    continue

                self.logger.debug(
                    "Exporting data from cvxpy variable to the related "
                    f"data table '{data_table_key}'. ")

                values_headers = Constants.get(
                    '_STD_VALUES_FIELD')['values'][0]

                if data_table.coordinates_dataframe is not None:
                    data_table_dataframe = data_table.coordinates_dataframe
                    if not util.add_column_to_dataframe(
                        dataframe=data_table_dataframe,
                        column_header=values_headers,
                    ):
                        self.logger.warning(
                            f"Column '{values_headers}' already exists in data "
                            f"table '{data_table_key}'")
                else:
                    msg = "Coordinates dataframe not defined for data " \
                        f"table '{data_table_key}'. "
                    self.logger.error(msg)
                    raise exc.OperationalError(msg)

                if data_table.cvxpy_var is not None:
                    cvxpy_var_data = data_table.cvxpy_var.value
                else:
                    cvxpy_var_data = None

                if cvxpy_var_data is None or len(cvxpy_var_data) == 0:
                    self.logger.warning(
                        f"No data available in cvxpy variable '{data_table_key}'")
                    continue

                data_table_dataframe[values_headers] = cvxpy_var_data

                self.sqltools.dataframe_to_table(
                    table_name=data_table_key,
                    dataframe=data_table_dataframe,
                    operation=operation,
                )

    def check_results_as_expected(
            self,
            values_relative_diff_tolerance: float,
    ) -> None:
        """
        Checks if the results of the current database match the expected results.
        This method uses the 'check_databases_equality' method to compare the 
        current database with a test database. The test database is specified 
        by the 'sqlite_database_file_test' setting and is located in the model 
        directory.

        Args:
            values_relative_diff_tolerance (float): The relative difference 
                tolerance (%) to use when comparing the databases. 

        Raises:
            OperationalError: If the connection or cursor of the database to be 
                checked are not initialized.
            ModelFolderError: If the test database does not exist or is not 
                correctly named.
            ResultsError: If the databases are not identical in terms of table 
                presence, structure, or contents.
        """
        with db_handler(self.sqltools):
            self.sqltools.check_databases_equality(
                other_db_dir_path=self.paths['model_dir'],
                other_db_name=self.settings['sqlite_database_file_test'],
                tolerance_percentage=values_relative_diff_tolerance,
            )

    def solve_integrated_problems(
            self,
            solver: str,
            verbose: bool,
            numerical_tolerance: Optional[float] = None,
            maximum_iterations: Optional[int] = None,
            **kwargs: Any,
    ) -> None:
        """
        """
        if maximum_iterations is None:
            maximum_iterations = Constants.get(
                '_MAXIMUM_ITERATIONS_MODEL_COUPLING')

        if numerical_tolerance is None:
            numerical_tolerance = Constants.get(
                '_TOLERANCE_MODEL_COUPLING_CONVERGENCE')

        sqlite_db_path = self.paths['model_dir']
        sqlite_db_file_name = self.settings['sqlite_database_file']

        base_name, extension = os.path.splitext(sqlite_db_file_name)
        sqlite_db_file_name_previous = f"{base_name}_previous_iter{extension}"

        iter_count = 0

        tables_to_check = [
            table_key for table_key in self.index.data.keys()
            if self.index.data[table_key].type not in ['exogenous', 'constant']
        ]

        while True:

            iter_count += 1
            if iter_count > maximum_iterations:
                self.logger.warning(
                    f"Maximum number of iterations reached before reaching "
                    "convergence to numerical_tolerance.")
                break

            self.logger.info(f"=====================")
            self.logger.info(f"Iteration number '{iter_count}'")

            if iter_count > 1:
                self.data_to_cvxpy_exogenous_vars()

            self.files.copy_file_to_destination(
                path_destination=sqlite_db_path,
                path_source=sqlite_db_path,
                file_name=sqlite_db_file_name,
                file_new_name=sqlite_db_file_name_previous,
                force_overwrite=True,
            )

            self.problem.solve_problems(
                solver=solver,
                verbose=verbose,
                **kwargs
            )

            self.cvxpy_endogenous_data_to_database(operation='update')

            with db_handler(self.sqltools):
                relative_difference = \
                    self.sqltools.get_tables_values_relative_difference(
                        other_db_dir_path=sqlite_db_path,
                        other_db_name=sqlite_db_file_name_previous,
                        tables_names=tables_to_check,
                    )

            self.logger.info(
                "Maximum relative differences in tables values: "
                f"'{relative_difference}'")

            if all(
                value <= numerical_tolerance
                for value in relative_difference.values()
            ):
                self.logger.info("Numerical convergence reached.")
                self.files.erase_file(
                    dir_path=sqlite_db_path,
                    file_name=sqlite_db_file_name_previous,
                    force_erase=True,
                    confirm=False,
                )
                break
