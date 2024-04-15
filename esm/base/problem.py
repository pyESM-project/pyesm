from typing import Any, Dict, List
import re

import pandas as pd
import numpy as np
import cvxpy as cp

from esm import constants
from esm.base.data_table import DataTable
from esm.log_exc import exceptions as exc
from esm.log_exc.logger import Logger
from esm.support import util
from esm.support.file_manager import FileManager
from esm.support.dotdict import DotDict
from esm.base.index import Index, Variable


class Problem:

    allowed_operators = constants._ALLOWED_OPERATORS

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            paths: Dict[str, str],
            settings: Dict[str, str],
            index: Index,
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.debug(f"'{self}' object initialization...")

        self.files = files
        self.settings = settings
        self.index = index
        self.paths = paths

        self.symbolic_problem = None
        self.numeric_problems = None
        self.model_run = None

        self.logger.debug(f"'{self}' object initialized.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def create_cvxpy_variable(
        self,
        type: str,
        shape: List[int],
        name: str = None,
        value: int | np.ndarray | np.matrix = None,
    ) -> cp.Variable | cp.Parameter | cp.Constant:

        if type == 'endogenous':
            return cp.Variable(shape=shape, name=name)
        elif type == 'exogenous':
            return cp.Parameter(shape=shape, name=name)
        elif type == 'constant':
            return cp.Constant(value=value)
        else:
            error = f"Unsupported variable type: {type}. " \
                "Check variables definitions."
            self.logger.error(error)
            raise exc.SettingsError(error)

    def slice_cvxpy_variable(
            self,
            type: str,
            shape: List[int],
            related_table_key: str,
            var_filter: Dict[str, List[str]],
    ) -> cp.Expression:

        if type != 'endogenous':
            msg = "Only endogenous variables can be sliced from DataTable."
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        related_table: DataTable = self.index.data[related_table_key]
        full_var_dataframe = related_table.coordinates_dataframe
        full_cvxpy_var = related_table.cvxpy_var

        filtered_var_dataframe = util.filter_dataframe(
            df_to_filter=full_var_dataframe,
            filter_dict=var_filter,
            reorder_columns_as_dict_keys=True,
            reorder_rows_based_on_filter=True,
        )

        filtered_index = filtered_var_dataframe.index
        sliced_cvxpy_var = full_cvxpy_var[filtered_index]
        sliced_cvxpy_var_reshaped = sliced_cvxpy_var.reshape(
            shape, order='C')

        return sliced_cvxpy_var_reshaped

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

    def generate_constant_data(
            self,
            variable_name: str,
            variable: Variable,
    ) -> cp.Constant:

        self.logger.debug(
            f"Generating constant '{variable_name}' as '{variable.value}'.")

        var_value = variable.define_constant(variable.value)

        return self.create_cvxpy_variable(
            type=variable.type,
            shape=variable.shape_size,
            name=variable_name + str(variable.shape),
            value=var_value,
        )

    def generate_vars_dataframe(
            self,
            variable_name: str,
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
            f"Generating dataframe for {variable.type} variable '{variable_name}' "
            "(cvxpy object, filter dictionary).")

        if variable.sets_parsing_hierarchy:
            sets_parsing_hierarchy = variable.sets_parsing_hierarchy.values()
        else:
            sets_parsing_hierarchy = None

        coordinates_dict_with_headers = util.substitute_keys(
            source_dict=variable.sets_parsing_hierarchy_values,
            key_mapping_dict=variable.sets_parsing_hierarchy,
        )

        var_data = util.unpivot_dict_to_dataframe(
            data_dict=coordinates_dict_with_headers,
            key_order=sets_parsing_hierarchy,
        )

        for item in headers.values():
            util.add_column_to_dataframe(
                dataframe=var_data,
                column_header=item,
                column_values=None,
            )

        # create variable filter
        for row in var_data.index:
            var_filter = {}

            for header in var_data.loc[row].index:

                if sets_parsing_hierarchy is not None and \
                        header in sets_parsing_hierarchy:
                    var_filter[header] = [var_data.loc[row][header]]

                elif header == headers['cvxpy']:
                    for dim in [0, 1]:
                        if isinstance(variable.shape[dim], int):
                            pass
                        elif isinstance(variable.shape[dim], str):
                            dim_header = variable.dims_labels[dim]
                            var_filter[dim_header] = variable.dims_items[dim]

                elif header == headers['filter']:
                    pass

                else:
                    msg = f"Variable 'data' dataframe headers mismatch."
                    self.logger.error(msg)
                    raise ValueError(msg)

            var_data.at[row, headers['filter']] = var_filter

        # create new cvxpy variables (exogenous vars and constants)
        if variable.type != 'endogenous':
            for row in var_data.index:
                var_data.at[row, headers['cvxpy']] = \
                    self.create_cvxpy_variable(
                        type=variable.type,
                        shape=variable.shape_size,
                        name=variable_name + str(variable.shape))

        # slice endogenous cvxpy variables (all endogenous variables are
        # slices of one unique variable stored in data table.)
        else:
            for row in var_data.index:
                var_data.at[row, headers['cvxpy']] = \
                    self.slice_cvxpy_variable(
                        type=variable.type,
                        shape=variable.shape_size,
                        related_table_key=variable.related_table,
                        var_filter=var_data.at[row, headers['filter']],
                )

        return var_data

    def load_symbolic_problem_from_file(
            self,
            force_overwrite: bool = False,
    ) -> None:

        problem_file_name = constants._SETUP_FILES[2]

        if self.symbolic_problem is not None:
            if not force_overwrite:
                self.logger.warning(f"Symbolic problem already loaded.")
                user_input = input(f"Update symbolic problem? (y/[n]): ")

                if user_input.lower() != 'y':
                    self.logger.info(f"Symbolic problem NOT updated.")
                    return
            else:
                self.logger.info(f"Symbolic problem updated.")
        else:
            self.logger.debug(
                f"Loading symbolic problem from '{problem_file_name}' file.")

        symbolic_problem = self.files.load_file(
            file_name=problem_file_name,
            dir_path=self.paths['model_dir'],
        )

        self.symbolic_problem = DotDict(symbolic_problem)

    def parse_allowed_symbolic_vars(
            self,
            expression: str,
            non_allowed_tokens: List[str] = allowed_operators.keys(),
            standard_pattern: str = r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'
    ) -> List[str]:

        tokens = re.findall(
            pattern=standard_pattern,
            string=expression,
        )

        allowed_vars = [
            token for token in tokens
            if token not in non_allowed_tokens
        ]

        if not allowed_vars:
            self.logger.warning(
                "Empty list of allowed variables "
                f"for expression: {expression}")

        return allowed_vars

    def check_variables_attribute_equality(
            self,
            variables_subset: DotDict[str, Variable],
            attribute: str,
    ) -> None:

        first_variable = next(iter(variables_subset.values()))
        first_var_attr = getattr(first_variable, attribute)

        all_same_attrs = all(
            getattr(variable, attribute) == first_var_attr
            for variable in variables_subset.values()
        )

        if not all_same_attrs:
            var_subset_symbols = [
                getattr(variable, 'symbol')
                for variable in variables_subset
            ]

            msg = f"Attributes '{attribute}' mismatch in the passed " \
                f"variables subset {var_subset_symbols}."
            self.logger.warning(msg)

    def find_common_sets_intra_problem(
        self,
        variables_subset: DotDict[str, Variable],
        allow_none: bool = True,
    ) -> Dict[str, str]:

        vars_sets_intra_problem = {
            key: variable.coordinates_info['intra']
            for key, variable in variables_subset.items()
        }

        if allow_none:
            vars_sets_intra_problem_list = [
                value for value in vars_sets_intra_problem.values() if value
            ]
        else:
            vars_sets_intra_problem_list = list(
                vars_sets_intra_problem.values())

        if not vars_sets_intra_problem_list:
            return {}

        if all(
            d == vars_sets_intra_problem_list[0]
            for d in vars_sets_intra_problem_list[1:]
        ):
            return vars_sets_intra_problem_list[0]
        else:
            msg = f"Fore each problem, each expression must be defined for " \
                "a unique common set (defined by 'sets_intra_problem')." \
                "A variable can be used for multiple expressions if ." \
                "'sets_intra_problem' is None."
            self.logger.error(msg)
            raise exc.ConceptualModelError(msg)

    def generate_problems_dataframe(
            self,
            force_overwrite: bool = False,
    ) -> None:

        if self.numeric_problems is not None:
            if not force_overwrite:
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
            'info': constants._PROBLEM_INFO_HEADER,
            'objective': constants._OBJECTIVE_HEADER,
            'constraints': constants._CONSTRAINTS_HEADER,
            'problem': constants._PROBLEM_HEADER,
            'status': constants._PROBLEM_STATUS_HEADER,
        }

        dict_to_unpivot = {}
        for set_name, set_header in self.index.sets_split_problem_list.items():
            set_values = self.index.sets[set_name].data[set_header]
            dict_to_unpivot[set_header] = list(set_values)

        list_sets_split_problem = self.index.sets_split_problem_list.values()

        problems_data = util.unpivot_dict_to_dataframe(
            data_dict=dict_to_unpivot,
            key_order=list_sets_split_problem,
        )

        for item in headers.values():
            util.add_column_to_dataframe(
                dataframe=problems_data,
                column_header=item,
                column_values=None,
            )

        for problem_num in problems_data.index:

            problem_info = [
                problems_data.loc[problem_num][set_name]
                for set_name in list_sets_split_problem
            ]

            self.logger.debug(
                "Defining numeric problem for combination "
                f"of sets: {problem_info}.")

            problem_filter = problems_data.loc[
                [problem_num],
                list_sets_split_problem
            ]

            # define explicit problem constraints (user-defined constraints)
            constraints = self.define_explicit_expressions(
                header_object=headers['constraints'],
                problem_filter=problem_filter
            )

            # define problem objective
            objective = sum(
                self.define_explicit_expressions(
                    header_object=headers['objective'],
                    problem_filter=problem_filter
                )
            )

            problem = cp.Problem(objective, constraints)

            problems_data.at[problem_num, headers['info']] = problem_info
            problems_data.at[problem_num, headers['constraints']] = constraints
            problems_data.at[problem_num, headers['objective']] = objective
            problems_data.at[problem_num, headers['problem']] = problem
            problems_data.at[problem_num, headers['status']] = None

        self.numeric_problems = problems_data

    def fetch_allowed_cvxpy_variables(
            self,
            variables_set_dict: DotDict[str, Variable],
            problem_filter: pd.DataFrame,
            set_intra_problem_header: str = None,
            set_intra_problem_value: str = None,
    ) -> Dict[str, cp.Parameter | cp.Variable]:

        allowed_variables = {}
        cvxpy_var_header = constants._CVXPY_VAR_HEADER

        for var_key, variable in variables_set_dict.items():
            variable: Variable

            # constants are directly assigned
            if variable.type == 'constant':
                allowed_variables[var_key] = variable.data
                continue

            # filter variable data based on problem filter
            variable_data = pd.merge(
                left=variable.data,
                right=problem_filter,
                on=list(problem_filter.columns),
                how='inner'
            )

            # if no sets intra-probles are defined for the variable, the cvxpy
            # variable is fetched for the current ploblem. cvxpy variable must
            # be unique for the defined problem
            if not variable.coordinates_info['intra']:
                if variable_data.shape[0] == 1:
                    allowed_variables[var_key] = \
                        variable_data[cvxpy_var_header].values[0]
                else:
                    msg = "Unable to identify a unique cvxpy variable for " \
                        f"{var_key} based on the current problem filter."
                    self.logger.error(msg)
                    raise exc.ConceptualModelError(msg)

            # if sets_intra_problem is defined for the variable, the right
            # cvxpy variable is fetched for the current problem
            elif variable.coordinates_info['intra'] \
                    and set_intra_problem_header and set_intra_problem_value:
                allowed_variables[var_key] = variable_data.loc[
                    variable_data[set_intra_problem_header] == set_intra_problem_value,
                    cvxpy_var_header,
                ].iloc[0]

            # other cases
            else:
                msg = "Unable to fetch cvxpy variable for " \
                    f"variable {var_key}."
                self.logger.error(msg)
                raise exc.ConceptualModelError(msg)

        return allowed_variables

    def execute_cvxpy_code(
            self,
            expression: str,
            allowed_variables: Dict[str, cp.Parameter | cp.Variable],
            allowed_operators: Dict[str, str] = constants._ALLOWED_OPERATORS,
    ) -> Any:

        local_vars = {}

        try:
            exec(
                'output = ' + expression,
                {**allowed_operators, **allowed_variables},
                local_vars,
            )

        except SyntaxError:
            msg = "Error in executing cvxpy expression: " \
                "check allowed variables, operators or expression syntax."
            self.logger.error(msg)
            raise exc.NumericalProblemError(msg)

        except NameError as msg:
            self.logger.error(f'NameError: {msg}')
            raise exc.NumericalProblemError(f'NameError: {msg}')

        return local_vars['output']

    def define_explicit_expressions(
            self,
            header_object: str,
            problem_filter: pd.DataFrame,
    ) -> List[Any]:

        expressions = []

        for expression in self.symbolic_problem[header_object]:

            vars_symbols_list = self.parse_allowed_symbolic_vars(expression)

            vars_subset = DotDict({
                key: variable for key, variable in self.index.variables.items()
                if key in vars_symbols_list
                and variable.type != 'constant'
            })

            constants_subset = DotDict({
                key: variable for key, variable in self.index.variables.items()
                if key in vars_symbols_list
                and variable.type == 'constant'
            })

            # look for intra-problem set in variables
            # only one intra-problem set per expression allowed
            set_intra_problem = self.find_common_sets_intra_problem(
                variables_subset=vars_subset,
            )

            if set_intra_problem:
                set_key = list(set_intra_problem.keys())[0]
                set_header = list(set_intra_problem.values())[0]
                set_data = self.index.sets[set_key].data

                # parse values in intra-problem-set
                for value in set_data[set_header]:

                    # fetch allowed cvxpy variables
                    allowed_variables = self.fetch_allowed_cvxpy_variables(
                        variables_set_dict={**vars_subset, **constants_subset},
                        problem_filter=problem_filter,
                        set_intra_problem_header=set_header,
                        set_intra_problem_value=value,
                    )

                    # define constraint
                    cvxpy_expression = self.execute_cvxpy_code(
                        expression=expression,
                        allowed_variables=allowed_variables,
                    )

                    expressions.append(cvxpy_expression)

            else:
                allowed_variables = self.fetch_allowed_cvxpy_variables(
                    variables_set_dict={**vars_subset, **constants_subset},
                    problem_filter=problem_filter,
                )

                cvxpy_expression = self.execute_cvxpy_code(
                    expression=expression,
                    allowed_variables=allowed_variables,
                )

                expressions.append(cvxpy_expression)

        return expressions

    def solve_problem(
            self,
            problem: cp.Problem,
            solver: str = None,
            verbose: bool = True,
            **kwargs: Any,
    ) -> None:

        problem.solve(
            solver=solver,
            verbose=verbose,
            **kwargs
        )

    def solve_all_problems(
            self,
            solver: str,
            verbose: bool,
            force_overwrite: bool = False,
            **kwargs: Any,
    ) -> None:

        if self.numeric_problems is None or \
                self.numeric_problems[constants._PROBLEM_HEADER].isna().all():
            msg = "Numeric problems have to be defined first"
            self.logger.warning(msg)
            raise exc.OperationalError(msg)

        if self.model_run:
            if not force_overwrite:
                self.logger.warning("Numeric problems already run.")
                user_input = input("Solve again numeric problems? (y/[n]): ")

                if user_input.lower() != 'y':
                    self.logger.info(
                        "Numeric problem NOT solved.")
                    return
            else:
                self.logger.info(
                    "Solving numeric problem and overwriting existing results.")

        for problem_num in self.numeric_problems.index:

            problem_info = self.numeric_problems.at[
                problem_num, constants._PROBLEM_INFO_HEADER]

            self.logger.info(f"Solving problem: {problem_info}.")

            problem = self.numeric_problems.at[
                problem_num, constants._PROBLEM_HEADER]

            self.solve_problem(
                problem=problem,
                solver=solver,
                verbose=verbose,
                **kwargs,
            )

            problem_status = getattr(problem, 'status', None)
            self.numeric_problems.at[
                problem_num,
                constants._PROBLEM_STATUS_HEADER] = problem_status

            self.logger.info(f"Problem status: '{problem_status}'")

        self.model_run = True
