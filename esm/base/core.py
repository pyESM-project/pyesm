from typing import Any, Dict
from pathlib import Path

import pandas as pd

from esm.base.database import Database
from esm.base.index import Index, Variable
from esm.base.problem import Problem
from esm.log_exc.logger import Logger
from esm import constants
from esm.support.file_manager import FileManager
from esm.support.sql_manager import SQLManager, connection


class Core:

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            settings: Dict[str, str],
            paths: Dict[str, Path],
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info(f"'{self}' object initialization...")

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

        self.logger.info(f"'{self}' initialized.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def initialize_problems_variables(self) -> None:
        self.logger.info(
            "Initialize variables dataframes "
            "(cvxpy objects, filters dictionaries).")

        for var_name, variable in self.index.variables.items():
            variable: Variable

            if variable.type == 'constant':
                variable.data = self.problem.generate_constant_data(
                    variable_name=var_name,
                    variable=variable
                )
            else:
                variable.data = self.problem.generate_vars_dataframe(
                    variable_name=var_name,
                    variable=variable
                )

    def define_numerical_problems(
            self,
            force_overwrite: bool = False,
    ) -> None:
        self.logger.info(
            "Load symbolic problem, initialize dataframes with cvxpy problems ")

        self.problem.load_symbolic_problem_from_file(force_overwrite)
        self.problem.generate_problems_dataframe(force_overwrite)

    def solve_numerical_problems(
            self,
            solver: str = None,
            verbose: bool = True,
            **kwargs: Any,
    ) -> None:
        self.problem.solve_all_problems(
            solver=solver,
            verbose=verbose,
            **kwargs
        )

    @connection
    def data_to_cvxpy_exogenous_vars(self) -> None:
        self.logger.info(
            f"Fetching data from '{self.settings['sqlite_database_file']}' "
            "to cvxpy exogenous variables.")

        for var_key, variable in self.index.variables.items():

            if isinstance(variable, Variable) and variable.type == 'exogenous':
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

    @connection
    def cvxpy_endogenous_data_to_database(self, operation: str) -> None:
        self.logger.info(
            "Fetching data from cvxpy endogenous variables "
            f"to SQLite database '{self.settings['sqlite_database_file']}' ")

        for var_key, variable in self.index.variables.items():

            if isinstance(variable, Variable) and variable.type == 'endogenous':
                self.logger.debug(
                    f"Fetching data from cvxpy variable '{var_key}' "
                    "to the related SQLite table.")

                cvxpy_var_data = pd.DataFrame()

                for row in variable.data.index:

                    none_coord = variable.none_data_coordinates(row)

                    if none_coord:
                        self.logger.debug(
                            f"SQLite table '{var_key}': "
                            f"no data available for {none_coord}.")
                        continue

                    cvxpy_var_data = pd.concat(
                        (cvxpy_var_data, variable.reshaping_variable_data(row))
                    )

                if cvxpy_var_data.empty:
                    self.logger.warning(
                        "No data available in cvxpy variable "
                        f"'{var_key}'")
                    return

                self.sqltools.dataframe_to_table(
                    table_name=variable.related_table,
                    dataframe=cvxpy_var_data,
                    operation=operation,
                )
