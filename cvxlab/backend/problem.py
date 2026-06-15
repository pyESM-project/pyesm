"""Module defining the Problem class.

This module defines the Problem class which is responsible for handling and solving
mathematical optimization problems. The class wraps the cvxpy package, serving as 
the engine for generating the mathematical problem. 
The Problem class includes functionalities for creating problem variables and constants, 
filtering and mapping variables to their corresponding data, and constructing and 
solving optimization problems based on symbolic representations.
The Problem class interacts with various components of the system such as data tables,
variables, and settings, leveraging the Index class for accessing and managing structured
data related to the optimization models.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from scipy.sparse import csr_matrix

import warnings

import pandas as pd
import numpy as np
import cvxpy as cp

from cvxlab.backend.data_table import DataTable
from cvxlab.defaults import Defaults
from cvxlab.log_exc import exceptions as exc
from cvxlab.log_exc.logger import Logger
from cvxlab.support import util, util_text
from cvxlab.support.file_manager import FileManager
from cvxlab.support.dotdict import DotDict
from cvxlab.backend.index import Index, Variable


class Problem:
    """Central class for managing and solving optimization problems.

    The Problem class provides methods for defining and solving optimization
    problems. It allows generating all items necessary to define a cvxpy numerical 
    optimization problem:

    - variables: endogenous, exogenous, and constants. Each variable type is
        associated to data retrieved and filtered from data tables.
    - expressions: objective function and constraints, can be defined symbolically
        by user and translated into cvxpy regular expressions.
    - problems: defined by a set of expressions, can be one or multiple
        problems to be solved as integrated or independent sub-problems.

    Attributes:

    - logger (Logger): Logger object for logging information, warnings, and errors.
    - files (FileManager): Manages file-related operations with files.
    - paths (Dict[str, Path]): Dictionary mapping of paths used in file operations.
    - settings (Dict[str, str]): Configuration settings for the model.
    - index (Index): Index instance providing central registry to access variables.
    - symbolic_problem (DotDict | None): Symbolic definition of the problem loaded
        from configuration files as a dictionary of expressions (objective function,
        equalities/inequalities).
    - numerical_problems (pd.DataFrame | None): DataFrame containing defined
        numerical problems and the related features.
    - problem_status: Current status of the model, reflecting the outcome of
        the latest problem-solving attempt.
    """

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            paths: Dict[str, Path],
            settings: Dict[str, str],
            index: Index,
    ) -> None:
        """Initialize a new instance of the Problem class.

        This constructor initializes the Problem instance with a logger, file manager,
        paths dictionary, settings dictionary, and embedding an Index instance
        to access model information.
        The constructor sets up the necessary attributes for managing and solving
        optimization problems using cvxpy package.

        Args:
            logger (Logger): Logger object for logging operations.
            files (FileManager): FileManager object for managing file operations.
            paths (Dict[str, Path]): Dictionary mapping of paths used in file operations.
            settings (Dict[str, str]): A dictionary containing configuration settings.
            index (Index): Index object that facilitates access to structured
                data related to optimization variables and tables.
        """
        self.logger = logger.get_child(__name__)

        self.files = files
        self.settings = settings
        self.index = index
        self.paths = paths

        self.symbolic_problem = {}
        self.numerical_problems = None
        self.problem_status = None

    @property
    def number_of_sub_problems(self) -> int:
        """Integer representing the number of sub-problems in the numerical model.

        This property returns the number of sub-problems defined in the numerical
        model. A sub-problem is defined as a numerical problem identified by a
        unique key in definition of symbolic problems.
        In numerical_problems attribute, a single sub-problem is represented
        as a pandas DataFrame, while multiple sub-problems are represented as
        a dictionary of DataFrames, each identified by a unique key.

        Returns:
            int: The number of sub-problems in the numerical model.
        """
        if self.numerical_problems is None:
            self.logger.warning("No numerical problems defined.")
            return 0

        if isinstance(self.numerical_problems, pd.DataFrame):
            return 1

        if isinstance(self.numerical_problems, dict):
            return len(self.numerical_problems)

    @property
    def endogenous_tables_all(self) -> list:
        """List of keys of the data tables that collect endogenous data.

        This property returns a list of keys corresponding to data tables
        that contain endogenous data (or both endogenous/exogenous data in case
        of integrated problems). 

        Returns:
            list: A list of keys for data tables with endogenous data.
        """
        allowed_var_types = Defaults.SymbolicDefinitions.VARIABLE_TYPES
        endogenous_tables_keys = []
        for table_key, data_table in self.index.data.items():
            data_table: DataTable
            if data_table.type not in [
                allowed_var_types['EXOGENOUS'], allowed_var_types['CONSTANT']
            ]:
                endogenous_tables_keys.append(table_key)

        return endogenous_tables_keys

    @property
    def endogenous_tables_hybrid(self) -> list:
        """List of keys of the data tables that collect mixed endogenous/exogenous data.

        This property returns a list of keys corresponding to data tables
        that contain both endogenous and exogenous data, typically used in
        integrated problems.

        Returns:
            list: A list of keys for data tables with mixed endogenous/exogenous data.
        """
        return [
            table_key for table_key, data_table in self.index.data.items()
            if isinstance(data_table.type, dict)
        ]

    def create_cvxpy_variable(
        self,
        var_type: str,
        shape: Tuple[int, ...],
        variable_domain: Optional[str] = None,
        name: Optional[str] = None,
        value: Optional[int | np.ndarray | np.matrix] = None,
    ) -> cp.Variable | cp.Parameter | cp.Constant:
        """Generate instances of cvxpy Variable, Parameter, or Constant.

        This class factory method generates and returns a cvxpy object
        (Variable, Parameter, or Constant) based on the specified type, with
        attributes defined by arguments (shape, variable_domain, name, value).

        Args:
            var_type (str): The type of the cvxpy object to create. Valid
                values are defined in Defaults.SymbolicDefinitions.VARIABLE_TYPES.
            shape (Tuple[int, ...]): The shape of the Variable or Parameter to
                be created.
            variable_domain (Optional[str]): Domain of the endogenous variable.
                Allowed values are defined in Defaults.SymbolicDefinitions.VARIABLE_DOMAINS:
                'integer' for integer variables, 'boolean' for binary {0,1} variables.
                None means continuous. Default to None.
            name (Optional[str]): The name assigned to the Variable or Parameter.
                This is not used for constants. Default to None.
            value (Optional[int | np.ndarray | np.matrix]): The numeric value
                for a Constant. This is ignored for Variable or Parameter types.

        Returns:
            cp.Variable | cp.Parameter | cp.Constant: The created CVXPY object.

        Raises:
            SettingsError: If an unsupported 'var_type' is provided, or if
                'variable_domain' is set for non-endogenous variables, or if 'value'
                is not provided for Constant type.
        """
        allowed_var_types = Defaults.SymbolicDefinitions.VARIABLE_TYPES
        allowed_domains = Defaults.SymbolicDefinitions.VARIABLE_DOMAINS

        if var_type != allowed_var_types['ENDOGENOUS'] and variable_domain is not None:
            msg = "Only endogenous data tables can have 'variable_domain' set."
            raise exc.SettingsError(msg)

        if variable_domain is not None and \
                variable_domain not in allowed_domains.values():
            msg = f"Unsupported variable domain: '{variable_domain}'. " \
                f"Allowed domains: {list(allowed_domains.values())}."
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        if var_type == allowed_var_types['ENDOGENOUS']:
            return cp.Variable(
                shape=shape,
                integer=(variable_domain == allowed_domains['INTEGER']),
                boolean=(variable_domain == allowed_domains['BOOLEAN']),
                name=name,
            )

        if var_type == allowed_var_types['EXOGENOUS']:
            return cp.Parameter(shape=shape, name=name)

        if var_type == allowed_var_types['CONSTANT']:
            if value is None:
                msg = "Attribute 'value' must be provided for var_type " \
                    f"{allowed_var_types['CONSTANT']}."
                self.logger.error(msg)
                raise exc.SettingsError(msg)
            return cp.Constant(value=value)

        error = f"Unsupported variable type: {var_type}. " \
            f"Allowed types: {list(allowed_var_types.values())}."
        self.logger.error(error)
        raise exc.SettingsError(error)

    def slice_cvxpy_variable(
            self,
            var_type: str,
            shape: Tuple[int],
            related_table_key: str,
            var_filter: Dict[str, List[str]],
            sub_problem_key: Optional[int] = None,
    ) -> cp.Expression:
        """Return a slice of a cvxpy variable based on filtering criteria.

        This method slices a part of a cvxpy variable (endogenous) based on 
        specified filtering criteria. This is necessary, since endogenous variables
        are stored as one unique variable in the related DataTable, and different
        slices of the same variables are used to generate expressions in the
        numerical problem.
        This method filters data in a specified DataTable using provided filtering
        criteria and slices the corresponding cvxpy variable to match the filtered
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
            sub_problem_key (int, optional): The sub-problem key to use for filtering
                data_table cvxpy_var. This key refers to a numerical problem defined
                by a combination of specific inter-problem sets coordinates. 
                Defaults to None. 

        Returns:
            cp.Expression: The reshaped sliced cvxpy variable.

        Raises:
            SettingsError: If an attempt is made to slice a non-endogenous variable
                or other slicing-related issues occur.
            MissingDataError: If the DataTable is missing necessary configurations
                or the data is undefined.
        """
        allowed_var_types = Defaults.SymbolicDefinitions.VARIABLE_TYPES

        if var_type != allowed_var_types['ENDOGENOUS']:
            msg = "Only endogenous variables can be sliced from DataTable."
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        related_table: DataTable = self.index.data[related_table_key]

        err_msg = []

        if not related_table:
            err_msg.append(
                f"Slicing variables | Data table '{related_table_key}' not found.")

        if related_table.coordinates_dataframe is None:
            err_msg.append(
                "Slicing variables | Coordinates not defined for data table "
                f"'{related_table_key}'."
            )

        if not related_table.cvxpy_var:
            err_msg.append(
                "Slicing variables | Variables not defined data table "
                f"'{related_table_key}'."
            )

        if err_msg:
            [self.logger.error(msg) for msg in err_msg]
            raise exc.MissingDataError("Slicing variables | Failed.")

        # use sub_problem_key to identify the endogenous variable for sub-problem
        if sub_problem_key is not None and \
                isinstance(related_table.coordinates_dataframe, dict) and \
                isinstance(related_table.cvxpy_var, dict):
            df_to_filter = related_table.coordinates_dataframe[sub_problem_key]
            cvxpy_var = related_table.cvxpy_var[sub_problem_key]
        else:
            df_to_filter = related_table.coordinates_dataframe
            cvxpy_var = related_table.cvxpy_var

        filtered_var_dataframe = util.filter_dataframe(
            df_to_filter=df_to_filter,
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
        sliced_cvxpy_var = cvxpy_var[filtered_index]
        sliced_cvxpy_var_reshaped = cp.reshape(
            sliced_cvxpy_var,
            shape=shape,
            order='C'
        )

        return sliced_cvxpy_var_reshaped

    def data_to_cvxpy_variable(
            self,
            var_key: str,
            cvxpy_var: cp.Parameter,
            data: pd.DataFrame | np.ndarray,
    ) -> None:
        """Assign to a cvxpy variable.

        This method put data in form of a pandas DataFrame or numpy ndarray and 
        assign it to a cvxpy variable. The method validates that the provided
        cvxpy variable is a Parameter (exogenous variable) and that the data 
        format is supported.
        If the data is sparse (i.e., contains a significant number of zeros),
        it is converted to a scipy csr_matrix before assignment to optimize
        memory usage and computational efficiency. 

        Args:
            var_key (str): The name of the variable to which data will be assigned.
            cvxpy_var (cp.Parameter): The cvxpy Parameter to which data will be assigned.
            data (pd.DataFrame | np.ndarray): The data to assign to the CVXPY Parameter.
                Must be either a pandas DataFrame or a numpy ndarray.

        Raises:
            OperationalError: If the provided cvxpy_var is not a cvxpy Parameter.
            MissingDataError: If the provided data is empty or not in a supported format.
        """
        if not isinstance(cvxpy_var, cp.Parameter):
            msg = "Data can only be assigned to exogenous variables."
            self.logger.error(msg)
            raise exc.OperationalError(msg)

        err_msg = []

        if isinstance(data, pd.DataFrame):
            if data.empty:
                err_msg.append(
                    f"Variable '{var_key}' | Provided DataFrame is empty.")
            data_values = data.values

        elif isinstance(data, np.ndarray):
            if data.size == 0:
                err_msg.append(
                    f"Variable '{var_key}' | Provided numpy array is empty.")
            data_values = data

        else:
            err_msg.append(
                f"Variable '{var_key}' | Supported data formats: pandas "
                "DataFrame or a numpy array."
            )

        if err_msg:
            [self.logger.error(msg) for msg in err_msg]
            raise exc.MissingDataError(
                f"Variable '{var_key}' | Data assigment failed."
            )

        # conversion to sparse matrix if data is sparse
        if util.is_sparse(
            data_values,
            Defaults.NumericalSettings.SPARSE_MATRIX_ZEROS_THRESHOLD
        ):
            data_values_converted = csr_matrix(data_values)
        else:
            data_values_converted = data_values

        cvxpy_var.value = data_values_converted

    def generate_constant_data(
            self,
            variable_key: str,
            variable: Variable,
    ) -> cp.Constant:
        """Generate a cvxpy constant from a Variable object.

        This method generates a cvxpy Constant object, defined according to 
        properties of a given Variable instance.
        The method first derive the value of the constant with the define_constant()
        method, then it uses create_cvxpy_variable() to create the Constant.
        In case the constant value is sparse (i.e., contains a significant
        number of zeros), it is converted to a scipy csr_matrix to optimize
        memory usage and computational efficiency.

        Args:
            variable_key (str): The name of the variable for which the constant
                is to be generated.
            variable (Variable): The Variable object containing the necessary
                specifications to create the constant.

        Returns:
            cp.Constant: The cvxpy Constant instance created from the Variable
                specifications.

        Raises:
            SettingsError: If the variable's value or type is not specified.
        """
        sparse_threshold = Defaults.NumericalSettings.SPARSE_MATRIX_ZEROS_THRESHOLD
        allowed_var_types = Defaults.SymbolicDefinitions.VARIABLE_TYPES

        if not variable.value or not variable.type:
            msg = f"Variable '{variable_key}' | Type or value of the constant " \
                "not specified."
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        if variable.type != allowed_var_types['CONSTANT']:
            msg = f"Variable '{variable_key}' | Should be of type " \
                f"'{allowed_var_types['CONSTANT']}'."
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        var_value = variable.define_constant(variable.value)

        if util.is_sparse(var_value, sparse_threshold):
            var_value = csr_matrix(var_value)

        result = self.create_cvxpy_variable(
            var_type=variable.type,
            shape=variable.shape_size,
            name=variable_key + str(variable.shape_sets),
            value=var_value,
        )

        return result

    def generate_vars_dataframe(
            self,
            variable_key: str,
            variable: Variable,
            variable_type: Optional[str] = None,
    ) -> pd.DataFrame:
        """Generate DataFrame embedding information of the variable.

        This method generates a DataFrame containing information necessary to 
        handle and process a Variable object in the numerical problem. This 
        includes the hierarchy structure of the variable, the associated cvxpy 
        objects, and a dictionary for SQL filtering.

        Args:
            variable_key (str): The name of the variable for which the DataFrame
                is generated.
            variable (Variable): The Variable instance containing all necessary
                data and specifications.
            variable_type (Optional[str]): Specifies the type of the variable,
                defaults to the type defined in the Variable object.

        Returns:
            pd.DataFrame: A DataFrame with columns corresponding to cvxpy objects
                and coordinates filters.

        Raises:
            ValueError: If there is a mismatch in expected DataFrame headers and
                the variable's data structure.
        """
        if variable_type is None:
            variable_type = variable.type

        headers = {
            'cvxpy': Defaults.Labels.CVXPY_VAR,
            'filter': Defaults.Labels.FILTER_DICT_KEY,
            'sub_problem_key': Defaults.Labels.SUB_PROBLEM_KEY,
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
            var_data = util.add_column_to_dataframe(
                dataframe=var_data,
                column_header=header,
                column_values=None,
            )

        # create variable filter
        for row in var_data.index:
            var_filter = {}
            var_data_item: pd.Series = var_data.loc[row]

            for header in var_data_item.index:

                if sets_parsing_hierarchy is not None and \
                        header in sets_parsing_hierarchy:
                    var_filter[header] = [var_data_item[header]]

                elif header == headers['cvxpy']:
                    for dim in [0, 1]:
                        if isinstance(variable.shape_sets[dim], int):
                            pass
                        elif isinstance(variable.shape_sets[dim], list):

                            for dim_header, dim_items in zip(
                                variable.dims_labels[dim],
                                variable.dims_items[dim],
                            ):
                                var_filter[dim_header] = dim_items

                elif header in [headers['filter'], headers['sub_problem_key']]:
                    pass

                else:
                    msg = "Variable 'data' dataframe headers mismatch."
                    self.logger.error(msg)
                    raise ValueError(msg)

            var_data.at[row, headers['filter']] = var_filter

        # identify sub_problem_key
        allowed_var_types = Defaults.SymbolicDefinitions.VARIABLE_TYPES
        inter_coord_label = 'inter'

        if variable_type not in [
            allowed_var_types['EXOGENOUS'], allowed_var_types['CONSTANT']] and \
                variable.coordinates[inter_coord_label]:
            for row in var_data.index:

                inter_problem_coords = {
                    set_label: variable.coordinates[inter_coord_label][set_key]
                    for set_key, set_label
                    in variable.coordinates_info[inter_coord_label].items()
                }
                inter_df = util.unpivot_dict_to_dataframe(inter_problem_coords)

                var_filter: dict = var_data.at[row, headers['filter']]
                var_inter_problem_coords = {
                    key: value
                    for key, value in var_filter.items()
                    if key in inter_problem_coords.keys()
                }
                var_inter_df = util.unpivot_dict_to_dataframe(
                    var_inter_problem_coords)

                merged_df = inter_df.reset_index().merge(
                    var_inter_df,
                    on=list(inter_df.columns),
                    how='inner'
                ).set_index('index')

                var_data.at[row, headers['sub_problem_key']] = \
                    merged_df.index[0]

        # create new cvxpy variables (exogenous vars and constants)
        if variable_type != allowed_var_types['ENDOGENOUS']:
            for row in var_data.index:
                var_data.at[row, headers['cvxpy']] = \
                    self.create_cvxpy_variable(
                        var_type=variable_type,
                        shape=variable.shape_size,
                        name=variable_key + str(variable.shape_sets))

        # slice endogenous cvxpy variables (all endogenous variables are
        # slices of one unique variable for each sub-problem stored in data table.)
        # sub-problem_key refers to each numerical problem resulting from a combination
        # of specific inter-problem sets coordinates.
        else:
            for row in var_data.index:
                sub_problem_key = var_data.at[row, headers['sub_problem_key']]

                var_data.at[row, headers['cvxpy']] = \
                    self.slice_cvxpy_variable(
                        var_type=variable_type,
                        shape=variable.shape_size,
                        related_table_key=variable.related_table,
                        var_filter=var_data.at[row, headers['filter']],
                        sub_problem_key=sub_problem_key,
                )

        return var_data

    def load_symbolic_problem_from_file(
            self,
            force_overwrite: bool = False,
    ) -> None:
        """Load symbolic problem from model setup file.

        This method loads the symbolic definition of the optimization problem
        from a specified model setup file (yml, Excel). It validates the structure 
        of the loaded data against a predefined schema to ensure correctness.

        Args:
            force_overwrite (bool, optional): If True, forces the re-export of 
                data even if the data table already exists. Defaults to False.

        Raises:
            exc.SettingsError: _description_
        """
        source = self.settings['model_settings_from']
        problem_key = Defaults.ConfigFiles.SETUP_INFO[2]
        problem_structure = Defaults.DefaultStructures.PROBLEM_STRUCTURE[1]

        if self.symbolic_problem:
            if not force_overwrite:
                self.logger.warning("Symbolic problem already loaded.")
                if not util.get_user_confirmation("Update symbolic problem?"):
                    self.logger.info("Symbolic problem NOT updated.")
                    return
            else:
                self.logger.info("Symbolic problem updated.")

        self.logger.debug(
            "Loading and validating structure of symbolic problem from "
            f"'{source}' source.")

        data = self.files.load_data_structure(
            structure_key=problem_key,
            source=source,
            dir_path=self.paths['model_dir'],
        )

        invalid_entries = {}

        if util.find_dict_depth(data) == 1:
            invalid_entries = self.files.validate_data_structure(
                data, problem_structure)

        elif util.find_dict_depth(data) == 2:
            invalid_entries = {
                key: problems
                for key, value in data.items()
                if (
                    problems := self.files.validate_data_structure(
                        value, problem_structure
                    )
                )
            }

        else:
            msg = f"Invalid symbolic problem structure. Check '{source}' file."
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        if invalid_entries:
            self.logger.error(
                f"Validation error report ===================================")
            if self.settings['detailed_validation']:
                for key, error_log in invalid_entries.items():
                    for coord, error in error_log.items():
                        self.logger.error(
                            f"Validation error | {problem_key} | '{key}' | "
                            f"{coord} | {error}"
                        )
            else:
                self.logger.error(
                    f"Validation | {problem_key} | Entries: "
                    f"{list(invalid_entries.keys())}")

            msg = f"'{problem_key}' data validation not successful. " \
                f"Check setup '{source}' file. "
            if not self.settings['detailed_validation']:
                msg += "Set 'detailed_validation=True' for more information."

            self.logger.error(msg)
            raise exc.SettingsError(msg)

        if util.find_dict_depth(data) == 1:
            self.symbolic_problem = DotDict(data)

        elif util.find_dict_depth(data) == 2:
            self.symbolic_problem = {}
            for key, problem in data.items():
                self.symbolic_problem[key] = DotDict(problem)

    def _collect_problems_expressions(self) -> Dict[Optional[int | str], List[str]]:
        """Collect symbolic expressions grouped by problem key.

        Normalizes the symbolic_problem structure into a dict keyed by problem_key
        (None for single-problem setups) and aggregates all expressions by selecting
        entries under Defaults.Labels.OBJECTIVE and Defaults.Labels.EXPRESSIONS.

        Returns:
            Dict[Optional[int], List[str]]: A mapping from problem_key to a flat list
            of expression strings to be parsed/validated.

        Notes:
            - If no symbolic_problem is loaded, returns an empty dict.
            - When symbolic_problem depth is 1, it is wrapped with key None.
        """
        if not self.symbolic_problem:
            return {}

        if util.find_dict_depth(self.symbolic_problem) == 1:
            symbolic_problem = {None: self.symbolic_problem}
        else:
            symbolic_problem = self.symbolic_problem

        problem_structure_labels = [
            Defaults.Labels.OBJECTIVE,
            Defaults.Labels.EXPRESSIONS,
        ]

        return {
            problem_key: [
                expr
                for label, expr_list in problem.items()
                if label in problem_structure_labels
                for expr in expr_list
            ]
            for problem_key, problem in symbolic_problem.items()
        }

    def _get_vars_in_expression(
        self,
        expression: str,
        tokens: Optional[Dict[str, List[str]]] = None,
    ) -> Dict[str, Variable]:
        """
        Return {var_key: Variable} for variables referenced in a literal expression.

        If 'tokens' is provided (as built by TOKEN_PATTERNS), it will use tokens['text'].
        Otherwise it will tokenize the expression to extract text tokens.
        """
        token_patterns = Defaults.SymbolicDefinitions.TOKEN_PATTERNS
        if tokens is None:
            text_tokens = util_text.extract_tokens_from_expression(
                expression=expression,
                pattern=token_patterns['text'],
            )
        else:
            text_tokens = tokens.get('text', [])

        return {
            var_key: variable
            for var_key, variable in self.index.variables.items()
            if var_key in text_tokens
        }

    def validate_symbolic_expressions(self) -> None:
        """Validate symbolic expressions.

        This method checks the coherence between properties of variables in each
        problem sybolic expression. The method parses each symbolic expression, 
        identifies variables names, math operators and user-defined operators, 
        constants, numbers and other symbols (relying on util_text methods). 
        Then, the following checks are performed on each expression (Further 
        checks can be added):

        - Number of chars in extracted tokens must match the expression length;
        - Parentheses must be balanced;
        - Variables, operators and user-defined operators must be allowed;
        - Variables names not overlapped with user-defined operators;
        - Intra-problem sets in a variable must not be a dimension in other 
            variables (example: in a same expression, i cannot have years as 
            a variable dimension and, at the same time having time as an 
            intra-problem set in another variable).

        Raises:
            exc.ConceptualModelError: If any of the validation checks fail.
        """
        self.logger.debug(
            f"Validating symbolic problem expressions coherence.")

        source_format = self.settings['model_settings_from']
        token_patterns = Defaults.SymbolicDefinitions.TOKEN_PATTERNS
        allowed_operators = Defaults.SymbolicDefinitions.ALLOWED_OPERATORS

        errors = []

        problems_expressions = self._collect_problems_expressions()

        for problem_key, expr_list in problems_expressions.items():

            for expression in expr_list:
                expression: str

                msg_str = f"Problem '{problem_key}' | " if problem_key is not None else ""
                msg_str += f"Expression '{expression}' | "

                # get all tokens from expression
                tokens = {
                    key: util_text.extract_tokens_from_expression(
                        expression=expression,
                        pattern=token_patterns[key],
                    )
                    for key in token_patterns.keys()
                }

                # identify unrecognized tokens in the expression
                all_tokens = [
                    token
                    for tokens_list in tokens.values()
                    for token in tokens_list
                ]
                all_tokens_sorted = sorted(all_tokens, key=len, reverse=True)

                residual = expression.replace(' ', '')
                for token in all_tokens_sorted:
                    residual = residual.replace(token, '', 1)

                if residual:
                    errors.append(
                        msg_str + f"Unrecognized chars: {list(residual)})"
                    )

                # check if parentheses are balanced
                if not util_text.balanced_parentheses(tokens['parentheses']):
                    errors.append(msg_str + "Parentheses are not balanced.")

                # spot non-allowed variables/symbolic operators
                non_allowed_tokens = [
                    token for token in tokens['text']
                    if token not in self.index.list_variables
                    if token not in allowed_operators
                ]
                if non_allowed_tokens:
                    errors.append(
                        msg_str + f"Non-allowed variable/operator: {non_allowed_tokens}.")

                # variables names not overlapped with custom operators
                non_allowed_vars_keys = [
                    token for token in tokens['text']
                    if token in self.index.list_variables and token in allowed_operators
                ]
                if non_allowed_vars_keys:
                    errors.append(
                        msg_str + f"Variable names overlapped with custom operators: "
                        f"{non_allowed_vars_keys}.")

                # intra-problem sets in a variable must not be a dimension in other variables
                vars_in_expression = self._get_vars_in_expression(
                    expression, tokens)

                intra_problem_sets = set()
                shape_set_map = {}

                for var_key, variable in vars_in_expression.items():
                    variable: Variable
                    intra_problem_sets.update(variable.intra_sets or [])
                    shape_set_map[var_key] = set(
                        util.flattening_list(variable.shape_sets)
                    )

                for var_key, dim_sets in shape_set_map.items():
                    overlapping_sets = intra_problem_sets & dim_sets
                    if overlapping_sets:
                        errors.append(
                            msg_str +
                            f"Variable '{var_key}' has shape_set(s) overlapped "
                            f"with intra-problem set(s) of the expression: "
                            f"{intra_problem_sets}."
                        )

                # other checks can be added here ...

        if errors:
            self.logger.error(
                f"Expressions validation report {'=' * 35}")
            for error_msg in errors:
                self.logger.error(f"Validation error | {error_msg}")

            msg = f"Symbolic expressions validation not successful. " \
                f"Check setup '{source_format}' file. "
            self.logger.error(msg)
            raise exc.ConceptualModelError(msg)

    def add_implicit_symbolic_expressions(self) -> None:
        """Add implicit symbolic expressions based on variable sign attributes.

        This method adds implicit symbolic expressions to the existing symbolic
        problem definitions based on the nonneg attribute of variables.
        For each variable with a defined nonneg attribute as true, the method 
        generates corresponding symbolic expressions (e.g., "var_key >= 0") and 
        appends them to the expressions list in the symbolic problem structure.

        NOTES:
            In case of single-problem setups, all implicit expressions are added
                to the problem.
            In case of multiple problems: 
                For hybrid variables type, the non-negativity constraints 
                    are added to the problem where the variable is endogenous.
                For pure endogenous variables, the non-negativity constraints are
                    added only if the variable is used in the problem expressions.
                    In case the variable is not used in any problem expressions,
                    an error is raised (constraint must be explicitly defined in
                    symbolic problem).
        """
        self.logger.debug(f"Adding implicit symbolic expressions.")

        expressions_key = Defaults.Labels.EXPRESSIONS
        var_types = Defaults.SymbolicDefinitions.VARIABLE_TYPES

        if not self.symbolic_problem:
            return

        problems_expressions = self._collect_problems_expressions()

        if util.find_dict_depth(self.symbolic_problem) == 1:
            symbolic_problem = {None: self.symbolic_problem}
        else:
            symbolic_problem = self.symbolic_problem

        # Collect variables in all expressions for all problems
        problems_vars: Dict[Optional[int | str], List[str]] = {}
        for problem_key, expr_list in problems_expressions.items():
            var_keys: set[str] = set()
            for expression in expr_list:
                var_keys.update(
                    self._get_vars_in_expression(expression).keys())
            problems_vars[problem_key] = list(var_keys)

        implicit_expr_by_problem: Dict[Optional[int | str], List[str]] = {
            problem_key: [] for problem_key in symbolic_problem
        }
        errors: List[str] = []

        # Add implicit expressions based on variable sign attributes
        for problem_key, problem in symbolic_problem.items():

            for var_key, variable in self.index.variables.items():
                variable: Variable

                if not variable.nonneg:
                    continue

                # Case of one single problem: add all implicit constraints
                if len(problems_expressions) == 1:
                    constraint = f"{var_key} >= 0"
                    if constraint not in problems_expressions.get(problem_key, []) and \
                            constraint not in implicit_expr_by_problem[problem_key]:
                        implicit_expr_by_problem[problem_key].append(
                            constraint)
                        continue

                # Multiple problems, hybrid variables: add implicit expressions
                # only to problem where variable is endogenous
                if isinstance(variable.type, dict):
                    if variable.type[problem_key] == var_types['ENDOGENOUS']:
                        constraint = f"{var_key} >= 0"
                        if constraint not in problems_expressions.get(problem_key, []) and \
                                constraint not in implicit_expr_by_problem[problem_key]:
                            implicit_expr_by_problem[problem_key].append(
                                constraint)

                # Multiple problems, pure endogenous variables
                elif variable.type == var_types['ENDOGENOUS']:

                    # Case of variable used in the problem expressions
                    if var_key in problems_vars.get(problem_key, []):
                        constraint = f"{var_key} >= 0"
                        if constraint not in problems_expressions.get(problem_key, []) and \
                                constraint not in implicit_expr_by_problem[problem_key]:
                            implicit_expr_by_problem[problem_key].append(
                                constraint)

                    else:
                        # If variable not used in problems expressions, raise error
                        used_elsewhere = any(
                            var_key in vars_list
                            for other_key, vars_list in problems_vars.items()
                            if other_key != problem_key
                        )
                        if not used_elsewhere and var_key not in errors:
                            errors.append(var_key)

        if errors:
            msg = (
                "Generation of implicit symbolic expressions failed | "
                f"Non-negative variables '{errors}' not used in any problems "
                "expressions. For these variables, define non-negativity constraints "
                "explicitly, if needed."
            )
            self.logger.error(msg)
            raise exc.ConceptualModelError(msg)

        # Append implicit expressions to symbolic problem
        for problem_key, problem in symbolic_problem.items():
            implicit_expressions = implicit_expr_by_problem.get(
                problem_key, [])

            if expressions_key in problem and \
                    isinstance(problem[expressions_key], list):
                problem[expressions_key].extend(implicit_expressions)
            else:
                problem[expressions_key] = implicit_expressions

    def check_data_tables_and_problem_coherence(self) -> None:
        """Check coherence between symbolic problems and data tables.

        This method checks the coherence between the symbolic problem definitions
        and the data tables definitions in the index. Specific checks include:

        - For hybrid type data tables, table types must be specified for all problems.
        - For variables generated from the same pure endogenous data tables, 
            in case these are used in multiple problems, an error is raised.
            This indeed causes the variable to be reinitialized in the latest 
            problem solved, losing the value assigned in previous problems. 
        - further checks can be added here ...

        Raises:
            exc.ConceptualModelError: If any coherence checks fail.
        """
        self.logger.debug(
            f"Checking coherence between symbolic problems and data tables.")

        source_format = self.settings['model_settings_from']
        data_table_types = Defaults.SymbolicDefinitions.VARIABLE_TYPES
        problems_expressions = self._collect_problems_expressions()

        errors = []

        for table_key, data_table in self.index.data.items():
            data_table: DataTable

            # hybrid type data tables must specify data type for all problems (also
            # in case a variable is not used at all in a specific problem)
            if isinstance(data_table.type, dict):

                valid_problem_keys = set(self.symbolic_problem.keys())
                defined_keys = set(data_table.type.keys())

                # check for invalid keys (typos)
                invalid_keys = defined_keys - valid_problem_keys
                if invalid_keys:
                    errors.append(
                        f"Data table '{table_key}' | Invalid problem keys "
                        f"in type definition: {invalid_keys}."
                    )

                # check for missing problem keys (only if no invalid keys found)
                # QUI DEVO CONTROLLARE SOLO CHE LE VARIABILI SIANO ASSOCIATE AI PROBLEMI
                # NEI QUALI EFFETTIVAMENTE LE VARIABILI VENGONO USATE
                else:
                    missing_keys = valid_problem_keys - defined_keys
                    if missing_keys:
                        errors.append(
                            f"Data table '{table_key}' | Missing type definition "
                            f"for problem keys: {missing_keys}."
                        )

            # pure endogenous variables from same data table used in multiple problems
            if isinstance(self.symbolic_problem, dict):
                if data_table.type == data_table_types['ENDOGENOUS']:

                    for variable in data_table.variables_list:
                        used_in_problems = [
                            problem_key
                            for problem_key, expr_list in problems_expressions.items()
                            if any(
                                var_key == variable
                                for expression in expr_list
                                for var_key in self._get_vars_in_expression(expression).keys()
                            )
                        ]
                        if len(used_in_problems) > 1:
                            errors.append(
                                f"Data table '{table_key}' | Variable '{variable}' | "
                                f"Pure endogenous variable cannot be used in multiple problems: "
                                f"{used_in_problems}."
                            )

        if errors:
            self.logger.error(
                f"Data tables and problems coherence validation report {'=' * 35}")
            for error_msg in errors:
                self.logger.error(f"Validation error | {error_msg}")

            msg = f"Data tables and problems coherence check not successful. " \
                f"Check setup '{source_format}' file. "
            self.logger.error(msg)
            raise exc.ConceptualModelError(msg)

    def find_vars_sets_intra_problem(
        self,
        variables_subset: DotDict,
    ) -> Dict[str, str]:
        """Identify intra-problem sets across a subset of variables.

        Args:
            variables_subset (DotDict): A subset of variables from which to find
                common intra-problem sets.

        Returns:
            Dict[str, str]: A dictionary representing all intra-problem sets (sets 
                names as keys, related table headers as values).
        """
        intra_problem_sets = {}
        for variable in variables_subset.values():
            variable: Variable
            intra_problem_sets.update(
                variable.coordinates_info.get('intra', {})
            )

        return intra_problem_sets

    def find_common_vars_coords(
        self,
        variables_subset: DotDict,
        coord_category: str,
    ) -> Dict[str, List[str]] | None:
        """Find common coordinates across a subset of variables.

        Retrieves and verifies that a specific coordinate category is uniformly
        defined across a subset of variables.
        This method ensures that all variables in the subset have the same settings
        for a specified coordinate category. If the variables do not have uniform
        coordinates, it raises an error.

        Args:
            variables_subset (DotDict): A subset of variables to check for uniform
                coordinate settings.
            coord_category (str): The category of coordinates to check (defined
                in Defaults.SymbolicDefinitions.DIMENSIONS dictionary).

        Returns:
            Dict[str, List[str]] | None: A dictionary of coordinates if uniform
                across the subset; otherwise, raises an error.

        Raises:
            ConceptualModelError: If the coordinates for the specified category are
                not the same across all variables in the subset.
        """
        all_vars_coords = []
        for variable in variables_subset.values():
            variable: Variable
            all_vars_coords.append(
                variable.coordinates.get(coord_category, {})
            )

        vars_coords_dict = {}
        for dictionary in all_vars_coords:
            dictionary: dict

            for set_key, set_items in dictionary.items():

                if set_key in vars_coords_dict:
                    if set(vars_coords_dict[set_key]) != set(set_items):
                        msg = "Passed variables are not defined with same coordinates " \
                            f"for category '{coord_category}'."
                        self.logger.error(msg)
                        raise exc.ConceptualModelError(msg)
                else:
                    vars_coords_dict[set_key] = set_items

        return vars_coords_dict

    def generate_numerical_problems(
            self,
            force_overwrite: bool = False,
    ) -> None:
        """Generate numerical problems from symbolic problem.

        This method generates numerical problems based on the loaded symbolic 
        problem. If symbolic problems are defined for multiple problem keys, 
        the method generates a separate numerical problem for each key. 

        Args:
            force_overwrite (bool, optional): If set to True, existing numerical
                problems will be overwritten without prompting the user for
                confirmation (for testing purposes). Defaults to False.

        Raises:
            exc.OperationalError: If no symbolic problem has been loaded.
            exc.SettingsError: If the symbolic problem structure is invalid.
        """
        with self.logger.log_timing(
            message=f"Generating cvxpy numerical problem/s...",
            level='info',
        ):
            if self.symbolic_problem is None:
                msg = "Symbolic problem must be loaded before generating numerical problems."
                self.logger.error(msg)
                raise exc.OperationalError(msg)

            if self.numerical_problems is not None:
                if not force_overwrite:
                    self.logger.warning("Numerical problem already defined.")
                    if not util.get_user_confirmation("Overwrite numerical problem?"):
                        self.logger.info("Numerical problem NOT overwritten.")
                        return
                else:
                    self.logger.info("Numerical problem overwritten.")
            else:
                self.logger.debug(
                    "Defining cvxpy numerical problems based on symbolic problems.")

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
                self.problem_status = {
                    key: None for key in self.symbolic_problem}

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
        """Generate problem DataFrame from symbolic problem.

        This method generates a DataFrame representing a set of problems based 
        on the provided symbolic problem, including information about each 
        problem's constraints, objective, and status. It also includes a reference 
        to the problem object itself.

        Args:
            symbolic_problem (DotDict): A dictionary-like object containing the
                symbolic representation of the problem.
            problem_key (Optional[int]): An optional key to identify the problem. 
                Defaults to None.

        Returns:
            pd.DataFrame: A DataFrame where each row represents a problem. The
                columns include:
                    'info' (a list of set values defining the problem),
                    'constraints' (a list of constraint expressions),
                    'objective' (the objective expression),
                    'problem' (the cvxpy Problem object),
                    'status' (the solution status, initially set to None).
        """
        headers = {
            'objective': Defaults.Labels.OBJECTIVE,
            'expressions': Defaults.Labels.EXPRESSIONS,
            'problem': Defaults.Labels.PROBLEM,
            'status': Defaults.Labels.PROBLEM_STATUS,
        }

        scenarios_coords_header = Defaults.Labels.SCENARIO_COORDINATES
        list_sets_split_problem = list(
            self.index.sets_split_problem_dict.values())

        problems_df = self.index.scenarios_info.copy()

        for item in headers.values():
            problems_df = util.add_column_to_dataframe(
                dataframe=problems_df,
                column_header=item,
                column_values=None,
            )

        for scenario in problems_df.index:

            scenario_coords = problems_df.loc[
                scenario,
                scenarios_coords_header,
            ]

            if problem_key is not None:
                msg = f"Defining sub-problem '{problem_key}'"
            else:
                msg = "Defining problem"

            if scenario_coords:
                msg += f" for scenario: {scenario_coords}."
            self.logger.debug(msg)

            problem_filter = problems_df.loc[
                [scenario],
                list_sets_split_problem
            ]

            # define problem expressions (user-defined)
            symbolic_expressions = symbolic_problem.get(headers['expressions'])
            expressions = self.define_expressions_list(
                symbolic_expressions=symbolic_expressions,
                problem_filter=problem_filter,
                problem_key=problem_key,
            )

            # define problem objective
            # if not defined, a dummy objective is defined
            symbolic_objective = symbolic_problem.get(
                headers['objective'], None)

            if symbolic_objective:
                # in case of multiple expressions, sum is used as default
                objective = sum(
                    self.define_expressions_list(
                        symbolic_expressions=symbolic_objective,
                        problem_filter=problem_filter,
                        problem_key=problem_key,
                    )
                )
            else:
                objective = cp.Minimize(1)

            problem = cp.Problem(objective, expressions)

            problems_df.at[scenario, headers['objective']] = objective
            problems_df.at[scenario, headers['expressions']] = expressions
            problems_df.at[scenario, headers['problem']] = problem
            problems_df.at[scenario, headers['status']] = None

        return problems_df

    def fetch_allowed_cvxpy_variables(
            self,
            variables_set_dict: Dict[str, Variable],
            problem_filter: pd.DataFrame,
            problem_key: Optional[int] = None,
            set_intra_problem_header: Optional[str] = None,
            set_intra_problem_value: Optional[str] = None,
    ) -> Dict[str, cp.Parameter | cp.Variable]:
        """Fetch allowed cvxpy variables based on problem filters.

        Fetches allowed cvxpy variables from a passed set of Variables instances 
        based on specific problem filters and conditions.

        Args:
            variables_set_dict (Dict[str, Variable]): A dictionary mapping variable
                names to Variable objects. 
            problem_filter (pd.DataFrame): A DataFrame containing filter criteria
                to apply to the variables, to precisely identify specific cvxpy 
                variables among different scenarios defined by inter-problem sets.
            problem_key (Optional[int], optional): An optional key to identify
                the numerical problem. Defaults to None.
            set_intra_problem_header (Optional[str], optional): The header name
                within the problem filter that specifies intra-problem distinctions.
                Defaults to None.
            set_intra_problem_value (Optional[str], optional): The specific value
                within the set_intra_problem_header to filter on. Defaults to None.

        Returns:
            Dict[str, Union[cp.Parameter, cp.Variable]]: A dictionary mapping variable
                names to their corresponding allowed CVXPY Parameter or Variable objects.

        Raises:
            exc.MissingDataError: If variable data is not defined for any variable.

            exc.ConceptualModelError: If a unique cvxpy variable cannot be identified
                for the problem due to ambiguous or insufficient filter criteria
                or if no appropriate cvxpy variable can be fetched for an
                intra-problem set.
        """
        allowed_variables = {}
        cvxpy_var_header = Defaults.Labels.CVXPY_VAR
        allowed_var_types = Defaults.SymbolicDefinitions.VARIABLE_TYPES

        for var_key, variable in variables_set_dict.items():
            variable: Variable

            if variable.data is None:
                msg = f"Variable data not defined for variable '{var_key}'"
                self.logger.error(msg)
                raise exc.MissingDataError(msg)

            # constants are directly assigned
            if variable.type == allowed_var_types['CONSTANT']:
                allowed_variables[var_key] = variable.data
                continue

            if isinstance(variable.data, dict):
                if problem_key is not None:
                    variable_data = variable.data[problem_key]
                else:
                    msg = "Problem key must be provided in case variables type " \
                        "is dependent by the problem."
                    self.logger.error(msg)
                    raise exc.SettingsError(msg)
            else:
                variable_data = variable.data

            # filter variable data based on problem filter (inter-problem sets)
            # if variable is defined for the current inter-problem sets, filter the variable data
            # if variable is defined for a sub set of inter-problem sets, finter the sub-set only
            # else, skip
            if not problem_filter.empty:
                if not set(problem_filter.columns).isdisjoint(variable_data.columns):
                    common_filter_cols = problem_filter.columns.intersection(
                        variable_data.columns
                    )
                    problem_filter_intersection = problem_filter[common_filter_cols]

                    variable_data = pd.merge(
                        left=variable_data,
                        right=problem_filter_intersection,
                        on=list(problem_filter_intersection.columns),
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
                        f"'{var_key}' based on the current problem filter."
                    self.logger.error(msg)
                    raise exc.ConceptualModelError(msg)

            # if sets_intra_problem is defined for the variable, the right
            # cvxpy variable is fetched for the current problem.
            # intra problem sets may be different for each variable
            elif variable.coordinates_info['intra'] \
                    and set_intra_problem_header and set_intra_problem_value:

                # filter only the headers that are in the intra-problem sets
                intra_values = set(variable.coordinates_info['intra'].values())

                filtered_header_value_pairs = [
                    (header, value)
                    for header, value
                    in zip(set_intra_problem_header, set_intra_problem_value)
                    if header in intra_values
                ]

                if not filtered_header_value_pairs:
                    msg = "No intra-problem sets found for variable " \
                        f"'{var_key}' based on the current problem filter."
                    self.logger.error(msg)
                    raise exc.ConceptualModelError(msg)

                filtered_header, filtered_value = map(
                    list, zip(*filtered_header_value_pairs)
                )

                conditions = [
                    variable_data[header] == value
                    for header, value in zip(filtered_header, filtered_value)
                ]
                condition = np.logical_and.reduce(conditions)

                allowed_variables[var_key] = variable_data.loc[
                    condition, cvxpy_var_header].iloc[0]

            # other cases
            else:
                msg = f"Unable to fetch cvxpy variable for variable {var_key}."
                self.logger.error(msg)
                raise exc.ConceptualModelError(msg)

        return allowed_variables

    def execute_cvxpy_code(
            self,
            expression: str,
            allowed_variables: Dict[str, cp.Parameter | cp.Variable],
            allowed_operators: Optional[Dict[str, str]] = None
    ) -> Any:
        """Execute literal expression to generate cvxpy expression.

        This method executes a literal expression to generate a cvxpy expression.
        The function uses the 'exec' function in a restricted environment to 
        prevent security risks. Only predefined variables and operators can be 
        used in the expression.

        Args:
            expression (str): The literal expression to be evaluated as a string.
            allowed_variables (Dict[str, Union[cp.Parameter, cp.Variable]]): A
                dictionary mapping variable names to their corresponding cvxpy objects.
            allowed_operators (Dict[str, str], optional): A dictionary mapping
                operator names to be executed as functions. Defaults to None.

        Returns:
            Any: The result of the evaluated symbolic expression.

        Raises:
            exc.NumericalProblemError: If there is a syntax error in the expression,
                or if the expression contains undefined names not included in
                the allowed variables or operators.
        """
        local_vars = {}
        if allowed_operators is None:
            allowed_operators = Defaults.SymbolicDefinitions.ALLOWED_OPERATORS

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
            error = f'NameError in reading literal expression: {msg}'
            self.logger.error(error)
            raise exc.NumericalProblemError(error) from msg

        return local_vars['output']

    def define_expressions_list(
            self,
            symbolic_expressions: List[str],
            problem_filter: pd.DataFrame,
            problem_key: Optional[int] = None,
    ) -> List[cp.Expression]:
        """Define a list of cvxpy expressions from symbolic definitions.

        This method constructs a list of cvxpy expressions based on symbolic problem
        definitions. It processes each symbolic expression, identifies the relevant
        variables, and constructs the corresponding cvxpy expressions. The method
        handles intra-problem sets distinctions by dynamically constructing
        expressions based on available data.

        Args:
            symbolic_expressions (List[str]): A list of symbolic expressions to be
                converted into cvxpy expressions.
            problem_filter (pd.DataFrame): A DataFrame used to filter relevant
                variables for constructing the expressions.
            problem_key (Optional[int], optional): An optional key to identify
                the problem. Defaults to None.

        Returns:
            List[cp.Expression]: A list of cvxpy expressions that have been dynamically
                constructed based on the input parameters.

        Raises:
            MissingDataError: If no symbolic expressions are passed or if set data 
                for a specific set is not defined.
            NumericalProblemError: If a cvxpy expression cannot be generated for a
                specific symbolic expression.
        """
        numerical_expressions = []

        text_pattern = Defaults.SymbolicDefinitions.TOKEN_PATTERNS['text']
        allowed_var_types = Defaults.SymbolicDefinitions.VARIABLE_TYPES
        allowed_operators = list(
            Defaults.SymbolicDefinitions.ALLOWED_OPERATORS.keys())

        if symbolic_expressions is []:
            msg = "No symbolic expressions have passed. Check symbolic problem."
            self.logger.error(msg)
            raise exc.MissingDataError(msg)

        expressions_not_generated = []

        for expression in symbolic_expressions:

            self.logger.debug(
                f"Processing literal expression | '{expression}'")
            cvxpy_expression = None

            vars_symbols_list = util_text.extract_tokens_from_expression(
                expression=expression,
                pattern=text_pattern,
                tokens_to_skip=allowed_operators,
            )

            vars_subset = DotDict({
                key: variable for key, variable in self.index.variables.items()
                if key in vars_symbols_list
                and variable.type != allowed_var_types['CONSTANT']
            })

            constants_subset = DotDict({
                key: variable for key, variable in self.index.variables.items()
                if key in vars_symbols_list
                and variable.type == allowed_var_types['CONSTANT']
            })

            sets_intra_problem = self.find_vars_sets_intra_problem(
                variables_subset=vars_subset,
            )

            # case of no intra-problem sets
            if not sets_intra_problem:
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

            # case of one or more intra-problem sets
            else:
                # check for common filtered intra-problem set coordinates
                sets_intra_problem_coords = self.find_common_vars_coords(
                    variables_subset=vars_subset,
                    coord_category='intra',
                )

                # if filtered intra-problem set coordinates are not defined
                if not sets_intra_problem_coords:
                    continue

                # substitute set keys with headers
                sets_intra_problem_coords = util.substitute_dict_keys(
                    source_dict=sets_intra_problem_coords,
                    key_mapping_dict=sets_intra_problem,
                )

                # define all possible combinations of intra-problem set values
                sets_intra_problem_coords_combinations = util.dict_cartesian_product(
                    data_dict=sets_intra_problem_coords,
                    include_dict_keys=True,
                )

                # define one expression for each combination of intra-problem set values
                for sets_combination in sets_intra_problem_coords_combinations:
                    sets_headers = list(sets_combination.keys())
                    sets_data = list(sets_combination.values())

                    # fetch allowed cvxpy variables
                    allowed_variables = self.fetch_allowed_cvxpy_variables(
                        variables_set_dict={
                            **vars_subset, **constants_subset},
                        problem_filter=problem_filter,
                        problem_key=problem_key,
                        set_intra_problem_header=sets_headers,
                        set_intra_problem_value=sets_data,
                    )

                    # define expression
                    cvxpy_expression = self.execute_cvxpy_code(
                        expression=expression,
                        allowed_variables=allowed_variables,
                    )

                    numerical_expressions.append(cvxpy_expression)

            if cvxpy_expression is None:
                expressions_not_generated.append(expression)

        if expressions_not_generated != []:
            self.logger.error(
                f"'{len(expressions_not_generated)}' CVXPY expressions not "
                "generated. Expressions: "
            )
            for expression in expressions_not_generated:
                self.logger.error(f"{expression}")
            raise exc.NumericalProblemError(
                f"Failed to generate '{len(expressions_not_generated)}' CVXPY expressions.")

        return numerical_expressions

    def solve_problem_dataframe(
            self,
            problem_dataframe: pd.DataFrame,
            problem_name: Optional[str] = None,
            scenarios_idx: Optional[List[int] | int] = None,
            **solver_settings: Any,
    ) -> None:
        """Solve numerical problems defined in problem DataFrame.

        This method solves the optimization problem defined in the problem DataFrame.
        This method iterates over the rows of the input DataFrame, each of which
        represents a problem. It logs the process, solves the problem using the
        specified solver, and updates the problem's status in the DataFrame.

        Args:
            problem_dataframe (pd.DataFrame): A DataFrame where each row represents 
                a problem. The columns include 'info' (a list of set values defining 
                the problem), 'problem' (the cvxpy Problem object), and 'status' 
                (the solution status).
            problem_name (Optional[str], optional): An optional name for the problem.
                Useful for logging purpose. Defaults to None.
            verbose (Optional[bool], optional): If set to True, the solver will
                print progress information. If verbose is set to False, UserWarnings 
                from the 'cvxpy.reductions.solvers.solving_chain' module are suppressed.
                Defaults to True.
            solver (Optional[str], optional): The solver to use. If None, cvxpy
                will choose a solver automatically. Defaults to None.
            **kwargs (Any): Additional arguments to pass to the solver.
        """
        if solver_settings['verbose'] == False:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
            warnings.filterwarnings(
                'ignore',
                category=UserWarning,
                module='cvxpy.reductions.solvers.solving_chain'
            )

        scenarios_info_header = Defaults.Labels.SCENARIO_COORDINATES
        problem_header = Defaults.Labels.PROBLEM
        status_header = Defaults.Labels.PROBLEM_STATUS

        if scenarios_idx is None:
            scenarios_idx = list(self.index.scenarios_info.index)
        elif isinstance(scenarios_idx, int):
            scenarios_idx = [scenarios_idx]
        else:
            util.items_in_list(
                items=scenarios_idx,
                control_list=list(self.index.scenarios_info.index),
            )

        for scenario in scenarios_idx:

            scenario_info: List[str] = problem_dataframe.at[
                scenario, scenarios_info_header]

            cvxpy_problem: cp.Problem = problem_dataframe.at[
                scenario, problem_header]

            if problem_name is not None:
                msg = f"Solving cvxpy sub-problem '{problem_name}'"
            else:
                msg = "Solving cvxpy problem"

            if scenario_info:
                msg += f" | Scenario {scenario_info}."

            self.logger.info(msg)

            cvxpy_problem.solve(**solver_settings)

            self.logger.info(f"Problem status: '{cvxpy_problem.status}'")

            problem_dataframe.at[scenario, status_header] = \
                cvxpy_problem.status

    def fetch_problem_status(self) -> None:
        """Fetch the status of all numerical problems.

        Raises:
            OperationalError: If the numerical problems are not defined.
        """
        if self.numerical_problems is None:
            msg = "Numerical problems have not yet defined."
            self.logger.warning(msg)
            raise exc.OperationalError(msg)

        status_header = Defaults.Labels.PROBLEM_STATUS
        scenario_header = Defaults.Labels.SCENARIO_COORDINATES

        if isinstance(self.numerical_problems, pd.DataFrame):
            problem_df = self.numerical_problems

            problem_status = {
                f'Scenario {info}'
                if len(problem_df) > 1 else '': status
                for info, status
                in zip(problem_df[scenario_header], problem_df[status_header])
            }

        elif isinstance(self.numerical_problems, dict):

            problem_status = {
                f'Sub-problem [{sub_problem_key}]' +
                (f' - Scenario {info}' if len(problem_df) > 1 else ''): status
                for sub_problem_key, problem_df in self.numerical_problems.items()
                for info, status
                in zip(problem_df[scenario_header], problem_df[status_header])
            }

        self.problem_status = problem_status

    def __repr__(self):
        """Return a string representation of the Problem instance."""
        class_name = type(self).__name__
        return f'{class_name}'
