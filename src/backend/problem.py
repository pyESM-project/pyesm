from typing import Dict

import pandas as pd
import numpy as np
import cvxpy as cp

from src.constants import constants
from src.log_exc.logger import Logger
from src.support import util
from src.support.file_manager import FileManager
from src.backend.index import Index, Variable


class Problem:

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            paths: Dict[str, str],
            settings: Dict[str, str],
            index: Index,
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info(f"'{self}' object initialization...")

        self.files = files
        self.settings = settings
        self.index = index
        self.paths = paths

        self.symbolic_problem = None
        self.numeric_problems = None

        self.logger.info(f"'{self}' object initialized.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def create_cvxpy_variable(
            self,
            type: str,
            shape: [int, int],
            name: str = None,
    ) -> cp.Variable | cp.Parameter:

        if type == 'endogenous':
            return cp.Variable(shape=shape, name=name)
        elif type == 'exogenous':
            return cp.Parameter(shape=shape, name=name)
        elif type == 'constant':
            pass  # tbd
        else:
            error = f"Unsupported variable type: {type}"
            self.logger.error(error)
            raise ValueError(error)

    def data_to_cvxpy_variable(
            self,
            cvxpy_var: cp.Parameter,
            data: pd.DataFrame | np.ndarray,
    ) -> None:

        if not isinstance(cvxpy_var, cp.Parameter):
            error = "Data can only be assigned to exogenous variables."
            self.logger.error(error)
            raise ValueError(error)

        if isinstance(data, pd.DataFrame):
            cvxpy_var.value = data.values
        elif isinstance(data, np.ndarray):
            cvxpy_var.value = data
        else:
            error = "Supported data formats: pandas DataFrame or a numpy array."
            self.logger.error(error)
            raise ValueError(error)

    def generate_vars_dataframe(
            self,
            variable: Variable,
    ) -> pd.DataFrame:
        """For a Variable object, generates a Pandas DataFrame with the  
        hierarchy structure, the related cvxpy variables and the dictionary to
        filter the sql table for fetching data.
        """

        headers = {
            'cvxpy': constants._CVXPY_VAR_HEADER,
            'filter': constants._FILTER_DICT_HEADER,
        }

        self.logger.debug(
            f"Generating variable '{variable.symbol}' dataframe "
            "(cvxpy object, filter dictionary).")

        sets_parsing_hierarchy = variable.sets_parsing_hierarchy.values()

        var_data = util.unpivot_dict_to_dataframe(
            data_dict=variable.coordinates,
            key_order=sets_parsing_hierarchy
        )

        for item in headers.values():
            util.add_column_to_dataframe(
                dataframe=var_data,
                column_header=item,
                column_values=None,
            )

        for row in var_data.index:

            var_data.at[row, headers['cvxpy']] = \
                self.create_cvxpy_variable(
                    type=variable.type,
                    shape=variable.shape_size,
                    name=variable.symbol + str(variable.shape))

            var_filter = {}

            for header in var_data.loc[row].index:

                if sets_parsing_hierarchy is not None and \
                        header in sets_parsing_hierarchy:
                    var_filter[header] = [var_data.loc[row][header]]

                elif header == headers['cvxpy']:
                    for dim in variable.shape:
                        if isinstance(dim, int):
                            pass
                        elif isinstance(dim, str):
                            dim_header = variable.table_headers[dim][0]
                            var_filter[dim_header] = variable.coordinates[dim_header]

                elif header == headers['filter']:
                    pass

                else:
                    msg = f"Variable 'data' dataframe headers mismatch."
                    self.logger.error(msg)
                    raise ValueError(msg)

            var_data.at[row, headers['filter']] = var_filter

        return var_data

    def load_symbolic_problem_from_file(self) -> None:

        problem_file_name = constants._SETUP_FILES['problem']

        if self.symbolic_problem is not None:
            self.logger.warning(f"Symbolic problem already loaded.")
            user_input = input(f"Update symbolic problem? (y/[n]): ")

            if user_input.lower() != 'y':
                self.logger.info(f"Symbolic problem NOT updated.")
                return
            else:
                self.logger.info(f"Symbolic problem updated.")
        else:
            self.logger.info(
                f"Loading symbolic problem from '{problem_file_name}' file.")

        symbolic_problem = self.files.load_file(
            file_name=problem_file_name,
            dir_path=self.paths['model_dir'],
        )

        self.symbolic_problem = util.DotDict(symbolic_problem)

    def generate_problems_dataframe(self):

        if self.numeric_problems is not None:
            self.logger.warning(f"Numeric problem already defined.")
            user_input = input(f"Overwrite numeric problem? (y/[n]): ")

            if user_input.lower() != 'y':
                self.logger.info(f"Numeric problem NOT overwritten.")
                return
            else:
                self.logger.info(f"Numeric problem overwritten.")
        else:
            self.logger.debug(
                "Defining numeric problems based on symbolic problem.")

        headers = {
            'problem_info': constants._PROBLEM_INFO_HEADER,
            'objective_function': constants._OBJECTIVE_HEADER,
            'constraints': constants._CONSTRAINTS_HEADER,
            'problem': constants._PROBLEM_HEADER
        }

        dict_to_unpivot = {}
        for set_name, set_header in self.index.list_sets_split_problem.items():
            set_values = self.index.sets[set_name].data[set_header]
            dict_to_unpivot[set_name] = list(set_values)

        problem_data = util.unpivot_dict_to_dataframe(
            data_dict=dict_to_unpivot,
            key_order=self.index.list_sets_split_problem.keys(),
        )

        for item in headers.values():
            util.add_column_to_dataframe(
                dataframe=problem_data,
                column_header=item,
                column_values=None,
            )

        for row in problem_data.index:

            problem_info = [
                problem_data.loc[row][set_name]
                for set_name in self.index.list_sets_split_problem.keys()
            ]

            self.logger.debug(
                f"Defining numeric problem for set/s: {problem_info}.")

            problem_data.at[row, headers['problem_info']] = problem_info

            problem_data.at[row, headers['objective_function']] = \
                self.load_objective_function()

            problem_data.at[row, headers['constraints']] = \
                self.load_constraints()

            problem_data.at[row, headers['problem']] = \
                self.define_problem()

        self.numeric_problems = problem_data

    def load_objective_function(self):
        pass

    def load_constraints(self):
        pass

    def define_problem(self):
        pass
