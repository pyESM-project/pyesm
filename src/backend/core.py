from typing import Dict
from pathlib import Path

import pandas as pd

from src.backend.database import Database
from src.backend.index import Index, Variable
from src.backend.problem import Problem
from src.log_exc.logger import Logger
from src.constants import constants
from src.support.file_manager import FileManager
from src.support.sql_manager import SQLManager, connection


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
            database_name=self.settings['sqlite_database']['name'],
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

        for variable in self.index.variables.values():
            variable.data = self.problem.generate_vars_dataframe(variable)

    def define_numerical_problems(self) -> None:
        self.logger.info(
            "Load symbolic problem, initialize dataframes with cvxpy problems ")

        self.problem.load_symbolic_problem_from_file()
        self.problem.generate_problems_dataframe()

    def solve_numerical_problems(self) -> None:
        self.logger.info(
            "Solve numerical problems.")

        self.problem.solve_problems()

    @connection
    def data_to_cvxpy_exogenous_vars(self) -> None:
        self.logger.info(
            f"Fetching data from '{self.settings['sqlite_database']['name']}' "
            "to cvxpy exogenous variables.")

        for variable in self.index.variables.values():

            if isinstance(variable, Variable) and variable.type == 'exogenous':
                self.logger.debug(
                    f"Fetching data from table '{variable.symbol}' "
                    "to cvxpy exogenous variable.")

                filter_header = constants._FILTER_DICT_HEADER
                cvxpy_var_header = constants._CVXPY_VAR_HEADER

                for row in variable.data.index:

                    raw_data = self.database.sqltools.filtered_table_to_dataframe(
                        table_name=variable.symbol,
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
            f"to database '{self.settings['sqlite_database']['name']}' ")

        for variable in self.index.variables.values():

            if isinstance(variable, Variable) and variable.type == 'endogenous':
                self.logger.debug(
                    f"Fetching data from cvxpy variable '{variable.symbol} "
                    "to the related SQLite table.")

                cvxpy_var_data = pd.DataFrame()

                for row in variable.data.index:

                    none_coord = variable.none_data_coordinates(row)

                    if none_coord:
                        self.logger.warning(
                            f"SQLite table '{variable.symbol}': "
                            f"no data available for {none_coord}.")
                        continue

                    cvxpy_var_data = pd.concat(
                        (cvxpy_var_data, variable.reshaping_variable_data(row))
                    )

                self.sqltools.dataframe_to_table(
                    table_name=variable.symbol,
                    dataframe=cvxpy_var_data,
                    operation=operation,
                )
