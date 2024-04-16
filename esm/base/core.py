from typing import Any, Dict
from pathlib import Path

from esm.base.data_table import DataTable
from esm.base.database import Database
from esm.base.index import Index, Variable
from esm.base.problem import Problem
from esm.log_exc.logger import Logger
from esm.log_exc import exceptions as exc
from esm import constants
from esm.support import util
from esm.support.file_manager import FileManager
from esm.support.sql_manager import SQLManager, db_handler


class Core:

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
        self.logger.debug(
            "Generating data structures for endogenous data tables "
            "(cvxpy objects, filters dict for data tables).")

        # generate dataframes and cvxpy var for whole endogenous data tables
        for data_table_key, data_table in self.index.data.items():
            data_table: DataTable

            if data_table.type == 'endogenous':

                self.logger.debug(
                    "Generating variable dataframe and cvxpy variable "
                    f"for endogenous data table '{data_table_key}'.")

                data_table.generate_coordinates_dataframe()
                data_table.cvxpy_var = self.problem.create_cvxpy_variable(
                    type=data_table.type,
                    shape=[data_table.table_length, 1],
                    name=data_table_key,
                )

        # generating variables dataframes with cvxpy var and filters dictionary
        # (endogenous vars are sliced from existing cvxpy var in data table
        self.logger.debug(
            "Generating data structures for all variables and constants.")

        for var_key, variable in self.index.variables.items():
            variable: Variable

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
        self.problem.solve_all_problems(
            solver=solver,
            verbose=verbose,
            **kwargs
        )

    def data_to_cvxpy_exogenous_vars(self) -> None:
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

                filter_header = constants._FILTER_DICT_HEADER
                cvxpy_var_header = constants._CVXPY_VAR_HEADER

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
        self.logger.debug(
            "Exporting data from cvxpy endogenous variable (in data table) "
            f"to SQLite database '{self.settings['sqlite_database_file']}' ")

        with db_handler(self.sqltools):
            for data_table_key, data_table in self.index.data.items():
                data_table: DataTable

                if not isinstance(data_table, DataTable):
                    msg = "Passed item is not a 'DataTable' class instance."
                    self.logger.error(msg)
                    raise TypeError(msg)

                if data_table.type != 'endogenous':
                    continue

                self.logger.debug(
                    "Exporting data from cvxpy variable to the related "
                    f"data table '{data_table_key}'. ")

                data_table_dataframe = data_table.coordinates_dataframe
                values_headers = constants._STD_VALUES_FIELD['values'][0]
                util.add_column_to_dataframe(
                    dataframe=data_table_dataframe,
                    column_header=values_headers,
                )

                cvxpy_var_data = data_table.cvxpy_var.value

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
