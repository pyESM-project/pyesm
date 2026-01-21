"""Module defining the Core class.

The Core class serves as the central management point for the CVXlab package
and orchestrates the interactions among Index (embedding all information about
data tables and variables), Database (handling SQLite database operations, using
SQLManager), and Problem (defining symbolic and numerical problems).
"""
import os
from typing import Any, Dict, List, Optional
from pathlib import Path

import numpy as np
import pandas as pd
import cvxpy as cp

from cvxlab.backend.data_table import DataTable
from cvxlab.backend.database import Database
from cvxlab.backend.index import Index, Variable
from cvxlab.backend.problem import Problem
from cvxlab.log_exc import exceptions as exc
from cvxlab.log_exc.logger import Logger
from cvxlab.defaults import Defaults
from cvxlab.support import util
from cvxlab.support.file_manager import FileManager
from cvxlab.support.sql_manager import SQLManager, db_handler


class Core:
    """Core class defines the interactions among main components of the package.

    The Core class generates instances of Index (with all the information about 
    sets, data tables and variables), SQLManager (with all the tools necessary 
    to handle SQLite database), Database (handling all database operations), and 
    Problem (defining symbolic and numerical problems). It manages the interactions
    among these components, including data fetching and writing to the database,
    variable initialization, problem definition and solving.
    It also provides methods for initializing variables, loading and validating
    symbolic problems, generating numerical problems, and solving both individual
    and integrated problems.

    Attributes:

    - logger (Logger): Logger object for logging information.
    - files (FileManager): FileManager object for file operations.
    - settings (Dict[str, str]): Settings for various file paths and configurations.
    - paths (Dict[str, Path]): Paths to various directories and files used in the model.
    - sqltools (SQLManager): SQLManager object for database interactions.
    - index (Index): Index object for managing data table and variable indices.
    - database (Database): Database object for database operations.
    - problem (Problem): Problem object for problem definitions and operations.

    """

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            settings: Dict[str, str],
            paths: Dict[str, Path],
    ):
        """Initialize the Core class with logger, files, settings and paths.

        Args:
            logger (Logger): An instance of Logger for logging information and
                error messages.
            files (FileManager): An instance of FileManager for managing
                file-related operations.
            settings (Dict[str, str]): A dictionary containing configuration
                settings for the application.
            paths (Dict[str, Path]): A dictionary containing paths used throughout
                operations, such as for files and directories.
        """
        self.logger = logger.get_child(__name__)
        self.files = files
        self.settings = settings
        self.paths = paths

        self.sqltools = SQLManager(
            logger=self.logger,
            database_path=self.paths['sqlite_database'],
            database_name=Defaults.ConfigFiles.SQLITE_DATABASE_FILE,
        )

        self.index = Index(
            logger=self.logger,
            files=self.files,
            settings=self.settings,
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

    def initialize_problems_variables(self) -> None:
        """Initialize data structures for handling problem variables.

        This method first iterates over each endogenous data table, generating 
        the coordinate dataframe and the related cvxpy variable in the data table 
        object (cvxpy variable in endogenous data tables include all data tables 
        entries that will be then sliced to be used in the problem). 
        It then iterates over all variables in the index, generating the variable's
        dataframe (including all variables information and the related cvxpy variable)
        in Problem object.

        Raises:
            SettingsError: If a variable's type is not of the allowed type.
        """
        allowed_var_types = Defaults.SymbolicDefinitions.VARIABLE_TYPES

        with self.logger.log_timing(
            message=f"Generating data structures for endogenous data tables...",
            level='info',
        ):
            # generate dataframes and cvxpy var for endogenous data tables
            # and for variables with type defined by problem linking logic
            for data_table_key, data_table in self.index.data.items():
                data_table: DataTable

                is_endogenous = data_table.type == allowed_var_types['ENDOGENOUS']
                is_hybrid = isinstance(data_table.type, dict)

                if not (is_endogenous or is_hybrid):
                    continue

                data_table_type = allowed_var_types['ENDOGENOUS'] if is_endogenous else 'hybrid'

                self.logger.debug(
                    f"Generating data structure | Type: {data_table_type} | "
                    f"Data table '{data_table_key}'")

                # get all coordinates for the data table based on sets
                data_table.generate_coordinates_dataframes(
                    sets_split_problems=self.index.sets_split_problem_dict
                )

                # data table coordinates dataframe are filtered to keep only
                # coordinates defined by the variables whithin the data table
                coordinates_df_filtered = pd.DataFrame()
                for var_key, variable in self.index.variables.items():
                    if var_key in data_table.variables_list:
                        var_coords_df = util.unpivot_dict_to_dataframe(
                            data_dict=variable.all_coordinates_w_headers
                        )
                        coordinates_df_filtered = pd.concat(
                            objs=[coordinates_df_filtered, var_coords_df],
                            ignore_index=True
                        )

                coordinates_df_filtered = coordinates_df_filtered.drop_duplicates()

                if isinstance(data_table.coordinates_dataframe, pd.DataFrame):
                    data_table.coordinates_dataframe = \
                        data_table.coordinates_dataframe.merge(
                            right=coordinates_df_filtered,
                            on=list(coordinates_df_filtered.columns),
                            how='inner'
                        )

                elif isinstance(data_table.coordinates_dataframe, dict):
                    for problem_key, coord_df in \
                            data_table.coordinates_dataframe.items():

                        coord_df: pd.DataFrame
                        data_table.coordinates_dataframe[problem_key] = \
                            coord_df.merge(
                                right=coordinates_df_filtered,
                                on=list(coordinates_df_filtered.columns),
                                how='inner'
                        )

                # generate cvxpy variables associated with data tables
                if isinstance(data_table.coordinates_dataframe, pd.DataFrame):
                    cvxpy_var = self.problem.create_cvxpy_variable(
                        var_type=allowed_var_types['ENDOGENOUS'],
                        integer=data_table.integer,
                        shape=(data_table.table_length, 1),
                        name=data_table_key,
                    )

                # in case of problem with sets split, multiple endogenous variables
                # are created and stored in a dictionary.
                elif isinstance(data_table.coordinates_dataframe, dict):
                    cvxpy_var = {}

                    for problem_key, coord_df in data_table.coordinates_dataframe.items():
                        cvxpy_var[problem_key] = self.problem.create_cvxpy_variable(
                            var_type=allowed_var_types['ENDOGENOUS'],
                            integer=data_table.integer,
                            shape=(len(coord_df), 1),
                            name=f"{data_table_key}_{problem_key}",
                        )

                data_table.cvxpy_var = cvxpy_var

        # generating variables dataframes with cvxpy var and filters dictionary
        # (endogenous vars will be sliced from existing cvxpy var in data table)
        with self.logger.log_timing(
            message=f"Generating data structures for all variables and constants...",
            level='info',
        ):
            for var_key, variable in self.index.variables.items():
                variable: Variable

                # for constants, values are directly generated (no dataframes needed)
                if variable.type == allowed_var_types['CONSTANT']:

                    self.logger.debug(
                        f"Generating data structure | Type: {variable.type} | "
                        f"Variable '{var_key}' | Value: '{variable.value}'")

                    variable.data = self.problem.generate_constant_data(
                        variable_key=var_key,
                        variable=variable
                    )

                # for variables whose type is univocally defined, only one data structure
                # is generated and stored in variable.data
                elif variable.type in [
                    allowed_var_types['EXOGENOUS'],
                    allowed_var_types['ENDOGENOUS']
                ]:
                    self.logger.debug(
                        f"Generating data structure | Type: {variable.type} | "
                        f"Variable '{var_key}'")

                    variable.data = self.problem.generate_vars_dataframe(
                        variable_key=var_key,
                        variable=variable
                    )

                # for variable whose type varies depending on the problem, both
                # endogenous/exogenous variable dataframes are stored in
                # variable.data defined as a dictionary
                elif isinstance(variable.type, dict):
                    variable.data = {}

                    self.logger.debug(
                        f"Generating data structure | Type: hybrid | "
                        f"Variable '{var_key}'")

                    for problem_key, problem_var_type in variable.type.items():
                        variable.data[problem_key] = self.problem.generate_vars_dataframe(
                            variable_key=var_key,
                            variable=variable,
                            variable_type=problem_var_type,
                        )

                else:
                    msg = f"Variable type '{variable.type}' not allowed. Available " \
                        f"types: {list(allowed_var_types.values())}"
                    self.logger.error(msg)
                    raise exc.SettingsError(msg)

    def data_to_cvxpy_exogenous_vars(
            self,
            scenarios_idx: Optional[List[int] | int] = None,
            allow_none_values: bool = True,
            var_list_to_update: List[str] = [],
            filter_negative_values: bool = False,
            warnings_on_negatives: bool = False,
            validate_types: bool = True,
    ) -> None:
        """Fetch data from the database and assign it to cvxpy exogenous variables.

        This method iterates over each exogenous variable in the Index, getting 
        related data from the SQLite database and assigns it to the cvxpy variable.
        The method handles variables whose type is defined by the problem separately.
        The method can fetch data for all scenarios or for a subset of scenarios 
        (scenarios_idx): scenarios are linear combinations of inter-problem sets 
        values defined in the index. 
        The method can update all exogenous variables or a specified list of variables 
        (var_list_to_update): this may be useful for continuous user model run, 
        when only a subset of exogenous variables need to be updated.
        Optionally, the method can check if variable data comply with nonneg attribute
        defined for the variable, putting negative values to zero.

        Args:
            scenarios_idx (Optional[List[int] | int], optional): List of indices
                of scenarios for which to fetch data. If None, fetches data for
                all scenarios. Defaults to None.
            allow_none_values (bool, optional): If True, allows None values in
                the data for the variable. Defaults to True.
            var_list_to_update (List[str], optional): List of variable keys to
                update. If empty, updates all exogenous variables. Defaults to [].
            filter_negative_values (bool, optional): If True, checks
                if variable data comply with nonneg attribute defined for the
                variable, putting negative values to zero. Defaults to False.
            warnings_on_negatives (bool, optional): If True, logs warnings when
                negative values are found and filtered out. Defaults to False.
            validate_types (bool, optional): If True, validates the types of
                the data against allowed types. Defaults to True.

        Raises:
            TypeError: If 'var_list_to_update' is not a list.
            SettingsError: If one or more items in 'var_list_to_update' are not
                in the index variables.
            MissingDataError: If no data or related table is defined for a variable,
                or if the data for a variable contains non-allowed values types.
        """
        with self.logger.log_timing(
            message=f"Fetching data from '{self.settings['sqlite_database_file']}' "
                "to cvxpy exogenous variables...",
            level='info',
        ):
            filter_header = Defaults.Labels.FILTER_DICT_KEY
            cvxpy_var_header = Defaults.Labels.CVXPY_VAR
            values_header = Defaults.Labels.VALUES_FIELD['values'][0]
            id_header = Defaults.Labels.ID_FIELD['id'][0]
            allowed_values_types = Defaults.NumericalSettings.ALLOWED_VALUES_TYPES
            allowed_var_types = Defaults.SymbolicDefinitions.VARIABLE_TYPES

            if not isinstance(var_list_to_update, list):
                msg = "Passed method parameter must be a list."
                self.logger.error(msg)
                raise TypeError(msg)

            if not var_list_to_update == [] and \
                    not util.items_in_list(var_list_to_update, self.index.variables.keys()):
                msg = "One or more passed items are not in the index variables."
                self.logger.error(msg)
                raise exc.SettingsError(msg)

            if var_list_to_update == []:
                var_list_to_update = self.index.list_variables

            with db_handler(self.sqltools):
                for var_key, variable in self.index.variables.items():
                    variable: Variable

                    var_sing_data_update = False
                    var_has_negatives = False

                    if var_key not in var_list_to_update:
                        continue

                    if variable.type in [
                        allowed_var_types['ENDOGENOUS'],
                        allowed_var_types['CONSTANT']
                    ]:
                        continue

                    self.logger.debug(
                        f"Fetching data to variables | Variable '{var_key}'")

                    err_msg = []

                    if variable.data is None:
                        err_msg.append(
                            "Fetching data to variables | No data defined for "
                            f"variable '{var_key}'.")
                    if variable.related_table is None:
                        err_msg.append(
                            "Fetching data to variables | No related table "
                            f"defined for variable '{var_key}'.")
                    if err_msg:
                        [self.logger.error(msg) for msg in err_msg]
                        raise exc.MissingDataError(
                            "Fetching data to variables | Failed.")

                    # for variables whose type is end/exo depending on the problem,
                    # fetch exogenous variable data.
                    # notice that a variable may be exogenous for more than one problem.
                    if isinstance(variable.type, dict):
                        problem_keys = util.find_dict_keys_corresponding_to_value(
                            variable.type, allowed_var_types['EXOGENOUS'])
                    else:
                        problem_keys = [None]

                    for problem_key in problem_keys:

                        if problem_key is not None:
                            variable_data = variable.data[problem_key]
                        else:
                            variable_data = variable.data

                        # case when all values of variables need to be fetched
                        if scenarios_idx is None:
                            sets_parsing_hierarchy_idx = list(
                                variable_data.index)

                        # case when values of variables need to be fetched for a
                        # sub-set of inter-problem sets defined by scenarios_idx
                        # (typically when solving integrated problems)
                        else:
                            if isinstance(scenarios_idx, int):
                                scenarios_idx = [scenarios_idx]

                            # case of variable not defined for any inter-problem sets
                            if not variable.coordinates['inter']:
                                sets_parsing_hierarchy_idx = \
                                    list(variable_data.index)

                            # case of variable defined for one or more inter-problem sets
                            # find the index of variable_data that matches the combination
                            # of inter-problem-sets defined by scenarios_idx
                            else:
                                info_label = Defaults.Labels.SCENARIO_COORDINATES
                                scenarios_to_fetch = \
                                    self.index.scenarios_info.loc[scenarios_idx].drop(
                                        columns=[info_label]
                                    )

                                var_inter_set_headers = list(
                                    variable.coordinates_info['inter'].values()
                                )

                                variable_data = variable_data.reset_index()

                                variable_data_filtered = variable_data.merge(
                                    right=scenarios_to_fetch,
                                    on=var_inter_set_headers,
                                    how='inner'
                                ).set_index('index')

                                sets_parsing_hierarchy_idx = \
                                    list(variable_data_filtered.index)

                        for combination in sets_parsing_hierarchy_idx:
                            # get raw data from database
                            raw_data = self.database.sqltools.table_to_dataframe(
                                table_name=variable.related_table,
                                filters_dict=variable_data[filter_header][combination]
                            )

                            if validate_types:
                                # check if variable data are int or float
                                non_allowed_ids = util.find_non_allowed_types(
                                    dataframe=raw_data,
                                    allowed_types=allowed_values_types,
                                    target_col_header=values_header,
                                    return_col_header=id_header,
                                    allow_none=allow_none_values,
                                )

                                if non_allowed_ids:
                                    if len(non_allowed_ids) > 5:
                                        non_allowed_ids = non_allowed_ids[:5] + \
                                            [f"(total items {len(non_allowed_ids)})"]
                                    msg = f"Data for variable '{var_key}' in table " \
                                        f"'{variable.related_table}' contains " \
                                        f"non-allowed values types in rows: " \
                                        f"{non_allowed_ids}."
                                    self.logger.error(msg)
                                    raise exc.MissingDataError(msg)

                            # optionally, check if variable raw_data comply with sign
                            # constraints defined for the variable, eventually putting
                            # non-complying values to zero. This may be useful for
                            # solving integrated problems iteratively, when small
                            # negative values may appear due to numerical errors.
                            if filter_negative_values:
                                # Only apply when the variable is hybrid and has a sign constraint
                                if isinstance(variable.type, dict) and \
                                        variable.nonneg is True:

                                    original_df = raw_data.copy()

                                    raw_data = util.filter_non_allowed_negatives(
                                        dataframe=raw_data,
                                        column_header=values_header,
                                    )
                                    if not util.check_dataframes_equality(
                                        df_list=[original_df, raw_data],
                                        homogeneous_num_types=True,
                                    ):
                                        var_sing_data_update = True
                                else:
                                    pass

                            # optionally, log warnings on negative values found
                            if warnings_on_negatives:
                                if values_header in raw_data.columns:
                                    if (raw_data[values_header] < 0).any():
                                        var_has_negatives = True

                            # pivoting and reshaping data to fit variables
                            pivoted_data = variable.reshaping_normalized_table_data(
                                var_key=var_key,
                                data=raw_data,
                            )

                            self.problem.data_to_cvxpy_variable(
                                var_key=var_key,
                                cvxpy_var=variable_data[cvxpy_var_header][combination],
                                data=pivoted_data
                            )

                    if var_sing_data_update:
                        self.logger.warning(
                            f"Negative values set to zero for variable '{var_key}'")

                    if var_has_negatives:
                        self.logger.warning(
                            f"Negative values found for variable '{var_key}'")

    def cvxpy_endogenous_data_to_database(
            self,
            scenarios_idx: Optional[List[int] | int] = None,
            force_overwrite: bool = False,
            suppress_warnings: bool = False,
    ) -> None:
        """Export data from cvxpy endogenous variables to the SQLite database.

        This method iterates over each endogenous data table in the Index, and it
        exports the data from the related cvxpy variable into the corresponding 
        data table in the SQLite database. 
        The method can export data for all scenarios or for a subset of scenarios
        (scenarios_idx): scenarios are linear combinations of inter-problem sets
        values defined in the index.
        The method can optionally suppress warnings during the export process (
        force_overwrite, useful for testing purpose).
        The method can optionally force the re-export of data even if the data
        table already exists (suppress_warnings, useful for continuous user model
        run, when only a subset of endogenous variables need to be exported).

        Args:
            scenarios_idx (Optional[List[int] | int], optional): List of indices
                of scenarios for which to fetch data. If None, fetches data for
                all scenarios. Defaults to None.
            force_overwrite (bool, optional): If True, forces the re-export of 
                data even if the data table already exists. Defaults to False.
            suppress_warnings (bool, optional): If True, suppresses warnings 
                during the data export process. Defaults to False.
        """
        self.logger.debug(
            "Exporting data from cvxpy endogenous variable (in data table) "
            f"to SQLite database '{self.settings['sqlite_database_file']}' ")

        values_headers = Defaults.Labels.VALUES_FIELD['values'][0]
        allowed_var_types = Defaults.SymbolicDefinitions.VARIABLE_TYPES

        if scenarios_idx is None:
            scenarios_list = list(self.index.scenarios_info.index)
        else:
            if isinstance(scenarios_idx, int):
                scenarios_list = [scenarios_idx]
            elif isinstance(scenarios_idx, list):
                scenarios_list = scenarios_idx
            else:
                msg = "'scenarios_idx' parameter must be an int or a list of ints."
                self.logger.error(msg)
                raise TypeError(msg)

        with db_handler(self.sqltools):
            for data_table_key, data_table in self.index.data.items():
                data_table: DataTable

                if data_table.type in [
                    allowed_var_types['EXOGENOUS'],
                    allowed_var_types['CONSTANT']
                ]:
                    continue

                if isinstance(data_table.coordinates_dataframe, pd.DataFrame):
                    data_table_dataframe = data_table.coordinates_dataframe

                elif isinstance(data_table.coordinates_dataframe, dict):
                    dataframes_list = [
                        dataframe for df_key, dataframe
                        in data_table.coordinates_dataframe.items()
                        if df_key in scenarios_list
                    ]
                    data_table_dataframe = pd.concat(
                        objs=dataframes_list,
                        ignore_index=True
                    )

                data_table_dataframe = util.add_column_to_dataframe(
                    dataframe=data_table_dataframe,
                    column_header=values_headers,
                )

                if values_headers not in data_table_dataframe.columns:
                    if self.settings['log_level'] == 'debug' or \
                            not suppress_warnings:
                        self.logger.warning(
                            f"Column '{values_headers}' already exists in data "
                            f"table '{data_table_key}'")

                if data_table.cvxpy_var is None:
                    if self.settings['log_level'] == 'debug' or \
                            not suppress_warnings:
                        self.logger.warning(
                            f"No data available in cvxpy variable '{data_table_key}'")
                    continue

                cvxpy_var_with_nones = False

                if isinstance(data_table.cvxpy_var, dict):
                    cvxpy_var_values_list = []

                    for cvxpy_var_key, cvxpy_var in data_table.cvxpy_var.items():
                        cvxpy_var: cp.Variable

                        if cvxpy_var_key not in scenarios_list:
                            continue

                        if cvxpy_var.value is None:
                            cvxpy_var_with_nones = True
                            value_to_append = np.zeros((cvxpy_var.shape[0], 1))
                        else:
                            value_to_append = cvxpy_var.value

                        cvxpy_var_values_list.append(value_to_append)
                    cvxpy_var_data = np.vstack(cvxpy_var_values_list)

                else:
                    if data_table.cvxpy_var.value is None:
                        cvxpy_var_with_nones = True
                        value_to_append = np.zeros(
                            (data_table.cvxpy_var.shape[0], 1))
                    else:
                        value_to_append = data_table.cvxpy_var.value

                    cvxpy_var_data = value_to_append

                if cvxpy_var_with_nones:
                    self.logger.warning(
                        f"Data table '{data_table_key}' | "
                        "No data available in cvxpy variable (probably not "
                        "used in model expressions). Exporting zeros to corresponding "
                        "SQLite data table."
                    )

                if len(data_table_dataframe) != cvxpy_var_data.shape[0]:
                    self.logger.error(
                        f"Length mismatch exporting '{data_table_key}': "
                        f"dataframe rows={len(data_table_dataframe)}, "
                        f"cvxpy rows={cvxpy_var_data.shape[0]}"
                    )
                    raise exc.OperationalError(
                        "Mismatch between coordinates and cvxpy values length.")

                data_table_dataframe[values_headers] = cvxpy_var_data

                self.sqltools.dataframe_to_table(
                    table_name=data_table_key,
                    dataframe=data_table_dataframe,
                    action='update',
                    force_overwrite=force_overwrite,
                    suppress_warnings=suppress_warnings,
                )

    def check_exogenous_data_coherence(self) -> None:
        """Check coherence of exogenous data in the SQLite database.

        The method parses all exogenous data tables in the Database, checking 
        for NULL entries in the 'values' column. Since all exogenous data are 
        expected to be filled by the user before running the model, in case NULL 
        entries are found, the method logs the table name and the corresponding 
        row IDs, and raises an error.

        Raises:
            exc.MissingDataError: If NULL entries are found in any data table.
        """
        with self.logger.log_timing(
            message=f"Checking exogenous data coherence...",
            level='info',
        ):
            null_entries = {}
            column_to_inspect = Defaults.Labels.VALUES_FIELD['values'][0]
            column_with_info = Defaults.Labels.ID_FIELD['id'][0]
            allowed_var_types = Defaults.SymbolicDefinitions.VARIABLE_TYPES

            with db_handler(self.sqltools):
                for table_name, data_table in self.index.data.items():
                    data_table: DataTable

                    if data_table.type in (
                        allowed_var_types['ENDOGENOUS'],
                        allowed_var_types['CONSTANT']
                    ):
                        continue

                    null_list = self.sqltools.get_null_values(
                        table_name=table_name,
                        column_to_inspect=column_to_inspect,
                        column_with_info=column_with_info,
                    )

                    if null_list:
                        null_entries[table_name] = null_list

            if null_entries:
                for table, rows in null_entries.items():
                    if len(rows) > 5:
                        rows = rows[:5] + [f"(total items {len(rows)})"]
                    self.logger.error(
                        f"Data coherence check | Table '{table}' | "
                        f"NULLs at id rows: {rows}."
                    )
                raise exc.MissingDataError(
                    "Data coherence check | NULL entries found in "
                    f"data tables: {list(null_entries.keys())}"
                )

    def load_and_validate_symbolic_problem(
            self,
            force_overwrite: bool = False,
    ) -> None:
        """Call methods to load and validate symbolic problem.

        The method calls the 'load_symbolic_problem_from_file' and complete the 
        problem expressions by adding implicit symbolic expressions using the 
        'add_implicit_symbolic_expressions' (i.e. defining expressions for variables
        with sign constraints defined in settings). Then, it calls the 
        'validate_symbolic_expressions' methods of the Problem instance to load
        and validate the symbolic problem definitions from a file.
        The method also performs a coherence check between data tables and problem
        definitions based on 'check_data_tables_and_problem_coherence' method.
        """
        with self.logger.log_timing(
            message=f"Loading and validating symbolic problem...",
            level='info',
        ):
            self.problem.load_symbolic_problem_from_file(force_overwrite)
            self.problem.add_implicit_symbolic_expressions()
            self.problem.validate_symbolic_expressions()
            self.problem.check_data_tables_and_problem_coherence()

    def generate_numerical_problem(
            self,
            force_overwrite: bool,
            allow_none_values: bool,
    ) -> None:
        """Call methods to generate numerical problems.

        The method initializes problem variables, fetch data from SQLite database
        to exogenous variables, and generate numerical problems. 
        The method can optionally overwrite existing problem definitions without
        prompting the user (force_overwrite, useful for testing purpose).
        The method can allow None values in the data for exogenous variables

        Args:
            force_overwrite (bool, optional): If True, forces the redefinition 
                of problems without prompting the user. Defaults to False.
            allow_none_values (bool, optional): If True, allows None values in
                the data for exogenous variables.
        """
        self.initialize_problems_variables()
        self.data_to_cvxpy_exogenous_vars(allow_none_values=allow_none_values)
        self.problem.generate_numerical_problems(force_overwrite)

    def solve_numerical_problems(
            self,
            force_overwrite: bool,
            integrated_problems: bool,
            convergence_monitoring: bool,
            convergence_norm: Defaults.NumericalSettings.NormType = 'l2',
            convergence_tables: Optional[List[str]] = None,
            relative_tolerance: Optional[float] = None,
            maximum_iterations: Optional[int] = None,
            keep_previous_iteration_db: bool = False,
            **solver_settings: Any,
    ) -> None:
        """Solve independent or integrated numerical problems.

        The method solves all defined numerical problems using the specified 
        solver, verbosity and numerical settings.
        The method checks if numerical problems have been defined and if they 
        have already been solved. If the problems have not been solved or if 
        'force_overwrite' is True, the method solves the problems using the 
        specified solver. The method can solve the problems individually or as 
        an integrated problem, depending on the 'integrated_problems' setting.
        The method logs information about the problem solving process.
        The method fetches the problem status after solving the problems.

        Args:
            force_overwrite (bool): If True, forces the re-solution of problems 
                even if they have already been solved without prompting the user.
            integrated_problems (bool): If True, solves the problems as an 
                integrated problem. If False, solves the problems as independent.
            convergence_monitoring (bool): If True, enables convergence monitoring
                during the solving of integrated problems.
            convergence_norm (Defaults.NumericalSettings.NormType, optional):
                The norm type to use for convergence monitoring in integrated 
                problems. Defaults to 'l2' (Euclidean norm). Overrides 
                'Defaults.NumericalSettings.MODEL_COUPLING_SETTINGS'.
            convergence_tables (Optional[List[str]], optional): List of data table
                keys to check for convergence in integrated problems. If None,
                all endogenous data tables are checked.
            relative_tolerance (float, optional): Numerical tolerance for verifying
                maximum relative change between iterations in integrated problems for 
                each data table. Overrides 'Defaults.NumericalSettings.MODEL_COUPLING_SETTINGS'.
            maximum_iterations (Optional[int], optional): The maximum number of 
                iterations for the solver. Overrides 
                'Defaults.NumericalSettings.MODEL_COUPLING_SETTINGS'.
            keep_previous_iteration_db (bool, optional): If True, does not delete 
                the database related to the last-1 iteration. For debugging purpose.
                Default to False.
            **solver_settings: Additional keyword arguments passed to the solver.

        Raises:
            OperationalError: If numerical problems have not been defined.
        """
        if self.problem.numerical_problems is None:
            msg = "Numerical problems must be defined first."
            self.logger.warning(msg)
            raise exc.OperationalError(msg)

        problem_status = self.problem.problem_status

        if (isinstance(problem_status, dict) and
            not all(value is None for value in problem_status.values())) or \
                (problem_status is not None and not isinstance(problem_status, dict)):

            if not force_overwrite:
                self.logger.warning("Numeric problems already solved.")
                if not util.get_user_confirmation("Solve again numeric problems?"):
                    self.logger.warning("Numeric problem NOT solved.")
                    return

        if integrated_problems:
            self.solve_integrated_problems(
                convergence_monitoring=convergence_monitoring,
                convergence_norm=convergence_norm,
                tables_to_check=convergence_tables,
                relative_tolerance=relative_tolerance,
                maximum_iterations=maximum_iterations,
                keep_previous_iteration_db=keep_previous_iteration_db,
                **solver_settings,
            )
        else:
            self.solve_independent_problems(**solver_settings)

        self.problem.fetch_problem_status()

    def compare_databases(
            self,
            values_relative_diff_tolerance: float,
            other_db_dir_path: Path | str,
            other_db_name: str,
    ) -> None:
        """COmpare results in the model SQLite database with another SQLite database.

        This method compares the results stored in the model's SQLite database 
        with those in a reference database. The reference database must be specified 
        via the 'other_db_dir_path' and 'other_db_name' arguments. 
        The comparison uses the 'check_databases_equality' method and applies a 
        relative difference tolerance.

        Args:
            values_relative_diff_tolerance (float): The relative difference 
                tolerance (%) to use when comparing the databases. It overwrites
                the default setting in Defaults.
            other_db_dir_path (Path | str): The directory path of the reference
                database.
            other_db_name (str): The name of the reference database.
        """
        with db_handler(self.sqltools):
            self.sqltools.check_databases_equality(
                other_db_dir_path=other_db_dir_path,
                other_db_name=other_db_name,
                tolerance_percentage=values_relative_diff_tolerance,
            )

    def solve_independent_problems(self, **solver_settings: Any) -> None:
        """Solve independent numerical problems.

        This method get and solve the numerical problem/s in the Problem instance
        based on solver settings as keyworded arguments.
        The method updates the 'status' field of the input DataFrame(s) in-place 
        to reflect the solution status of each problem.

        Args:
            **solver_settings (Any): Additional arguments to pass to the solver.

        Raises:
            exc.OperationalError: If 'numerical_problems' has not defined as Problem
                property.
        """
        numerical_problems = self.problem.numerical_problems

        if isinstance(numerical_problems, pd.DataFrame):
            self.problem.solve_problem_dataframe(
                problem_dataframe=numerical_problems,
                **solver_settings
            )
        elif isinstance(numerical_problems, dict):
            for sub_problem in numerical_problems.keys():
                self.problem.solve_problem_dataframe(
                    problem_dataframe=numerical_problems[sub_problem],
                    problem_name=sub_problem,
                    **solver_settings
                )
        else:
            if numerical_problems is None:
                msg = "Numerical problems must be defined first."
                self.logger.warning(msg)
                raise exc.OperationalError(msg)

    def solve_integrated_problems(
            self,
            convergence_monitoring: bool = True,
            convergence_norm: Defaults.NumericalSettings.NormType = 'l2',
            tables_to_check: str | List[str] = 'all_endogenous',
            relative_tolerance: Optional[float] = None,
            maximum_iterations: Optional[int] = None,
            keep_previous_iteration_db: bool = False,
            **solver_settings: Any,
    ) -> None:
        """Solve integrated numerical problems iteratively.

        Nonlinear problems are formulated by the user as sequence of convex problems
        (i.e. decomposed into coupled convex subproblems). These problems are 
        solved iteratively using a block Gauss-Seidel (alternating optimization) 
        scheme, where updated endogenous variables are exchanged until convergence.

        This method implement such iterative algorithm, solving problems using the 
        specified solver and verbosity settings.
        First, the method creates a backup copy of the original database, which is
        used to restore the database at the end of the iterations.
        Then, for each scenario defined in the index, the method iteratively solves
        all sub-problems until convergence is reached or until the maximum number
        of iterations is reached.
        The method calculates the values differences between the solutions in 
        consecutive iterations using the 'get_tables_values_norm_changes' method 
        of the SQLTools instance, by computing different norm types for each table:

            - Maximum relative/absolute changes (max_relative, max_absolute)
            - Manhattan Norm (l1) 
            - Euclidean Norm (l2)
            - Maximum Norm (linf)

        The method handles the database operations required for each iteration, 
        including updating the data for exogenous variables and exporting the 
        data for endogenous variables.
        Differently with respect to solve_independent_problems() method, this method
        solve all sub-problems iteratively for the same case (combination of sets).

        Args:
            convergence_monitoring (bool, optional): If True, enables convergence
                monitoring during the solving of integrated problems. Defaults to True.
            convergence_norm (Literal['max_relative', 'max_absolute', 'l1', 
                'l2', 'linf'], optional): The type of norm to use for convergence 
                checking. Defaults to 'l2'.
            tables_to_check (str | List[str], optional): List of data table keys to check for convergence. 
                If 'all_endogenous', all endogenous data tables are checked.
                If 'hybrid_only', only hybrid endogenous data tables are checked.
                Defaults to 'all_endogenous'.
            relative_tolerance (Optional[float], optional): The maximum
                relative tolerance that all value tables must respect as a convergence
                criterion (0.1 -> 10%). Overwrite default setting in Defaults. 
                Defaults to None.
            maximum_iterations (Optional[int], optional): The maximum number of 
                iterations for the solver. Overwrite default setting in Defaults. 
                Defaults to None.
            keep_previous_iteration_db (bool, optional): If True, saves the
                database of the previous iteration for debugging purposes. 
                Defaults to False.
            **solver_settings (Any): Arguments to pass to the solver.
        """
        sqlite_db_file_name = Defaults.ConfigFiles.SQLITE_DATABASE_FILE
        sqlite_db_file_name_bkp = Defaults.ConfigFiles.SQLITE_DATABASE_FILE_BKP
        scenarios_header = Defaults.Labels.SCENARIO_COORDINATES
        problem_status_header = Defaults.Labels.PROBLEM_STATUS

        sqlite_db_path = self.paths['model_dir']
        base_name, extension = os.path.splitext(sqlite_db_file_name)
        sqlite_db_file_name_previous = f"{base_name}_previous{extension}"
        sub_problems_keys = list(self.problem.numerical_problems.keys())
        scenarios_df = self.index.scenarios_info

        model_coupling_settings = Defaults.NumericalSettings.MODEL_COUPLING_SETTINGS
        min_guard_tolerance = model_coupling_settings['absolute_minimum_guard_tolerance']

        if not maximum_iterations:
            maximum_iterations = model_coupling_settings['max_iterations']
        elif maximum_iterations <= 1:
            msg = "Maximum iterations for integrated problems must be greater than 1."
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        if not relative_tolerance:
            relative_tolerance = model_coupling_settings['relative_tolerance']

        if isinstance(tables_to_check, str):
            if tables_to_check == 'all_endogenous':
                tables_to_check = self.problem.endogenous_tables_all
            elif tables_to_check == 'hybrid_only':
                tables_to_check = self.problem.endogenous_tables_hybrid
            else:
                msg = "Parameter 'tables_to_check' string value not allowed. "
                self.logger.error(msg)
                raise exc.SettingsError(msg)

        elif isinstance(tables_to_check, list):
            invalid_tables = [
                table for table in tables_to_check
                if table not in self.problem.endogenous_tables_all
            ]
            if invalid_tables:
                msg = f"One or more tables in 'tables_to_check' are not " \
                    f"endogenous tables: {invalid_tables}."
                self.logger.error(msg)
                raise exc.SettingsError(msg)

        problems_status = pd.DataFrame(
            index=scenarios_df.index,
            columns=sub_problems_keys,
        )

        # create a backup copy of the original database
        # (will be restored at the end)
        self.files.copy_file_to_destination(
            path_destination=sqlite_db_path,
            path_source=sqlite_db_path,
            file_name=sqlite_db_file_name,
            file_new_name=sqlite_db_file_name_bkp,
            force_overwrite=True,
        )

        try:
            for scenario_idx in scenarios_df.index:

                scenario_coords = scenarios_df.loc[
                    scenario_idx,
                    scenarios_header
                ]

                if scenario_coords:
                    scenario_label = '-'.join(map(str, scenario_coords))
                    self.logger.info(
                        f"Solving integrated problems | Scenario {scenario_coords}")
                else:
                    self.logger.info("Solving integrated problems")

                iter_count = 0
                all_errors = {table: [] for table in tables_to_check}
                convergence_thresholds = {}

                with self.logger.convergence_monitor(
                    output_dir=sqlite_db_path,
                    scenario_name=scenario_label if scenario_coords else "default",
                    activate_terminal=convergence_monitoring,
                    norm_metric=convergence_norm,
                    relative_tolerance=relative_tolerance,
                ) as conv_monitor:

                    conv_log = conv_monitor['log']

                    while True:
                        try:
                            self.logger.info(
                                f"Iteration count: {iter_count} | "
                                f"iterations limit: {maximum_iterations}")

                            if iter_count >= 1:

                                self.logger.info(
                                    f"Creating copy of database from previous iteration.")

                                self.files.copy_file_to_destination(
                                    path_destination=sqlite_db_path,
                                    path_source=sqlite_db_path,
                                    file_name=sqlite_db_file_name,
                                    file_new_name=sqlite_db_file_name_previous,
                                    force_overwrite=True,
                                )

                                self.logger.info(
                                    "Updating exogenous variables data from previous iteration.")

                                self.data_to_cvxpy_exogenous_vars(
                                    scenarios_idx=scenario_idx,
                                    filter_negative_values=True,
                                    warnings_on_negatives=True,
                                    validate_types=False,
                                )

                            for sub_problem, problem_df \
                                    in self.problem.numerical_problems.items():

                                self.problem.solve_problem_dataframe(
                                    problem_name=sub_problem,
                                    problem_dataframe=problem_df,
                                    scenarios_idx=scenario_idx,
                                    **solver_settings
                                )

                                status = problem_df.loc[
                                    scenario_idx,
                                    problem_status_header
                                ]

                                problems_status.at[scenario_idx, sub_problem] = \
                                    status

                            if not all(
                                problems_status.loc[scenario_idx] == 'optimal'
                            ):
                                self.logger.warning(
                                    "One or more sub-problems infeasible for scenario "
                                    f"{scenario_coords}."
                                )
                                break

                            self.logger.info(
                                "Problems solved successfully. Exporting data to "
                                "SQLite database.")

                            self.cvxpy_endogenous_data_to_database(
                                scenarios_idx=scenario_idx,
                                force_overwrite=True,
                                suppress_warnings=True,
                            )

                            # first solution: compute tolerances
                            if iter_count == 0:
                                self.logger.info(
                                    "Setting convergence thresholds as relative "
                                    "tolerances of tables scales.")

                                with db_handler(self.sqltools):
                                    tables_scales = \
                                        self.sqltools.get_tables_values_scale(
                                            norm_type=convergence_norm,
                                            tables_names=tables_to_check,
                                        )
                                convergence_thresholds = {
                                    table_key: min_guard_tolerance +
                                    tables_scales[table_key] *
                                    relative_tolerance
                                    for table_key in tables_to_check
                                }

                                iter_count += 1
                                continue

                            # relative error must be computed for scenarios_idx only
                            # funziona lo stesso, perchè se il problema è infeasible i
                            # risultati non vengono esportati (break qui sopra) e il
                            # database rimane sempre uguale
                            with db_handler(self.sqltools):
                                norm_changes = \
                                    self.sqltools.get_tables_values_norm_changes(
                                        other_db_dir_path=sqlite_db_path,
                                        other_db_name=sqlite_db_file_name_previous,
                                        norm_type=convergence_norm,
                                        tables_names=tables_to_check,
                                    )

                            # Defining messages for convergence monitoring
                            for table in tables_to_check:
                                all_errors[table].append(norm_changes[table])

                            lines: List[str] = self._format_convergence_table(
                                tables_to_check=tables_to_check,
                                all_errors=all_errors,
                                iter_count=iter_count,
                                convergence_thresholds=convergence_thresholds,
                            )

                            # Check convergence: any table above thresholds?
                            tables_above_max = {
                                table: value
                                for table, value in norm_changes.items()
                                if value > convergence_thresholds[table]
                            }

                            if tables_above_max:
                                self.logger.info(
                                    "Numerical convergence NOT reached")
                                conv_log("\n".join(lines))
                            else:
                                lines.append("")
                                lines.append("Convergence reached!")
                                conv_log("\n".join(lines))

                                self.logger.info(
                                    f"Numerical convergence reached | "
                                    f"Scenario {scenario_coords} | "
                                    f"Iterations: {iter_count} ")
                                break

                            if iter_count == maximum_iterations:
                                self.logger.warning(
                                    "Maximum number of iterations hit before "
                                    "reaching convergence")
                                break

                            iter_count += 1

                        finally:
                            if iter_count >= 1 and \
                                    not keep_previous_iteration_db:
                                self.files.erase_file(
                                    dir_path=sqlite_db_path,
                                    file_name=sqlite_db_file_name_previous,
                                    force_erase=True,
                                    confirm=False,
                                )

        finally:
            # after iterations are concluded for all scenarios
            # erase the database modified during the iterations
            # and restore original database from backup
            self.files.erase_file(
                dir_path=sqlite_db_path,
                file_name=sqlite_db_file_name,
                force_erase=True,
                confirm=False,
            )

            self.files.rename_file(
                dir_path=sqlite_db_path,
                name_old=sqlite_db_file_name_bkp,
                name_new=sqlite_db_file_name,
            )

    def _format_convergence_table(
            self,
            tables_to_check: List[str],
            all_errors: Dict[str, List[float]],
            iter_count: int,
            convergence_thresholds: Dict[str, float],
            values_format: str = ".3e",
    ) -> List[str]:
        """Format convergence monitoring table with errors for each iteration.

        - Per-table values are starred if > tolerance_max.
        - 'ALL TABLES RMS' row is starred if tolerance_avg is provided and exceeded.

        Args:
            tables_to_check: List of table names to monitor.
            all_errors: Dictionary mapping table names to list of errors. It can
                include the special key 'ALL TABLES RMS' with a single series.
            iter_count: Current iteration count.
            convergence_thresholds: Absolute thresholds for each table.
            values_format: Format string for floating-point values. Defaults to ".3e".

        Returns:
            List of formatted strings for table display.
        """
        lines: List[str] = []
        display_rows = list(tables_to_check)

        # Table (first) column width
        max_table_name_len = max(len(table) for table in display_rows) \
            if display_rows else len("Table")
        table_col_width = max(max_table_name_len + 2, 16)

        # First column with thresholds values
        thresholds_tokens = [
            f"{format(convergence_thresholds[table], values_format)} "
            for table in display_rows
        ]
        thresholds_col_width = max(
            len("Thresholds"), max(len(t) for t in thresholds_tokens)
        ) + 2

        # Iteration labels as ranges: Iter_1-2, Iter_2-3, ...
        # If iter_count < 2, there are no ranges to display.
        iter_labels = [
            f"Iter_{j-1}-{j}"
            for j in range(1, max(iter_count, 1)+1)
        ]

        # Helper to build a value token (formatted value + optional star)
        def make_token(val: float, threshold: float) -> str:
            val_str = format(val, values_format)
            star = '*' if val > threshold else ' '
            return f"{val_str}{star}"

        # Compute per-value column width:
        # longest among tokens (values_format + star) and iteration labels
        tokens_for_width: List[str] = []
        for table in tables_to_check:
            tokens_for_width.extend(
                make_token(v, convergence_thresholds[table])
                for v in all_errors.get(table, []))

        # Fallback token in case of empty errors
        default_token_len = len(format(0.0, values_format)) + 1
        max_token_len = max(
            (len(t) for t in tokens_for_width),
            default=default_token_len
        )
        max_label_len = max((len(lbl) for lbl in iter_labels), default=0)
        padding = 2
        value_col_width = max(max_token_len, max_label_len) + padding

        # Header: Table | Thresholds | Iter columns
        header = f"{'Table':<{table_col_width}}" \
                 f"{'Thresholds':<{thresholds_col_width}}" + \
            "".join(f"{lbl:^{value_col_width}}" for lbl in iter_labels)
        lines.append(header)
        lines.append("-" * len(header))

        # Data rows
        for table, thr_str in zip(tables_to_check, thresholds_tokens):
            values_tokens = [
                make_token(e, convergence_thresholds[table])
                for e in all_errors.get(table, [])
            ]
            values_str = "".join(
                f"{tok:>{value_col_width}}" for tok in values_tokens
            )
            lines.append(
                f"{table:<{table_col_width}}"
                f"{thr_str:<{thresholds_col_width}}"
                f"{values_str}"
            )

        return lines

    def __repr__(self):
        """Return a string representation of the Core instance."""
        class_name = type(self).__name__
        return f'{class_name}'
