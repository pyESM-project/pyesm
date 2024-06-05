"""
problem.py

@author: Matteo V. Rocco
@institution: Politecnico di Milano

This module defines the Problem class which is responsible for handling and solving
mathematical optimization problems using the CVXPY framework. It includes functionalities
for creating CVXPY variables and parameters, filtering and mapping variables to their
corresponding data, and constructing and solving optimization problems based on symbolic
representations.
The Problem class interacts with various components of the system such as data tables,
variables, and settings, leveraging the Index class for accessing and managing structured
data related to the optimization models.

Key functionalities include:
    Creation of optimization variables and parameters with CVXPY.
    Mapping and filtering of data according to variable requirements.
    Solving optimization problems and managing the results.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import re
import warnings

import pandas as pd
import numpy as np
import cvxpy as cp

from esm.constants import Constants
from esm.log_exc import exceptions as exc
from esm.log_exc.logger import Logger
from esm.support import util
from esm.support.file_manager import FileManager
from esm.support.dotdict import DotDict
from esm.base.index import Index, Variable


class Problem:
    """
    Manages the creation, configuration, and solving of optimization problems.
    This class uses CVXPY to define and solve optimization problems. It provides
    methods to create CVXPY variables, parameters, and constants, map data to
    these variables, and apply filtering based on the model's requirements.
    It is capable of handling multiple types of variables including endogenous,
    exogenous, and constants, each associated with specific data handling needs.

    Attributes:
        logger (Logger): Logger object for logging information and errors.
        files (FileManager): FileManager object for handling file operations.
        settings (Dict[str, str]): Configuration settings for optimization and
            model handling.
        index (Index): Index object providing access to data tables and variables.
        paths (Dict[str, Path]): Dictionary containing paths used across the model
            for file handling.
        symbolic_problem (DotDict | None): Symbolically defined problem loaded
            from configuration files.
        numeric_problems (pd.DataFrame | None): DataFrame containing defined
            numerical problems ready to solve.
        model_solved (bool | None): Indicates if the model has been solved.
        status: Indicates the status of the model (from cvxpy.Problem.status)

    Methods:
        create_cvxpy_variable: Creates a CVXPY variable, parameter, or constant
            based on specified attributes.
        slice_cvxpy_variable: Slices variables from data tables based on
            filtering conditions.
        data_to_cvxpy_variable: Assigns data to CVXPY parameters for use in
            model calculations.
        generate_constant_data: Generates constant data for use in the
            optimization problem.
        generate_vars_dataframe: Constructs a DataFrame for variables with
            necessary CVXPY objects and filtering information.
        load_symbolic_problem_from_file: Loads symbolic problem definitions
            from a specified file.
        parse_allowed_symbolic_vars: Extracts and validates variable names from
            symbolic expressions.
        check_variables_attribute_equality: Checks if a specified attribute is
            equal across a subset of variables.
        find_common_sets_intra_problem: Identifies common sets for intra-problem
            use from a subset of variables.
        fetch_common_vars_coords: Retrieves common coordinates for a specified
            category from a subset of variables.
        generate_problems_dataframe: Defines and constructs a DataFrame for
            managing multiple optimization problems.
        fetch_allowed_cvxpy_variables: Fetches and constructs a dictionary of
            allowed CVXPY variables for problem solving.
        execute_cvxpy_code: Executes CVXPY expressions dynamically using exec.
        define_expressions: Defines and constructs optimization expressions from
            symbolic definitions.
        solve_problem: Solves an individual CVXPY problem using specified solver
            options.
        solve_all_problems: Solves all defined problems and updates their status.
    """

    allowed_operators: Dict[str, Any] = Constants.get('_ALLOWED_OPERATORS')

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            paths: Dict[str, Path],
            settings: Dict[str, str],
            index: Index,
    ) -> None:

        self.logger = logger.get_child(__name__)
        self.logger.debug(f"'{self}' object initialization...")

        self.files = files
        self.settings = settings
        self.index = index
        self.paths = paths

        self.symbolic_problem = None
        self.numerical_problems = None
        self.status = 'not solved'

        self.logger.debug(f"'{self}' object initialized.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    @property
    def number_of_problems(self) -> int:
        """
        Returns the number of numerical problems defined in the system.
        """
        if self.numerical_problems is None:
            self.logger.warning("No numerical problems defined.")
            return 0

        if isinstance(self.numerical_problems, pd.DataFrame):
            return 1

        if isinstance(self.numerical_problems, dict):
            return len(self.numerical_problems)

    def create_cvxpy_variable(
        self,
        var_type: str,
        shape: Tuple[int, ...],
        name: Optional[str] = None,
        value: Optional[int | np.ndarray | np.matrix] = None,
    ) -> cp.Variable | cp.Parameter | cp.Constant:
        """
        Creates a CVXPY object based on the specified type. The type of object
        created (Variable, Parameter, or Constant) depends on the 'var_type' argument.

        Args:
            var_type (str): The type of the CVXPY object to create. Valid
                values are 'endogenous', 'exogenous', or 'constant'.
            shape (Tuple[int, ...]): The shape of the Variable or Parameter to
                be created.
            name (Optional[str]): The name assigned to the Variable or Parameter.
                This is not used for Constants.
            value (Optional[int | np.ndarray | np.matrix]): The numeric value
                for a Constant. This is ignored for Variable or Parameter types.

        Returns:
            cp.Variable | cp.Parameter | cp.Constant: The created CVXPY object.

        Raises:
            SettingsError: If an unsupported 'var_type' is provided.
        """

        if var_type == 'endogenous':
            return cp.Variable(shape=shape, name=name)

        if var_type == 'exogenous':
            return cp.Parameter(shape=shape, name=name)

        if var_type == 'constant':
            if value is None:
                msg = "Attribute 'value' must be provided for var_type 'constant'."
                self.logger.error(msg)
                raise exc.SettingsError(msg)
            return cp.Constant(value=value)

        error = f"Unsupported variable type: {var_type}. " \
            "Check variables definitions."
        self.logger.error(error)
        raise exc.SettingsError(error)

    def slice_cvxpy_variable(
            self,
            var_type: str,
            shape: Tuple[int],
            related_table_key: str,
            var_filter: Dict[str, List[str]],
    ) -> cp.Expression:
        """
        Slices a part of a CVXPY variable based on specified filtering criteria,
        applying only to endogenous variables.
        This method filters data in a specified DataTable using provided filtering
        criteria and slices the corresponding CVXPY variable to match the filtered
        data subset. The resulting variable slice is reshaped according to the
        specified dimensions.

        Args:
            var_type (str): The type of the variable, which must be 'endogenous'
                for slicing.
            shape (Tuple[int]): The target shape for the reshaped sliced variable.
            related_table_key (str): Key to identify the DataTable containing the
                variable to slice.
            var_filter (Dict[str, List[str]]): Dictionary specifying the filtering
                criteria to apply to the DataTable.

        Returns:
            cp.Expression: The reshaped sliced CVXPY variable.

        Raises:
            SettingsError: If an attempt is made to slice a non-endogenous variable
                or other slicing-related issues occur.
            MissingDataError: If the DataTable is missing necessary configurations
                or the data is undefined.
        """
        if var_type != 'endogenous':
            msg = "Only endogenous variables can be sliced from DataTable."
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        related_table = self.index.data[related_table_key]

        err_msg = []

        if not related_table:
            err_msg.append(f"Data table '{related_table_key}' not found.")

        if related_table.coordinates_dataframe is None or \
                related_table.coordinates_dataframe.empty:
            msg = f"Coordinates not defined for data table '{related_table_key}'."

        if not related_table.cvxpy_var:
            msg = f"Variables not defined data table '{related_table_key}'."

        if err_msg:
            self.logger.error("\n".join(err_msg))
            raise exc.MissingDataError("\n".join(err_msg))

        filtered_var_dataframe = util.filter_dataframe(
            df_to_filter=related_table.coordinates_dataframe,
            filter_dict=var_filter,
            reset_index=False,
            reorder_cols_based_on_filter=True,
            reorder_rows_based_on_filter=True,
        )

        if filtered_var_dataframe.empty:
            msg = f"Variable sliced from '{related_table_key}' is empty. " \
                "Check related variables filters."
            self.logger.error(msg)
            raise exc.MissingDataError(msg)

        filtered_index = filtered_var_dataframe.index
        sliced_cvxpy_var = related_table.cvxpy_var[filtered_index]
        sliced_cvxpy_var_reshaped = cp.reshape(
            sliced_cvxpy_var,
            shape=shape,
            order='C'
        )

        return sliced_cvxpy_var_reshaped

    def data_to_cvxpy_variable(
            self,
            cvxpy_var: cp.Parameter,
            data: pd.DataFrame | np.ndarray,
    ) -> None:
        """
        Assigns data to a CVXPY Parameter from a pandas DataFrame or numpy ndarray.
        This method is specifically for populating exogenous variables with data
        prior to solving an optimization problem. It validates that the provided
        CVXPY variable is indeed a Parameter and that the data format is supported.

        Args:
            cvxpy_var (cp.Parameter): The CVXPY Parameter to which data will be assigned.
            data (pd.DataFrame | np.ndarray): The data to assign to the CVXPY Parameter.
                Must be either a pandas DataFrame or a numpy ndarray.

        Raises:
            ConceptualModelError: If the provided cvxpy_var is not a CVXPY Parameter.
            ValueError: If the provided data is not in a supported format.
        """

        if not isinstance(cvxpy_var, cp.Parameter):
            msg = "Data can only be assigned to exogenous variables."
            self.logger.error(msg)
            raise exc.ConceptualModelError(msg)

        err_msg = []

        if isinstance(data, pd.DataFrame):
            if data.empty:
                err_msg.append("Provided DataFrame is empty.")
            cvxpy_var.value = data.values

        elif isinstance(data, np.ndarray):
            if data.size == 0:
                err_msg.append("Provided numpy array is empty.")
            cvxpy_var.value = data

        else:
            err_msg = "Supported data formats: pandas DataFrame or a numpy array."

        if err_msg:
            self.logger.error("\n".join(err_msg))
            raise exc.MissingDataError("\n".join(err_msg))

    def generate_constant_data(
            self,
            variable_name: str,
            variable: Variable,
    ) -> cp.Constant:
        """
        Generates a CVXPY Constant object for a given variable.
        This method ensures that the variable's value and type are correctly
        specified before creating the constant. The constant is created using
        predefined specifications in the Variable object.

        Args:
            variable_name (str): The name of the variable for which the constant
                is to be generated.
            variable (Variable): The Variable object containing the necessary
                specifications to create the constant.

        Returns:
            cp.Constant: The CVXPY Constant object created from the Variable
                specifications.

        Raises:
            SettingsError: If the variable's value or type is not specified.
            TypeError: If the generated object is not a CVXPY Constant as expected.
        """
        if not variable.value or not variable.type:
            msg = "Type of constant value or type not specified for variable " \
                f"'{variable_name}'"
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        if variable.type != 'constant':
            msg = f"Variable '{variable_name}' is not of type 'constant'."
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        self.logger.debug(
            f"Generating constant '{variable_name}' as '{variable.value}'.")

        var_value = variable.define_constant(variable.value)

        result = self.create_cvxpy_variable(
            var_type=variable.type,
            shape=variable.shape_size,
            name=variable_name + str(variable.shape),
            value=var_value,
        )

        if not isinstance(result, cp.Constant):
            msg = f"Expected a cvxpy.Constant but got {type(result)}."
            self.logger.error(msg)
            raise TypeError(msg)

        return result

    def generate_vars_dataframe(
            self,
            variable_name: str,
            variable: Variable,
            variable_type: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Generates a DataFrame containing information necessary to handle and process
        a Variable object for optimization tasks. This includes the hierarchy
        structure of the variable, associated CVXPY objects, and a dictionary
        for SQL filtering.
        This DataFrame organizes the variable's data, which is crucial for
        creating CVXPY variables and specifying filtering conditions for database
        queries based on the variable's properties.

        Args:
            variable_name (str): The name of the variable for which the DataFrame
                is generated.
            variable (Variable): The Variable object containing all required data
                and specifications.

        Returns:
            pd.DataFrame: A DataFrame with columns corresponding to CVXPY objects
                and SQL filters.

        Raises:
            ValueError: If there is a mismatch in expected DataFrame headers and
                the variable's data structure.
        """

        if variable_type is None:
            variable_type = variable.type

        self.logger.debug(
            f"Generating dataframe for {variable_type} variable '{variable_name}' "
            "(cvxpy object, filter dictionary).")

        headers = {
            'cvxpy': Constants.get('_CVXPY_VAR_HEADER'),
            'filter': Constants.get('_FILTER_DICT_HEADER'),
        }

        if variable.sets_parsing_hierarchy:
            sets_parsing_hierarchy = list(
                variable.sets_parsing_hierarchy.values())
        else:
            sets_parsing_hierarchy = None

        coordinates_dict_with_headers = util.substitute_dict_keys(
            source_dict=variable.sets_parsing_hierarchy_values,
            key_mapping_dict=variable.sets_parsing_hierarchy,
        )

        var_data = util.unpivot_dict_to_dataframe(
            data_dict=coordinates_dict_with_headers,
            key_order=sets_parsing_hierarchy,
        )

        for header in headers.values():
            util.add_column_to_dataframe(
                dataframe=var_data,
                column_header=header,
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
                    msg = "Variable 'data' dataframe headers mismatch."
                    self.logger.error(msg)
                    raise ValueError(msg)

            var_data.at[row, headers['filter']] = var_filter

        # create new cvxpy variables (exogenous vars and constants)
        if variable_type != 'endogenous':
            for row in var_data.index:
                var_data.at[row, headers['cvxpy']] = \
                    self.create_cvxpy_variable(
                        var_type=variable_type,
                        shape=variable.shape_size,
                        name=variable_name + str(variable.shape))

        # slice endogenous cvxpy variables (all endogenous variables are
        # slices of one unique variable stored in data table.)
        else:
            for row in var_data.index:
                var_data.at[row, headers['cvxpy']] = \
                    self.slice_cvxpy_variable(
                        var_type=variable_type,
                        shape=variable.shape_size,
                        related_table_key=variable.related_table,
                        var_filter=var_data.at[row, headers['filter']],
                )

        return var_data

    def load_symbolic_problem_from_file(
            self,
            force_overwrite: bool = False,
    ) -> None:
        """
        Loads a symbolic problem from a specified file into the system. The 
        symbolic problem defines the mathematical expressions and constraints 
        for the linear programming CVXPY model.
        If a symbolic problem is already loaded, the method will prompt the 
        user to confirm whether to overwrite it. The problem is only reloaded 
        from the file if the user explicitly confirms, or if 'force_overwrite' 
        is set to True.
        One or more symbolic problems can be loaded, depending on the structure
        of the problem file. One problem: dictionary with one level. More problems:
        each problem correspond to a key value pair in the dictionary.

        Args:
            force_overwrite (bool, optional): If True, the existing symbolic 
                problem will be overwritten without user confirmation. 
                Defaults to False.

        Notes:
            The problem definition is expected to be in a file specified by the 
                system's constants configuration. The file should contain a 
                dictionary with keys matching the constants '_OBJECTIVE_HEADER' 
                and '_CONSTRAINTS_HEADER'.

        Raises:
            SettingsError: If the symbolic problem structure is invalid.
        """
        problem_file_name = Constants.get('_SETUP_FILES')[2]
        problem_keys = [
            Constants.get('_OBJECTIVE_HEADER'),
            Constants.get('_CONSTRAINTS_HEADER'),
        ]

        if self.symbolic_problem is not None:
            if not force_overwrite:
                self.logger.warning("Symbolic problem already loaded.")
                user_input = input("Update symbolic problem? (y/[n]): ")

                if user_input.lower() != 'y':
                    self.logger.info("Symbolic problem NOT updated.")
                    return
            else:
                self.logger.info("Symbolic problem updated.")

        self.logger.debug(
            f"Loading symbolic problem from '{problem_file_name}' file.")

        data = self.files.load_file(
            file_name=problem_file_name,
            dir_path=self.paths['model_dir'],
        )

        if isinstance(data, dict):

            if util.find_dict_depth(data) == 1:

                if not util.items_in_list(data.keys(), problem_keys):
                    msg = "Invalid symbolic problem structure. Allowed problem " \
                        f"keys: '{problem_keys}'. Passed keys: '{data.keys()}' " \
                        f"Check '{problem_file_name}' file."
                    self.logger.error(msg)
                    raise exc.SettingsError(msg)

                self.symbolic_problem = DotDict(data)
                self.logger.debug(
                    "Symbolic problem successfully loaded.")

            elif util.find_dict_depth(data) == 2:

                self.symbolic_problem = {}

                for key, problem in data.items():

                    if not isinstance(problem, dict) or \
                            not util.items_in_list(problem.keys(), problem_keys):
                        msg = "Invalid symbolic problem structure. Allowed problem " \
                            f"keys: '{problem_keys}'. Passed keys: '{data.keys()}' " \
                            f"Check '{problem_file_name}' file."
                        self.logger.error(msg)
                        raise exc.SettingsError(msg)

                    self.symbolic_problem[key] = DotDict(problem)
                    self.logger.debug(
                        f"Symbolic problem '{key}' successfully loaded.")

            else:
                msg = "Invalid symbolic problem structure. " \
                    f"Check '{problem_file_name}' file."
                self.logger.error(msg)
                raise exc.SettingsError(msg)

        else:
            msg = f"Invalid problem data type. Check '{problem_file_name}' file."
            self.logger.error(msg)
            raise exc.SettingsError(msg)

    def parse_allowed_symbolic_vars(
            self,
            expression: str,
            non_allowed_tokens: Optional[List[str]] = None,
            standard_pattern: str = r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'
    ) -> List[str]:
        """
        Parses and extracts variable names from a symbolic expression, excluding
        any non-allowed tokens.
        This method uses regular expressions to identify potential variable names
        within the given expression and filters out any tokens that are designated
        as non-allowed, such as mathematical operators or reserved keywords.

        Args:
            expression (str): The symbolic expression from which to extract
                variable names.
            non_allowed_tokens (Optional[List[str]]): A list of tokens that should
                not be considered as variables. Defaults to the keys from
                allowed_operators.
            standard_pattern (str): The regex pattern used to identify possible
                variables in the expression.

        Returns:
            List[str]: A list of valid variable names extracted from the expression.
        """

        if non_allowed_tokens is None:
            non_allowed_tokens = list(self.allowed_operators.keys())

        tokens = re.findall(pattern=standard_pattern, string=expression)
        allowed_vars = [
            token for token in tokens if token not in non_allowed_tokens]

        if not allowed_vars:
            self.logger.warning(
                "Empty list of allowed variables "
                f"for expression: {expression}")

        return allowed_vars

    def check_variables_attribute_equality(
            self,
            variables_subset: DotDict,
            attribute: str,
    ) -> None:
        """
        Checks if a specific attribute is equal across all variables in a given subset.
        This method is used to ensure that all variables in a subset share the same
        value for a specified attribute, which can be critical for operations that
        require uniform variable configurations, such as batch processing or
        collective optimizations.

        Args:
            variables_subset (DotDict): A subset of variables to check.
            attribute (str): The attribute of the variables to check for uniformity.

        Raises:
            ValueError: If the attribute values are not the same across all variables
                in the subset.
        """
        try:
            first_variable = next(iter(variables_subset.values()))
        except StopIteration as e:
            msg = "Variable subset is empty."
            self.logger.error(msg)
            raise ValueError(msg) from e

        try:
            first_var_attr = getattr(first_variable, attribute)
        except AttributeError as e:
            msg = f"Attribute '{attribute}' not found in the first variable."
            self.logger.error(msg)
            raise ValueError(msg) from e

        all_same_attrs = all(
            getattr(variable, attribute, first_var_attr) == first_var_attr
            for variable in variables_subset.values()
        )

        if not all_same_attrs:
            var_subset_symbols = [
                getattr(variable, 'symbol', '<unknown>')
                for variable in variables_subset.values()
            ]

            msg = f"Attributes '{attribute}' mismatch in the passed " \
                f"variables subset {var_subset_symbols}."
            self.logger.warning(msg)
            raise ValueError(msg)

    def find_common_sets_intra_problem(
        self,
        variables_subset: DotDict,
        allow_none: bool = True,
    ) -> Dict[str, str]:
        """
        Identifies common intra-problem sets for a subset of variables.
        This method checks if there is a consistent set of intra-problem settings 
        across all variables in the subset. If 'allow_none' is True, variables 
        without specific intra-problem sets are considered uniform. If all variables 
        share the same intra-problem set or none, the common set is returned; 
        otherwise, an error is raised.

        Args:
            variables_subset (DotDict): A subset of variables from which to find 
                common intra-problem sets.
            allow_none (bool): Specifies whether to treat variables with no defined 
                intra-problem set as having a common set. Defaults to True.

        Returns:
            Dict[str, str]: A dictionary representing the common intra-problem set.

        Raises:
            ConceptualModelError: If no common intra-problem set is found and 
                'allow_none' is False, or if the intra-problem sets are inconsistent.

        Example:
            Assuming variables have differing or consistent intra-problem settings, 
                this method will validate and return the common setting or raise 
                an error.
        """
        vars_sets_intra_problem = {}
        for key, variable in variables_subset.items():
            variable: Variable
            vars_sets_intra_problem[key] = \
                variable.coordinates_info.get('intra', None)

        if allow_none:
            # in this case, a variable is equal for all intra-problem set items
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
            msg = "Fore each problem, each expression must be defined for " \
                "a unique common set (defined by 'sets_intra_problem')." \
                "A variable can be used for multiple expressions if ." \
                "'sets_intra_problem' is None."
            self.logger.error(msg)
            raise exc.ConceptualModelError(msg)

    def fetch_common_vars_coords(
        self,
        variables_subset: DotDict,
        coord_category: str,
        allow_empty_coord: bool,
    ) -> Dict[str, List[str]] | None:
        """
        Retrieves and verifies that a specific coordinate category is uniformly 
        defined across a subset of variables.
        This method ensures that all variables in the subset have the same settings 
        for a specified coordinate category, which is crucial for collective 
        operations in optimization tasks. If the variables do not have uniform 
        coordinates, it raises an error.

        Args:
            variables_subset (DotDict): A subset of variables to check for uniform 
                coordinate settings.
            coord_category (str): The category of coordinates to check (e.g., 
                'rows', 'cols').

        Returns:
            Dict[str, List[str]] | None: A dictionary of coordinates if uniform 
                across the subset; otherwise, raises an error.

        Raises:
            SettingsError: If the coordinates for the specified category are 
                not the same across all variables in the subset.
        """
        all_vars_coords = []
        for variable in variables_subset.values():
            variable: Variable
            all_vars_coords.append(
                variable.coordinates.get(coord_category)
            )

        # avoid check empty dictionaries
        if allow_empty_coord:
            all_vars_coords = [
                item for item in all_vars_coords
                if item != {}
            ]

        if not util.compare_dicts_ignoring_order(all_vars_coords):
            msg = "Passed variables are not defined with same coordinates " \
                f"for category '{coord_category}'."
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        return all_vars_coords[0]

    def generate_numerical_problems(
            self,
            force_overwrite: bool = False,
    ) -> None:

        if self.symbolic_problem is None:
            msg = "Symbolic problem must be loaded before generating numerical problems."
            self.logger.error(msg)
            raise exc.OperationalError(msg)

        if self.numerical_problems is not None:
            if not force_overwrite:
                self.logger.warning("Numerical problem already defined.")
                user_input = input("Overwrite numerical problem? (y/[n]): ")

                if user_input.lower() != 'y':
                    self.logger.info("Numerical problem NOT overwritten.")
                    return
            else:
                self.logger.info("Numerical problem overwritten.")
        else:
            self.logger.debug(
                "Defining numerical problems based on symbolic problems.")

        if util.find_dict_depth(self.symbolic_problem) == 1:
            self.numerical_problems = self.generate_problem_dataframe(
                symbolic_problem=self.symbolic_problem
            )
            self.problem_status = None

        elif util.find_dict_depth(self.symbolic_problem) == 2:
            self.numerical_problems = {
                problem_key: self.generate_problem_dataframe(
                    symbolic_problem=problem,
                    problem_key=problem_key,
                )
                for problem_key, problem in self.symbolic_problem.items()
            }
            self.problem_status = {key: None for key in self.symbolic_problem}

        else:
            msg = "Invalid symbolic problem structure. " \
                "Check symbolic problem definition."
            self.logger.error(msg)
            raise exc.SettingsError(msg)

    def generate_problem_dataframe(
            self,
            symbolic_problem: DotDict,
            problem_key: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        """
        headers = {
            'info': Constants.get('_PROBLEM_INFO_HEADER'),
            'objective': Constants.get('_OBJECTIVE_HEADER'),
            'constraints': Constants.get('_CONSTRAINTS_HEADER'),
            'problem': Constants.get('_PROBLEM_HEADER'),
            'status': Constants.get('_PROBLEM_STATUS_HEADER'),
        }

        dict_to_unpivot = {}
        for set_name, set_header in self.index.sets_split_problem_list.items():
            set_values = self.index.sets[set_name].data[set_header]
            dict_to_unpivot[set_header] = list(set_values)

        list_sets_split_problem = list(
            self.index.sets_split_problem_list.values())

        problems_df = util.unpivot_dict_to_dataframe(
            data_dict=dict_to_unpivot,
            key_order=list_sets_split_problem,
        )

        for item in headers.values():
            util.add_column_to_dataframe(
                dataframe=problems_df,
                column_header=item,
                column_values=None,
            )

        for sub_problem in problems_df.index:

            problem_info = [
                problems_df.loc[sub_problem][set_name]
                for set_name in list_sets_split_problem
            ]

            msg = "Defining numeric problem"
            if problem_key:
                msg += f" '{problem_key}'"
            if problem_info:
                msg += f" for combination of sets: {problem_info}."
            self.logger.debug(msg)

            problem_filter = problems_df.loc[
                [sub_problem],
                list_sets_split_problem
            ]

            # define explicit problem constraints (user-defined constraints)
            symbolic_constraints = symbolic_problem.get(headers['constraints'])
            constraints = self.define_expressions(
                symbolic_expressions=symbolic_constraints,
                problem_filter=problem_filter,
                problem_key=problem_key,
            )

            # define problem objective
            # if not defined in yml, a dummy objective is defined
            symbolic_objective = symbolic_problem.get(
                headers['objective'], None)
            if symbolic_objective:
                objective = sum(
                    self.define_expressions(
                        symbolic_expressions=symbolic_objective,
                        problem_filter=problem_filter,
                        problem_key=problem_key,
                    )
                )
            else:
                objective = cp.Minimize(1)

            problem = cp.Problem(objective, constraints)

            problems_df.at[sub_problem, headers['info']] = problem_info
            problems_df.at[sub_problem, headers['constraints']] = constraints
            problems_df.at[sub_problem, headers['objective']] = objective
            problems_df.at[sub_problem, headers['problem']] = problem
            problems_df.at[sub_problem, headers['status']] = None

        return problems_df

    def fetch_allowed_cvxpy_variables(
            self,
            variables_set_dict: Dict[str, Variable],
            problem_filter: pd.DataFrame,
            problem_key: Optional[int] = None,
            set_intra_problem_header: Optional[str] = None,
            set_intra_problem_value: Optional[str] = None,
    ) -> Dict[str, cp.Parameter | cp.Variable]:
        """
        Fetches allowed CVXPY variables from a set of variables based on specific 
        problem filters and conditions.

        Args:
            variables_set_dict (Dict[str, Variable]): A dictionary of variable 
                names to Variable objects.
            problem_filter (pd.DataFrame): A DataFrame containing filter criteria 
                to apply to the variables.
            set_intra_problem_header (str, optional): The header name within the 
                problem filter that specifies intra-problem distinctions.
            set_intra_problem_value (str, optional): The specific value within 
                the set_intra_problem_header to filter on.

        Returns:
            Dict[str, Union[cp.Parameter, cp.Variable]]: A dictionary of variable 
                names to their corresponding allowed CVXPY Parameter or Variable objects.

        Raises:
            ConceptualModelError: If a unique CVXPY variable cannot be identified 
                for the problem due to ambiguous or insufficient filter criteria 
                or if no appropriate CVXPY variable can be fetched for an 
                intra-problem specified variable.

        Notes:
            Constant type variables from the input dictionary are directly 
                assigned as values.
            Variables are filtered based on the problem_filter DataFrame using 
                an inner join operation.
            In cases where 'set_intra_problem_header' and 'set_intra_problem_value' 
                are provided, variables will be further filtered to match these 
                intra-problem criteria.
            The function will log errors and raise a 'ConceptualModelError' if 
                it encounters issues in fetching or identifying the required CVXPY 
                variables.
        """
        allowed_variables = {}
        cvxpy_var_header = Constants.get('_CVXPY_VAR_HEADER')

        for var_key, variable in variables_set_dict.items():
            variable: Variable

            if variable.data is None:
                msg = f"Variable data not defined for variable '{var_key}'"
                self.logger.error(msg)
                raise exc.MissingDataError(msg)

            # constants are directly assigned
            if variable.type == 'constant':
                allowed_variables[var_key] = variable.data
                continue

            if isinstance(variable.data, dict):
                if problem_key:
                    variable_data = variable.data[problem_key]
                else:
                    msg = "Problem key must be provided in case variables type " \
                        "is dependent by the problem."
                    self.logger.error(msg)
                    raise exc.SettingsError(msg)
            else:
                variable_data = variable.data

            # filter variable data based on problem filter
            if not problem_filter.empty:
                variable_data = pd.merge(
                    left=variable_data,
                    right=problem_filter,
                    on=list(problem_filter.columns),
                    how='inner'
                ).copy()

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
            allowed_operators: Optional[Dict[str, str]] = None
    ) -> Any:
        """
        Executes a CVXPY expression securely using allowed variables and operators.

        Args:
            expression (str): The CVXPY expression to be evaluated as a string.
            allowed_variables (Dict[str, Union[cp.Parameter, cp.Variable]]): A 
                dictionary mapping variable names to their corresponding CVXPY objects.
            allowed_operators (Dict[str, str], optional): A dictionary mapping 
                operator names to their Python equivalents, defaults to predefined 
                constants.

        Returns:
            Any: The result of the evaluated CVXPY expression.

        Raises:
            NumericalProblemError: If there is a syntax error in the expression, 
                or if the expression contains undefined names not included in 
                the allowed variables or operators.

        Notes:
            The function uses the `exec` function in a restricted environment 
                to prevent security risks. Only predefined variables and operators 
                can be used in the expression.
            Python's built-in `exec` is used with a controlled local namespace 
                to securely evaluate the expression.

        Examples:
            >>> allowed_vars = {'x': cp.Variable()}
            >>> allowed_ops = {'add': '+'}
            >>> execute_cvxpy_code('add(x, 5)', allowed_vars, allowed_ops)
            cp.Expression(...) # Depending on CVXPY's handling and the context
        """

        local_vars = {}
        if allowed_operators is None:
            allowed_operators = dict(Constants.get('_ALLOWED_OPERATORS'))

        try:
            # pylint: disable-next=exec-used
            exec(
                'output = ' + expression,
                {**allowed_operators, **allowed_variables},
                local_vars,
            )

        except SyntaxError as e:
            msg = "Error in executing cvxpy expression: " \
                "check allowed variables, operators or expression syntax."
            self.logger.error(msg)
            raise exc.NumericalProblemError(msg) from e

        except NameError as msg:
            self.logger.error(f'NameError: {msg}')
            raise exc.NumericalProblemError(f'NameError: {msg}')

        return local_vars['output']

    def define_expressions(
            self,
            symbolic_expressions: List[str],
            problem_filter: pd.DataFrame,
            problem_key: Optional[int] = None,
    ) -> List[cp.Expression]:
        """
        Constructs a list of CVXPY expressions based on symbolic problem definitions.

        Args:
            header_object (str): A key to access specific expressions from the 
                symbolic problem definitions.
            problem_filter (pd.DataFrame): A DataFrame used to filter relevant 
                variables for constructing the expressions.

        Returns:
            List[Any]: A list of CVXPY expressions that have been dynamically 
                constructed based on the input parameters.

        Raises:
            NumericalProblemError: If an expression cannot be generated due to 
                insufficient data or logical inconsistencies.

        Notes:
            The function processes each expression defined under 'header_object' 
                in the symbolic problem settings.
            It distinguishes between variable types (constant vs. non-constant) 
                and filters variables based on the specified problem settings.
            The function handles intra-problem set distinctions by dynamically 
                constructing expressions based on available data.
            Expressions are skipped if they do not meet the required conditions 
                specified in the 'problem_filter' and the intra-problem sets.
        """
        numerical_expressions = []

        if not symbolic_expressions:
            msg = "No symbolic expressions have passed. Check symbolic problem."
            self.logger.error(msg)
            raise exc.MissingDataError(msg)

        for expression in symbolic_expressions:

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

            # only one intra-problem set per expression allowed
            set_intra_problem = self.find_common_sets_intra_problem(
                variables_subset=vars_subset,
            )

            cvxpy_expression = None

            if set_intra_problem:
                set_key = list(set_intra_problem.keys())[0]
                set_header = list(set_intra_problem.values())[0]
                set_data = self.index.sets[set_key].data

                if set_data is None:
                    msg = f"Set data for set '{set_key}' not defined."
                    self.logger.error(msg)
                    raise exc.MissingDataError(msg)

                # check if there are filters (and if it is equal for all vars)
                common_intra_coords = self.fetch_common_vars_coords(
                    variables_subset=vars_subset,
                    coord_category='intra',
                    allow_empty_coord=True,
                )

                # parse values in intra-problem-set
                for value in set_data[set_header]:

                    # define expression only for filtered intra-problem set values
                    if common_intra_coords is None or \
                            value not in common_intra_coords.get(set_key, []):
                        continue

                    # fetch allowed cvxpy variables
                    allowed_variables = self.fetch_allowed_cvxpy_variables(
                        variables_set_dict={**vars_subset, **constants_subset},
                        problem_filter=problem_filter,
                        problem_key=problem_key,
                        set_intra_problem_header=set_header,
                        set_intra_problem_value=value,
                    )

                    # define constraint
                    cvxpy_expression = self.execute_cvxpy_code(
                        expression=expression,
                        allowed_variables=allowed_variables,
                    )

                    numerical_expressions.append(cvxpy_expression)

            else:
                allowed_variables = self.fetch_allowed_cvxpy_variables(
                    variables_set_dict={**vars_subset, **constants_subset},
                    problem_filter=problem_filter,
                    problem_key=problem_key,
                )

                cvxpy_expression = self.execute_cvxpy_code(
                    expression=expression,
                    allowed_variables=allowed_variables,
                )

                numerical_expressions.append(cvxpy_expression)

            if cvxpy_expression is None:
                msg = "CVXPY expression not generated for " \
                    f"expression: '{expression}'"
                self.logger.error(msg)
                raise exc.NumericalProblemError(msg)

        return numerical_expressions

    def solve_single_problem(
            self,
            problem_dataframe: pd.DataFrame,
            problem_name: Optional[str] = None,
            verbose: Optional[bool] = True,
            solver: Optional[str] = None,
            **kwargs: Any,
    ) -> None:
        """
        """

        if verbose == False:
            warnings.filterwarnings(
                'ignore',
                category=UserWarning,
                module='cvxpy.reductions.solvers.solving_chain'
            )

        for problem_num in problem_dataframe.index:

            problem_info: List[str] = problem_dataframe.at[
                problem_num, Constants.get('_PROBLEM_INFO_HEADER')]

            msg = "Solving numerical problem"
            if problem_name:
                msg += f" '{problem_name}'"
            if problem_info:
                msg += f" {problem_info}."
            self.logger.info(msg)

            numerical_problem: cp.Problem = problem_dataframe.at[
                problem_num, Constants.get('_PROBLEM_HEADER')]

            numerical_problem.solve(
                solver=solver,
                verbose=verbose,
                **kwargs,
            )

            problem_dataframe.at[
                problem_num, Constants.get('_PROBLEM_STATUS_HEADER')
            ] = numerical_problem.status

            self.logger.info(f"Problem status: '{numerical_problem.status}'")

    def fetch_problem_status(self) -> None:
        """
        Fetches the status of the problem. If all problems are 'optimal', sets 
        the status of the instance to 'optimal'.

        Raises:
            OperationalError: If the numerical problems are not defined.
        """
        if self.numerical_problems is None:
            msg = "Numerical problems must be defined first."
            self.logger.warning(msg)
            raise exc.OperationalError(msg)

        status_header = Constants.get('_PROBLEM_STATUS_HEADER')

        if isinstance(self.numerical_problems, pd.DataFrame):
            if all(self.numerical_problems[status_header] == 'optimal'):
                self.status = 'optimal'

        elif isinstance(self.numerical_problems, dict):
            if all(
                all(problem[status_header] == 'optimal')
                for problem in self.numerical_problems.values()
            ):
                self.status = 'optimal'

    def solve_problems(
            self,
            solver: str,
            verbose: bool,
            **kwargs: Any,
    ) -> None:
        """solve problems as defined in the numerical_problems attribute.
        as indepenent problems.
        """
        if isinstance(self.numerical_problems, pd.DataFrame):
            self.solve_single_problem(
                problem_dataframe=self.numerical_problems,
                verbose=verbose,
                solver=solver,
                **kwargs
            )

        elif isinstance(self.numerical_problems, dict):
            for problem_name in self.numerical_problems.keys():
                self.solve_single_problem(
                    problem_dataframe=self.numerical_problems[problem_name],
                    problem_name=problem_name,
                    verbose=verbose,
                    solver=solver,
                    **kwargs
                )
        else:
            if self.numerical_problems is None:
                msg = "Numerical problems must be defined first."
                self.logger.warning(msg)
                raise exc.OperationalError(msg)
