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

from typing import Any, Dict
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

        self.logger = logger.getChild(__name__)
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

        # generate dataframes and cvxpy var for whole endogenous data tables
        for data_table_key, data_table in self.index.data.items():

            if data_table.type == 'endogenous':
                self.logger.debug(
                    "Generating variable dataframe and cvxpy variable "
                    f"for endogenous data table '{data_table_key}'.")

                data_table.generate_coordinates_dataframe()
                data_table.cvxpy_var = self.problem.create_cvxpy_variable(
                    type=data_table.type,
                    shape=(data_table.table_length, 1),
                    name=data_table_key,
                )

        # generating variables dataframes with cvxpy var and filters dictionary
        # (endogenous vars are sliced from existing cvxpy var in data table
        self.logger.debug(
            "Generating data structures for all variables and constants.")

        for var_key, variable in self.index.variables.items():

            if variable.type == 'constant':
                variable.data = self.problem.generate_constant_data(
                    variable_name=var_key,
                    variable=variable
                )
            else:
                variable.data = self.problem.generate_vars_dataframe(
                    variable_name=var_key,
                    variable=variable
                )

    def define_numerical_problems(
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
            "Load symbolic problem, initialize dataframes with cvxpy problems ")

        self.problem.load_symbolic_problem_from_file(force_overwrite)
        self.problem.generate_problems_dataframe(force_overwrite)

    def solve_numerical_problems(
            self,
            solver: str = "",
            verbose: bool = True,
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
        self.problem.solve_all_problems(
            solver=solver,
            verbose=verbose,
            **kwargs
        )

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

                if variable.type != 'exogenous':
                    continue

                self.logger.debug(
                    f"Fetching data from table '{var_key}' "
                    "to cvxpy exogenous variable.")

                filter_header = Constants.get('_FILTER_DICT_HEADER')
                cvxpy_var_header = Constants.get('_CVXPY_VAR_HEADER')

                if variable.data is not None and \
                        variable.related_table is not None:

                    for row in variable.data.index:
                        raw_data = self.database.sqltools.filtered_table_to_dataframe(
                            table_name=variable.related_table,
                            filters_dict=variable.data[filter_header][row])

                        pivoted_data = variable.reshaping_sqlite_table_data(
                            data=raw_data
                        )

                        self.problem.data_to_cvxpy_variable(
                            cvxpy_var=variable.data[cvxpy_var_header][row],
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

                if data_table.type != 'endogenous':
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
