"""Moduel defining the Index class.

The Index class acts as a central registry for managing sets, data tables, and 
variables within the modeling system. It facilitates access and manipulation of 
these entities from other classes.
The Index class loads and initializes set tables, data tables, and variable
objects from configured sources and provides properties to access metadata and
operational characteristics related to these entities.
"""
from pathlib import Path
from typing import Dict, List, Optional

from scipy.sparse import issparse
import pandas as pd
import cvxpy as cp

from cvxlab.backward_compat import BackwardCompat
from cvxlab.backend.data_table import DataTable
from cvxlab.backend.model_settings import ModelSettings, ModelPaths
from cvxlab.backend.set_table import SetTable
from cvxlab.backend.variable import Variable
from cvxlab.defaults import Defaults
from cvxlab.log_exc import exceptions as exc
from cvxlab.log_exc.logger import Logger
from cvxlab.support import util
from cvxlab.support.file_manager import FileManager
from cvxlab.support.dotdict import DotDict


class Index:
    """Central registry for managing sets, data tables and variables.

    Attributes:

    - logger (Logger): Logger object for logging information, warnings, and errors.
    - files (FileManager): Manages file-related operations with files.
    - paths (ModelPaths): Validated container with model file-system paths.
    - sets (Dict[str, SetTable]): Dictionary of set tables loaded upon initialization.
    - data (Dict[str, DataTable]): Dictionary of data tables loaded upon initialization.
    - variables (Dict[str, Variable]): Dictionary of variables fetched upon initialization.

    """

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            settings: ModelSettings,
            paths: ModelPaths,
    ):
        """Initialize a new instance of the Index class.

        This constructor initializes the Index with a logger, file manager, paths
        dictionary. It initializes sets and data attributes, loads and validates 
        structures of such items based on default structures provided in Defaults. 
        Once sets and data are loaded, it checks for coherence between them and 
        completes data tables with sets information. The method then generates variables 
        objects and fetches their coordinates information.

        Args:
            logger (Logger): Logger object for logging operations.
            files (FileManager): FileManager object for managing file operations.
            settings (ModelSettings): Validated container with model configuration settings.
            paths (ModelPaths): Validated container with model file-system paths.
        """
        self.logger = logger.get_child(__name__)

        self.files = files
        self.settings = settings
        self.paths = paths
        self._coordinates_loaded = False

        structures = Defaults.ConfigFiles.SETUP_INFO

        self.sets: dict[str, SetTable] = \
            self.load_and_validate_structure(structures[0])
        self.data: dict[str, DataTable] = \
            self.load_and_validate_structure(structures[1])

        self.check_data_tables_variables_naming_coherence()
        self.check_sets_coherence()
        self.check_data_coherence()
        self.data_tables_completion()

        self.variables: dict[str, Variable] = self.generate_variables()
        self.fetch_vars_coordinates_info()

    @property
    def sets_split_problem_dict(self) -> Dict[str, str]:
        """Dictionary containing sets that define different problems.

        This property returns a dictionary collecting inter-problem sets, that is,
        sets that defines independent numerical problems (i.e. with split problem 
        attribute as True). The dictionary maps the names of sets (dict keys) and 
        the related headers used in database tables for identifying sets entries 
        names (dict values). The method returns an empty dictionary if no 
        inter-problem sets are defined.

        Returns:
            Dict[str, str]: A dictionary where keys are set names and values
                are headers used in set tables. Returns an empty dictionary if 
                the required information is not available.
        """
        sets_split_problem = {}
        name_header = Defaults.Labels.NAME

        for key, set_table in self.sets.items():
            set_table: SetTable

            if getattr(set_table, 'split_problem', False) and \
                    set_table.table_headers is not None:

                headers = set_table.table_headers.get(name_header, [])

                if headers:
                    sets_split_problem[key] = headers[0]

        return sets_split_problem

    @property
    def list_sets(self) -> List[str]:
        """List of all set names.

        This property returns a list of all set names currently loaded in the Index.
        An empty list is returned if no sets are loaded.

        Returns:
            List[str]: List of set names.
        """
        return list(self.sets.keys()) if self.sets else []

    @property
    def list_data_tables(self) -> List[str]:
        """List of all data table names.

        This property returns a list of all data table names currently loaded 
        in the index. It returns an empty list if no data tables are loaded.

        Returns:
            List[str]: List of data table names.
        """
        return list(self.data.keys()) if self.sets else []

    @property
    def list_exogenous_data_tables(self) -> List[str]:
        """List of names of exogenous data table.

        This property returns a list of all data table names currently loaded into 
        the index collecting exogenous data. The method returns an empty list if 
        no exogenous data tables are loaded.
        In case a data table serves as container for both exogenous and endogenous
        data types, the table is considered exogenous.

        Returns:
            List[str]: List of exogenous data table identifiers.
        """
        var_types = Defaults.SymbolicDefinitions.VARIABLE_TYPES

        result = []
        for key, data_table in self.data.items():
            data_table: DataTable
            if data_table.type not in [
                var_types['ENDOGENOUS'],
                var_types['CONSTANT']
            ]:
                result.append(key)

        return result

    @property
    def list_all_tables(self) -> List[str]:
        """List of names of all sets tables and data tables.

        This property returns a list of all names of sets tables and data tables 
        currently loaded in the Index. The method returns an empty list if no 
        tables are loaded.

        Returns:
            List[str]: List of table identifiers.
        """
        return [*self.list_sets, *self.list_data_tables]

    @property
    def list_variables(self) -> List[str]:
        """List of names of all variables.

        This property returns a list of names of all the variables currently 
        loaded in the Index. Returns an empty list if no variables are loaded.

        Returns:
            List[str]: List of variable identifiers.
        """
        return list(self.variables.keys()) if self.variables else []

    @property
    def scenarios_info(self) -> Optional[pd.DataFrame]:
        """Dataframe containing scenarios information.

        This property returns a DataFrame containing linear combination of
        all set values for all inter-problem sets, representing different
        scenarios.

        Returns:
            Optional[pd.DataFrame]: A DataFrame with scenarios information if 
                available, otherwise None.
        """
        scenarios_coordinates = {}
        list_sets_split_problem = list(self.sets_split_problem_dict.values())
        scenarios_coords_header = Defaults.Labels.SCENARIO_COORDINATES

        for set_key, set_header in self.sets_split_problem_dict.items():
            set_table: SetTable = self.sets[set_key]

            if set_table.data is None:
                msg = (
                    "Cannot generate scenarios information: "
                    f"Set table '{set_key}' has no data loaded. "
                )
                self.logger.error(msg)
                raise exc.MissingDataError(msg)

            set_values = set_table.data[set_header]
            scenarios_coordinates[set_header] = list(set_values)

        scenarios_df = util.unpivot_dict_to_dataframe(
            data_dict=scenarios_coordinates,
            key_order=list_sets_split_problem,
        )

        scenarios_df = util.add_column_to_dataframe(
            dataframe=scenarios_df,
            column_header=scenarios_coords_header,
            column_values=None,
        )

        for scenario_idx in scenarios_df.index:
            scenarios_coords = [
                scenarios_df.loc[scenario_idx][set_key]
                for set_key in list_sets_split_problem
            ]
            scenarios_df.at[
                scenario_idx, scenarios_coords_header
            ] = scenarios_coords

        return scenarios_df

    @property
    def hybrid_var_keys(self) -> List[str]:
        """List of keys of hybrid variables.

        This property returns a list of keys identifying all hybrid variables
        currently loaded in the Index. An empty list is returned if no hybrid
        variables are found.

        Returns:
            List[str]: A list of hybrid variable keys.
        """
        return [
            var_key for var_key, variable in self.variables.items()
            if isinstance(variable.type, dict)
        ]

    @property
    def data_tables_inter_problem_sets(self) -> Dict[str, Dict[str, str]]:
        """Dictionary of inter-problem sets for each data table.

        This property returns a dictionary where keys are data table identifiers
        and values are lists of inter-problem sets associated with each data table.
        An empty dictionary is returned if no inter-problem sets are found.

        Returns:
            Dict[str, List[str]]: A dictionary mapping data table identifiers to
                their corresponding inter-problem sets.
        """
        data_tables_inter_problem_sets = {}

        for table_key, data_table in self.data.items():
            data_table: DataTable

            for set_key in data_table.coordinates:

                if set_key in self.sets_split_problem_dict:
                    set_table: SetTable = self.sets[set_key]
                    set_header = set_table.set_name_header

                    if table_key not in data_tables_inter_problem_sets:
                        data_tables_inter_problem_sets[table_key] = {}

                    data_tables_inter_problem_sets[table_key][set_key] = set_header

        return data_tables_inter_problem_sets

    def load_and_validate_structure(
            self,
            data_structure_key: str,
    ) -> DotDict[str, SetTable | DataTable]:
        """Load and validate a data structure (sets or data tables).

        This method loads and validates a specified data structure, which can be
        either sets or data tables, based on the provided key. It retrieves the
        appropriate structure and validation schema from predefined defaults,
        loads the data from the configured source, and validates each entry against
        the corresponding schema. If any entries fail validation, it logs the
        issues and raises a SettingsError. Upon successful validation, it transforms
        the data into a DotDict of either SetTable or DataTable objects, depending
        on the structure key provided.

        Args:
            data_structure_key (str): Key indicating which data structure to load
                and validate. Must be one of the predefined structure keys available
                in Defaults.ConfigFiles.SETUP_INFO.

        Raises:
            exc.SettingsError: If the passed data structure key is not recognized.
            exc.SettingsError: If any entries in the loaded data fail validation.

        Returns:
            DotDict[str, SetTable | DataTable]: A DotDict containing the validated
                data structure, with keys as identifiers and values as either
                SetTable or DataTable objects.
        """
        structures = Defaults.DefaultStructures
        config = Defaults.ConfigFiles

        source = self.settings.model_settings_from

        structures_mapping = {
            config.SETUP_INFO[0]: (SetTable, structures.SET_STRUCTURE[1]),
            config.SETUP_INFO[1]: (DataTable, structures.DATA_TABLE_STRUCTURE[1]),
        }

        if data_structure_key in structures_mapping:
            object_class, validation_structure = \
                structures_mapping[data_structure_key]
        else:
            msg = "Data structure key not recognized. Available keys: " \
                f"{config.SETUP_INFO}."
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        self.logger.debug(
            f"Loading and validating '{data_structure_key}' data structure "
            f"from '{source}' source.")

        data = self.files.load_data_structure(
            structure_key=data_structure_key,
            source=source,
            dir_path=self.paths.model_dir,
        )

        # Normalize deprecated fields before validating the loaded structure.
        if data_structure_key == config.SETUP_INFO[1]:
            BackwardCompat.integer_to_domain(data, self.logger)

        invalid_entries = {
            key: problems
            for key, value in data.items()
            if (
                problems := self.files.validate_data_structure(
                    value, validation_structure
                )
            )
        }

        if invalid_entries:
            if self.settings.detailed_validation:
                self.logger.error(
                    "Validation error report ===================================")
                for key, error_log in invalid_entries.items():
                    for coord, error in error_log.items():
                        self.logger.error(
                            f"Validation error | {data_structure_key} | '{key}' | "
                            f"{coord} | {error}")
            else:
                self.logger.error(
                    f"Validation | {data_structure_key} | Entries: "
                    f"{list(invalid_entries.keys())}")

            msg = f"'{data_structure_key}' data validation not successful. " \
                f"Check setup '{source}' file. "
            if not self.settings.detailed_validation:
                msg += "Set 'detailed_validation=True' for more information."

            self.logger.error(msg)
            raise exc.SettingsError(msg)

        data = util.transform_dict_none_to_values(data, none_to={})

        validated_structure = DotDict({
            key: object_class(logger=self.logger, key_name=key, **value)
            for key, value in data.items()
        })

        return validated_structure

    def check_sets_coherence(self) -> None:
        """Check coherence among set tables.

        This method performs coherence checks among the set tables loaded in the Index.
        All anomalies are collected in a dictionary with keys identifying the location
        of the anomaly, and value as the related description. Errors are raised and
        logged at the end of the method. Further checks may be developed.

        The following checks are performed looping over set tables:

        - In case of copied set tables (copy_from attribute), the source table
            must be a valid set table.
        - Copied set table split_problem attribute must match source set table.
        - Copied set table structure must match source set table structure.
        - Copied set table aggregations must match source set table aggregations.

        Raises:
            exc.SettingsError: Raised with the list of all exceptions collected
                during the coherence checks, identifying mistakes in model settings.
        """
        problems = {}

        for set_key, set_table in self.sets.items():
            set_table: SetTable

            # in case of copied set tables (copy_from attribute)
            if set_table.copy_from:
                set_table_source_key = set_table.copy_from

                # source table must be a valid set table
                if set_table_source_key not in self.sets:
                    problems[set_key] = f"Source set table '{set_table_source_key}' " \
                        "to be copied not found in defined sets."

                else:
                    set_table_source: SetTable = self.sets[set_table_source_key]

                    # copied set table split_problem attribute must match source set table
                    if set_table.split_problem != set_table_source.split_problem:
                        problems[set_key] = f"'split_problem' attribute of copied set " \
                            f"table do not match those of source set table " \
                            f"'{set_table_source_key}'."

                    # if filters are defined, they must be for source and destination sets
                    if set_table_source.table_filters and not set_table.table_filters:
                        problems[set_key] = f"Filters of set table '{set_key}' " \
                            f"must be defined and equal to filters of the " \
                            f"source set table '{set_table_source_key}'. " \
                            "Check filters in settings files."

                    # if aggregations are defined, they must be for source and destination sets
                    if set_table.table_aggregations and not set_table_source.table_aggregations:
                        problems[set_key] = "Aggregations must be defined for both " \
                            f"copied set table and source set table '{set_table_source_key}'."

        if problems:
            if self.settings.detailed_validation:
                for key, error_log in problems.items():
                    self.logger.error(
                        f"Set tables coherence check | {key} | {error_log}")
            else:
                self.logger.error(
                    f"Set tables coherence error | Sets tables | Entries: "
                    f"{list(problems.keys())}")

            msg = "Sets tables coherence check not successful. " \
                "Check setup files."
            if not self.settings.detailed_validation:
                msg += "Set 'detailed_validation=True' for more information."

            self.logger.error(msg)
            raise exc.SettingsError(msg)

    def check_data_tables_variables_naming_coherence(self) -> None:
        """Check naming coherence for data tables and variables.

        This method performs naming coherence checks to ensure that:
        - All data table names are unique (case insensitive).
        - All variable names are unique (case sensitive).

        The method collects all anomalies in a dictionary with keys identifying 
        the location of the anomaly, and values as the related description. 
        Errors are raised and logged at the end of the method.

        Raises:
            exc.SettingsError: Raised with the list of all exceptions collected
                during the naming coherence checks, identifying mistakes in model settings.
        """
        self.logger.debug(
            "Checking data tables and variables naming coherence.")

        problems = {}

        # Check that all data table names are unique (case insensitive)
        table_names_lower = {}
        for table_key in self.data.keys():
            table_name_lower = table_key.lower()
            if table_name_lower in table_names_lower:
                problems['data_tables_naming'] = \
                    f"Duplicate data table names (case insensitive): " \
                    f"'{table_names_lower[table_name_lower]}' and '{table_key}'. " \
                    f"Table names must be unique regardless of case."
                break
            table_names_lower[table_name_lower] = table_key

        # Check that all variable names are unique (case sensitive)
        all_variable_names = []
        for data_table in self.data.values():
            all_variable_names.extend(data_table.variables_info.keys())

        duplicate_vars = [
            var for var in set(all_variable_names)
            if all_variable_names.count(var) > 1
        ]

        if duplicate_vars:
            problems['variables_naming'] = \
                f"Duplicate variable names found: {duplicate_vars}. " \
                f"Variable names must be unique across all data tables."

        if problems:
            if self.settings.detailed_validation:
                for key, error_log in problems.items():
                    self.logger.error(
                        f"Naming coherence check | {key} | {error_log}")
            else:
                self.logger.error(
                    f"Naming coherence error | Data tables, Variables | Entries: "
                    f"{list(problems.keys())}")

            msg = "Data tables and variables naming coherence check not successful. " \
                "Check setup files."
            if not self.settings.detailed_validation:
                msg += " Set 'detailed_validation=True' for more information."

            self.logger.error(msg)
            raise exc.SettingsError(msg)

    def check_data_coherence(self) -> None:
        """Check coherence between sets and data tables.

        This method performs various coherence checks between the sets and data
        tables loaded in the Index. All anomalies are collected in a dictionary
        with keys identifying the location of the anomaly, and value as the related
        description. Errors are raised and logged at the end of the method.
        Further checks may be developed.

        The following checks are performed looping over data tables:

        - Data tables must be of the allowed type (defined in Defaults class).
        - Exogenous/constant data tables cannot have 'domain' set.
        - Coordinates defining data tables must be valid (defined among sets).
        - All inter-problem sets must be embedded in endogenous data tables coordinates.

        For each data table, variables are looped and the following checks performed:

        - Variable property 'value' can be only assigned for 'constant' type, and 
            it must be of the allowed type (defined in Defaults class).
        - Variable property 'blank_fill' can be only defined for exogenous variables.
        - Other variable properties can be defined only as related data table 
            coordinates.

        For coordinates defined within the variable, the following checks are performed:

        - Variable dimension assigned to the coordiante must be valid (row, cols).
        - Eventual variable dimension filter must be well-defined: filter key 
            and related values must be part of the defined filters in sets.

        Raises:
            exc.SettingsError: Raised with the list of all exceptions collected
                during the coherence checks, identifying mistakes in model settings.
        """
        allowed_var_types = Defaults.SymbolicDefinitions.VARIABLE_TYPES
        allowed_constants = Defaults.SymbolicDefinitions.ALLOWED_CONSTANTS.keys()
        allowed_dims = list(Defaults.SymbolicDefinitions.DIMENSIONS.values())

        coordinates_key = Defaults.Labels.COORDINATES_KEY
        dim_key = Defaults.Labels.DIM
        filters_key = Defaults.Labels.FILTERS
        variables_info_key = Defaults.Labels.VARIABLES_INFO_KEY
        value_key = Defaults.Labels.VALUE_KEY
        blank_fill_key = Defaults.Labels.BLANK_FILL_KEY
        nonneg_key = Defaults.Labels.NONNEG_KEY

        problems = {}

        for table_key, data_table in self.data.items():
            data_table: DataTable

            # data table type must be allowed
            if isinstance(data_table.type, dict):
                table_type = data_table.type.values()
            else:
                table_type = [data_table.type]

            if not all(
                type in allowed_var_types.values()
                for type in table_type
            ):
                problems[table_key] = "Table type not allowed."

            # exogenous/constant data tables cannot have a domain set
            if data_table.type in [
                allowed_var_types['EXOGENOUS'], allowed_var_types['CONSTANT']
            ] and data_table.domain is not None:
                problems[table_key] = (
                    "Exogenous or constant table data cannot have 'domain' set. ")

            # coordinates in data table must be coherent with sets
            invalid_coordinates = [
                coord for coord in data_table.coordinates
                if coord not in self.sets
            ]
            if invalid_coordinates:
                path = f"{table_key}.{coordinates_key}"
                problems[path] = f"Invalid coordinates: {invalid_coordinates}"

            # for each variable in data table
            for var_key, var_info in data_table.variables_info.items():
                var_info: dict | None

                # variable can be defined without specifying dimensions
                # (will be parsed as scalars)
                if not var_info:
                    continue

                path = f"{table_key}.{variables_info_key}.{var_key}"

                for property_key, property_value in var_info.items():

                    # if there are no values to be parsed, continue
                    if not property_value:
                        continue

                    # value field must be assigned to constants only, and it
                    # must be allowed
                    elif property_key == value_key:
                        if data_table.type != allowed_var_types['CONSTANT']:
                            problems[f"{path}.{value_key}"] = \
                                "'value' attribute can only be assigned to constants."

                        if property_value and property_value not in allowed_constants:
                            problems[f"{path}.{value_key}"] = \
                                f"Constant value type '{property_value}' not allowed. " \
                                f"Allowed types: {list(allowed_constants)}."

                    # blank_fill field can only be assigned to exogenous variables
                    elif property_key == blank_fill_key:
                        if data_table.type == (
                            allowed_var_types['ENDOGENOUS'] or allowed_var_types['CONSTANT']
                        ):
                            problems[f"{path}.{blank_fill_key}"] = \
                                "'blank_fill' attribute cannot be assigned to " \
                                "endogenous variables or constants."

                    # sign field can only be assigned to endogenous or hybrid variables
                    elif property_key == nonneg_key:
                        if data_table.type == allowed_var_types['EXOGENOUS'] and \
                                property_value is True:
                            problems[f"{path}.{nonneg_key}"] = \
                                "Exogenous variables cannot be defined as " \
                                "non-negative. Check variables settings."

                    # other properties must be allowed coordinates
                    elif property_key not in data_table.coordinates:
                        problems[path] = f"Property '{property_key}' not found in " \
                            "allowed properties or defined coordinates."

                    # for each var coordinate
                    elif property_key in data_table.coordinates \
                            and isinstance(property_value, dict):

                        # check if dim is allowed
                        if dim_key in property_value:
                            if property_value[dim_key] not in allowed_dims:
                                problems[f"{path}.{property_key}.{dim_key}"] = \
                                    f"Coordinate '{property_key}': " \
                                    f"dimension '{property_value[dim_key]}' not allowed. " \
                                    f"Allowed dimensions: {allowed_dims}."

                        # check if filters are allowed
                        if filters_key in property_value:
                            var_filters = dict(property_value[filters_key])

                            # verify if the filters are defined in the related set table
                            set_structure = \
                                self.sets[property_key].table_structure

                            if filters_key not in set_structure:
                                problems[f"{path}.{property_key}.{filters_key}"] = \
                                    f"Filters not defined for related '{property_key}' set."
                                continue

                            # if filters are defined, check if they are coherent with the
                            # related set table
                            set_filters = {
                                key: list(value['values']) for key, value
                                in set_structure[filters_key].items()
                            }

                            for filter_key, filter_value in var_filters.items():
                                if not isinstance(filter_value, list):
                                    filter_value = [filter_value]

                                if filter_key not in set_filters:
                                    problems[f"{path}.{filters_key}.{filter_key}"] = \
                                        f"Filter '{filter_key}' not found in available " \
                                        f"'{property_key}' set filters."

                                elif not util.items_in_list(
                                    filter_value,
                                    set_filters[filter_key]
                                ):
                                    problems[f"{path}.{property_key}.filters.{filter_key}"] = \
                                        f"Filter value '{filter_value}' not found in " \
                                        f"related '{property_key}' set filter values."

        if problems:
            if self.settings.detailed_validation:
                for key, error_log in problems.items():
                    self.logger.error(
                        f"Data coherence check | {key} | {error_log}")
            else:
                self.logger.error(
                    f"Data coherence error | Sets, Data tables | Entries: "
                    f"{list(problems.keys())}")

            msg = "Sets and Data tables coherence check not successful. " \
                "Check setup files."
            if not self.settings.detailed_validation:
                msg += "Set 'detailed_validation=True' for more information."

            self.logger.error(msg)
            raise exc.SettingsError(msg)

    def data_tables_completion(self) -> None:
        """Complete attributes of data tables based on sets tables.

        This method loops over each data table and complete some attributes,
        specifically the dictionaries table headers and coordinate headers to be
        subsequently used to define data tables in the database.

        Raises:
            exc.MissingDataError: Raised in case information in sets are missing.
        """
        self.logger.debug(
            "Completing data tables with information taken from related Sets.")

        for table in self.data.values():
            table: DataTable
            set_headers_key = Defaults.Labels.NAME

            table.table_headers = {}
            for set_key in table.coordinates:

                if self.sets.get(set_key) and self.sets[set_key].table_headers:
                    table.table_headers[set_key] = \
                        self.sets[set_key].table_headers[set_headers_key]
                else:
                    msg = f"Set key '{set_key}' not found in sets or table_headers is None."
                    self.logger.error(msg)
                    raise exc.MissingDataError(msg)

            table.table_headers = util.add_item_to_dict(
                dictionary=table.table_headers,
                item=Defaults.Labels.ID_FIELD,
                position=0,
            )
            table.coordinates_headers = {
                key: value[0] for key, value in table.table_headers.items()
                if key in table.coordinates
            }

    def generate_variables(self) -> DotDict[str, Variable]:
        """Generate all variables as Variable instances.

        This method is a Variable class factory, generating the variable DotDict 
        instance collecting instances of all Variable objects.

        Returns:
            Dict[str, Variable]: A DotDict instance with 'Variable' objects keyed by
                their identifiers, collected across all data tables.
        """
        self.logger.debug(
            "Fetching and validating variables from data tables, generating "
            f"'{Variable.__name__}' objects.")

        variables_info = DotDict({})

        for table_key, data_table in self.data.items():
            data_table: DataTable

            for var_key, var_info in data_table.variables_info.items():

                variable = DotDict({
                    var_key: Variable(
                        logger=self.logger,
                        symbol=var_key,
                        related_table=table_key,
                        type=data_table.type,
                        var_info=var_info,
                    )
                })

                variables_info.update(variable)

        return variables_info

    def fetch_vars_coordinates_info(self) -> None:
        """Fetch variables coordinates information from related data tables.

        This method populates each variable in the Index with detailed coordinates 
        information, categorizing data table headers into rows, columns, intra-problem sets,
        and inter-problem sets based on the variable's shape and configuration.
        The method derives this information from the related data tables specified for
        each variable.
        Specifically, for each variable, coordinates are categorized as follows:

        - rows: corresponding to the rows dimension in the variable's shape.
        - cols: corresponding to the columns dimension in the variable's shape.
        - intra: sets that are not part of the variable's shape and do not define
            different problems. In numerical problems, equations are defined
            for a number of times equal to the linear combination of intra-problem
            sets of all the variables involved.
        - inter: sets that define different problems (i.e., sets with the
            'split_problem' attribute set to True). Each unique combination
            of inter-problem sets defines a separate numerical problem.

        Raises:
            exc.MissingDataError: If a variable's related table is not defined, or
                if no data is found for a variable's related table.
        """
        self.logger.debug("Fetching 'coordinates_info' to Index.variables.")

        dimensions = Defaults.SymbolicDefinitions.DIMENSIONS

        def _key_matches_shape(
                key: str,
                shape: List[str] | str | int
        ) -> bool:
            """Check if a key matches a given shape."""
            if isinstance(shape, list):
                return key in shape
            elif isinstance(shape, str):
                return key == shape
            else:  # shape is 1 (int)
                return False

        for var_key, variable in self.variables.items():
            variable: Variable

            if variable.related_table is None:
                msg = "Variable related table not defined for variable " \
                    f"'{var_key}'."
                self.logger.error(msg)
                raise exc.MissingDataError(msg)

            related_table_data: DataTable = self.data.get(
                variable.related_table)

            if not related_table_data:
                msg = f"No data found for related table '{variable.related_table}' "
                self.logger.error(msg)
                raise exc.MissingDataError(msg)

            related_table_headers = related_table_data.table_headers
            rows, cols, intra, inter = {}, {}, {}, {}

            for key, value in related_table_headers.items():
                table_header = value[0]

                if key in Defaults.Labels.ID_FIELD:
                    continue

                rows_shape = variable.shape_sets[0]
                cols_shape = variable.shape_sets[1]

                if _key_matches_shape(key, rows_shape):
                    rows[key] = table_header
                elif _key_matches_shape(key, cols_shape):
                    cols[key] = table_header
                else:
                    if key not in self.sets_split_problem_dict:
                        intra[key] = table_header
                    else:
                        inter[key] = table_header

            variable.coordinates_info = {
                dimensions['ROWS']: rows,
                dimensions['COLS']: cols,
                dimensions['INTRA']: intra,
                dimensions['INTER']: inter,
            }

    def check_variables_coherence(self) -> None:
        """Validate variables definitions.

        This method performs various checks related to how variables have defined. 
        All anomalies are collected in a dictionary with keys identifying the location
        of the anomaly, and value as the related description. Errors are raised and
        logged at the end of the method. Further checks can be added. 

        Current checks include:
            If variable coordinates are defined for any dimension, the related
                values must be not empty, otherwise the variable will have no dimensions.

        Raises:
            exc.SettingsError: Raised with the list of all exceptions collected
                during the coherence checks, identifying mistakes in model settings.      
        """
        self.logger.debug("Validating variables coherence with coordinates.")

        problems = {}

        for var_key, variable in self.variables.items():
            variable: Variable

            # if variable coordinates are defined for any dimension, their values
            # must be not empty, otherwise the variable will have no dimensions.
            for dimension, coordinates in variable.coordinates.items():
                if not coordinates:
                    continue

                for coord_key, coord_list in coordinates.items():
                    if not coord_list:
                        path = f"{var_key}.coordinates.{dimension}"
                        problems[path] = "Empty list of coordinates for " \
                            f"'{coord_key}' set. Check related sets and filters."

            # other checks can be added
            # ...

        if problems:
            if self.settings.detailed_validation:
                self.logger.error(
                    "Validation error report ===================================")
                for key, error_log in problems.items():
                    self.logger.error(
                        f"Variables coherence check | {key} | {error_log}")
            else:
                self.logger.error(
                    f"Variables coherence error | Entries: "
                    f"{list(problems.keys())}")

            msg = "Variables coherence check not successful. " \
                "Check setup files and sets information."
            if not self.settings.detailed_validation:
                msg += "Set 'detailed_validation=True' for more information."

            self.logger.error(msg)
            raise exc.SettingsError(msg)

    def fetch_foreign_keys_to_data_tables(self) -> None:
        """Define foreign key relationships to data tables.

        This method assigns foreign keys relationships to the data tables in the 
        Index. This is achieved by referencing set tables that are associated with
        each data table based on coordinate headers. Each foreign key relationship 
        is defined by matching coordinate headers in the data tables with set tables, 
        effectively linking related data entities across the model.
        The 'foreign_keys' attribute is used to generate SQLite database tables 
        with foreign keys.

        Raises:
            exc.MissingDataError: If a table is referenced in a set but not found
                in the Index sets, indicating a configuration or data entry error.
        """
        self.logger.debug(
            "Loading tables 'foreign_keys' to Index.data_tables.")

        for table in self.data.values():
            table: DataTable

            if not hasattr(table, 'foreign_keys'):
                table.foreign_keys = {}

            for set_key, set_header in table.coordinates_headers.items():
                if set_key in self.sets:
                    table.foreign_keys[set_header] = \
                        (set_header, self.sets[set_key].table_name)
                else:
                    msg = f"Set key '{set_key}' not found in sets when " \
                        "assigning foreign keys."
                    self.logger.error(msg)
                    raise exc.MissingDataError(msg)

    def load_sets_data_to_index(
            self,
            excel_file_name: str,
            excel_file_dir_path: Path | str,
    ) -> None:
        """Load sets data from an Excel file into the Index.

        This method reads data from Excel sets tables and generates the related 
        DataFrames in set tables in the Index. If any set already contains data, 
        prompts the user to decide whether to overwrite the existing data.
        This method ensures that all sets defined in the Index are populated with
        the appropriate data from the specified Excel file, handling cases where
        sets may be defined as copies of other sets.

        Args:
            excel_file_name (str): The name of the Excel file to load.
            excel_file_dir_path (Path | str): The directory path where the Excel
                file is located.

        Raises:
            exc.SettingsError:  If errors are encountered while loading sets, 
                such as missing tables or mismatched headers, detailed in the logs.
        """
        if all(
            set_instance.data is None
            for set_instance in self.sets.values()
        ):
            self.logger.debug("Loading Sets data to Index.sets.")
        else:
            self.logger.warning(
                "At least one Set is already defined in Index.")
            if not util.get_user_confirmation("Overwrite Sets in Index?"):
                self.logger.info("Sets not overwritten in Index.")
                return
            self.logger.info("Overwriting Sets in Index.")

        sets_excel_data = self.files.excel_to_dataframes_dict(
            excel_file_name=excel_file_name,
            excel_file_dir_path=excel_file_dir_path,
        )

        sets_excel_keys = sets_excel_data.keys()

        problems = []

        for set_instance in self.sets.values():
            set_instance: SetTable

            if set_instance.table_name in sets_excel_keys:

                set_excel_table = sets_excel_data[set_instance.table_name]

                # check if table headers are well defined
                if (
                    not util.items_in_list(
                        items=set_excel_table.columns,
                        control_list=set_instance.set_excel_file_headers,
                    ) or
                    not util.items_in_list(
                        items=set_instance.set_excel_file_headers,
                        control_list=set_excel_table.columns,
                    )
                ):
                    msg = f"Set table '{set_instance.name}' | Excel Set table headers " \
                        "do not match Set table structure in Settings."
                    problems.append(msg)

                set_instance.data = set_excel_table
                continue

            if not set_instance.copy_from:
                msg = f"Set table '{set_instance.name}' | Table not included in " \
                    "the excel sets file, nor defined as a copy of another " \
                    "existing set. Check sets definition."
                problems.append(msg)
                continue

            if set_instance.table_headers is None:
                msg = f"Set table '{set_instance.name}' | Headers not defined."
                self.logger.error(msg)
                continue

            set_to_be_copied = set_instance.copy_from

            if set_to_be_copied in self.sets and \
                    self.sets[set_to_be_copied].data is not None and \
                    isinstance(self.sets[set_to_be_copied].data, pd.DataFrame):

                set_instance.data = self.sets[set_to_be_copied].data.copy()
                set_instance.data.columns = set_instance.set_excel_file_headers

            else:
                msg = f"Set table '{set_instance.name}' | Source table " \
                    f"'{set_to_be_copied}' not included in the defined Sets, or " \
                    "data not defined or defined in the wrong format. Check set " \
                    "name and data."
                problems.append(msg)
                continue

        if problems:
            for problem in problems:
                self.logger.error(problem)
            raise exc.SettingsError(
                "Errors encountered while loading sets. See logs for details.")

    def load_coordinates_to_data_index(self) -> None:
        """Fetch coordinates values from sets to data tables.

        This method populates the 'coordinates_values' dictionary of each data 
        table in the Index, with coordinates values from corresponding sets based 
        on headers defined in 'coordinates_headers'.
        This method maps set items to their respective data tables, facilitating 
        direct access to these items for operations that require context-specific 
        data, such as data processing or analysis tasks.

        Raises:
            exc.MissingDataError: If a set key specified in the data table's
                coordinates_headers does not exist in the Index sets, indicating
                a configuration or data entry error.
        """
        self.logger.debug("Loading variable coordinates to Index.data.")

        for table in self.data.values():
            table: DataTable

            for set_key, set_header in table.coordinates_headers.items():
                if set_key in self.sets:
                    table.coordinates_values[set_header] = self.sets[set_key].set_items
                else:
                    msg = f"Set key '{set_key}' not found in sets while " \
                        "loading coordinates"
                    self.logger.error(msg)
                    raise exc.MissingDataError(msg)

    def load_all_coordinates_to_variables_index(self) -> None:
        """Fetch coordinates values from sets to variables.

        This method populates the 'coordinates' attribute of each variable in 
        the Index with coordinates values taken from related sets. 
        This method utilizes 'coordinates_info' from each variable to retrieve 
        and to assign corresponding set items from the sets.
        The method ensures that all variables are enriched with complete and correct
        coordinate data, linking directly to the related set items based on
        specified coordinates headers.

        Raises:
            SettingsError: If a set key specified in the variable's coordinates_info
                does not exist in the Index sets, indicating a configuration or
                data entry error.
        """
        self.logger.debug("Loading variable coordinates to Index.variables.")

        for var_key, variable in self.variables.items():
            variable: Variable

            # Replicate coordinates_info with inner values as None
            # to prepare the structure
            coordinates: Dict[str, Dict[str, Optional[List[str]]]] = {
                category: {key: None for key in coord_values}
                for category, coord_values in variable.coordinates_info.items()
            }

            # Populate the coordinates with actual set names and values
            # from the index's sets
            for category, coord_dict in coordinates.items():
                for coord_key in coord_dict:
                    set_instance: SetTable = self.sets.get(coord_key)

                    if set_instance:
                        coordinates[category][coord_key] = set_instance.set_items
                    else:
                        msg = f"Set key '{coord_key}' not found in Index set for " \
                            f"variable '{var_key}'."
                        self.logger.error(msg)
                        raise exc.SettingsError(msg)

            variable.coordinates = coordinates

    def filter_coordinates_in_variables_index(self) -> None:
        """Filter variables coordinates based on sets filters.

        This method filters the coordinates values for each variable based on 
        filter conditions stored in sets. This process adjusts the coordinate values
        for 'rows', 'cols', and 'intra' categories by applying the filters
        specified in the sets filter headers.
        This method modifies the variable's coordinate data directly, ensuring
        that only relevant items that meet the filter conditions are retained.

        Raises:
            exc.MissingDataError: If a set key specified in a variable's
                coordinates does not exist in the Index sets, or if necessary
                filter headers are missing.
        """
        self.logger.debug(
            "Filtering variables coordinates in Index.variables.")

        filter_label = Defaults.Labels.FILTERS
        dimensions = Defaults.SymbolicDefinitions.DIMENSIONS

        # only rows, cols and intra-problem sets can be filtered
        categories_to_filter = [
            dimensions['ROWS'],
            dimensions['COLS'],
            dimensions['INTRA'],
        ]

        for variable in self.variables.values():
            variable: Variable

            # if no var_info are specified, variable is not filtered
            if variable.var_info is None:
                continue

            for coord_category, coord_dict in variable.coordinates.items():

                # Skip if no coordinates are defined for the category
                if not coord_dict:
                    continue

                for coord_key in coord_dict:

                    if not self.sets.get(coord_key):
                        msg = f"Set key '{coord_key}' not found in sets."
                        self.logger.error(msg)
                        raise exc.MissingDataError(msg)

                    set_table: SetTable = self.sets[coord_key]
                    set_filters_headers: dict = set_table.set_filters_headers

                    if not set_filters_headers:
                        continue

                    var_coord_info: dict = variable.var_info.get(coord_key, {})
                    var_coord_filter_raw: dict = var_coord_info.get(
                        filter_label, {})

                    var_coord_filter = {
                        set_filters_headers[num]: var_coord_filter_raw[num]
                        for num in set_filters_headers.keys()
                        if num in var_coord_filter_raw.keys()
                    }

                    if var_coord_filter and coord_category in categories_to_filter:
                        set_data: pd.DataFrame = set_table.data.copy()

                        for column, conditions in var_coord_filter.items():
                            if isinstance(conditions, list):
                                set_data = set_data[
                                    set_data[column].isin(conditions)
                                ]
                            else:
                                set_data = set_data[
                                    set_data[column] == conditions
                                ]

                        items_column_header = set_table.set_name_header
                        variable.coordinates[coord_category][coord_key] = \
                            list(set_data[items_column_header])

    def fetch_set_data(
            self,
            set_key: str,
    ) -> Optional[pd.DataFrame]:
        """Fetch set data from Index.

        Args:
            set_key (str): The key of the set in the sets dictionary.

        Returns:
            Optional[pd.DataFrame]: A DataFrame containing the set data if the 
                set exists, otherwise None.
        """
        if not isinstance(set_key, str) or set_key not in self.sets:
            self.logger.warning(
                f"Set '{set_key}' not found in Index. "
                f"Available sets: {list(self.sets.keys())}.")
            return

        set_table: SetTable = self.sets[set_key]
        return set_table.data

    def fetch_variable_data(
            self,
            var_key: str,
            scenario_key: Optional[int] = None,
            intra_problem_key: Optional[int] = None,
            if_hybrid_var: Defaults.LiteralTypes.HybridVarType = 'endogenous',
    ) -> Optional[pd.DataFrame]:
        """Fetch variable data from Index.

        This method retrieves the data for a specified variable based on optional 
        inter-problem and intra-problem sets cardinality, supporting the data 
        inspection process after a model has run, but before data has exported to the 
        database. This is particularly useful in case multiple runs of the model, 
        to facilitate the control of the numerical data from the user.
        In case a variable is defined as both endogeous and exogenous, depending on 
        the numerical problem, the user can specify the one to inspect (default 
        as the endogenous one).
        If the variable is specified for multiple inter- and intra-problem sets,
        scenario_key defines the cardinality of inter-problem sets, while 
        intra_problem_key defines the cardinality of intra-problem sets.

        Args:
            var_key (str): The key of the variable in the variables dictionary.
            scenario_key (Optional[int]): Defines the cardinality of inter-problem 
                sets. Default to None.
            intra_problem_key (Optional[int]): Defines the cardinality of intra-problem
                sets. Default to None.
            if_hybrid_var (Defaults.LiteralTypes.HybridVarType): Defines the type 
                of variable data to inspect in case variable type depends on the 
                problem.

        Returns:
            pd.DataFrame: A DataFrame containing the requested variable data, or
                None if any issues are encountered.
        """
        variable_header = Defaults.Labels.CVXPY_VAR
        allowed_var_types = Defaults.SymbolicDefinitions.VARIABLE_TYPES
        sub_problem_key_label = Defaults.Labels.SUB_PROBLEM_KEY

        if var_key not in self.variables:
            self.logger.warning(
                f"Variable '{var_key}' not found in Index. Available variables: "
                f"{list(self.variables.keys())}."
            )
            return

        variable: Variable = self.variables[var_key]

        df_index = variable.build_axis(
            target_labels=variable.dims_labels[0],
            target_items=variable.dims_items[0],
        )

        df_columns = variable.build_axis(
            target_labels=variable.dims_labels[1],
            target_items=variable.dims_items[1],
        )

        if variable.type == allowed_var_types['CONSTANT']:
            data: cp.Constant = variable.data
            if variable.value == 'set_length':
                values_dataframe = pd.DataFrame(data=data.value)
            else:
                values_dataframe = pd.DataFrame(
                    data=data.value,
                    index=df_index,
                    columns=df_columns,
                )

            return values_dataframe

        else:
            if variable.data is None:
                self.logger.warning(
                    f"Data not initialized for variable '{var_key}'.")
                return

            # Identifying variable data
            if isinstance(variable.data, dict):
                problem_key = util.find_dict_keys_corresponding_to_value(
                    dictionary=variable.type,
                    target_value=if_hybrid_var,
                )
                problem_key = problem_key[0] if problem_key else None
                variable_data = variable.data[problem_key]
            else:
                variable_data = variable.data

            # Filtering eventual sub-problem data (inter-problem sets cardinality)
            scenario_series = pd.to_numeric(
                variable_data[sub_problem_key_label], errors='coerce').dropna()
            scenario_key_list = set(scenario_series.astype(int).tolist())

            # If scenarios are present, enforce selection and filter
            if scenario_key_list:
                if scenario_key is None:
                    self.logger.warning(
                        f"'scenario_key' not specified for variable '{var_key}'. "
                        f"Available scenarios keys: {scenario_key_list}."
                    )
                    return

                if scenario_key not in scenario_key_list:
                    self.logger.warning(
                        f"Scenario '{scenario_key}' not found for variable '{var_key}'. "
                        f"Available scenarios keys: {scenario_key_list}."
                    )
                    return

                variable_data = variable_data.loc[
                    variable_data[sub_problem_key_label].eq(scenario_key)
                ]

            elif scenario_key is not None:
                self.logger.warning(
                    f"'scenario_key' specified for variable '{var_key}', "
                    "but variable has no inter-problem sets defined."
                )
                return

            if variable_data.empty:
                self.logger.warning(
                    f"Variable '{var_key}' data is empty after filtering.")
                return

            # If multiple intra-problem sets are defined, filter accordingly
            if len(variable_data) > 1:

                if intra_problem_key is None:
                    self.logger.warning(
                        f"'intra_problem_key' not specified for variable '{var_key}'. "
                        f"Select from 0 to {len(variable_data) - 1}."
                    )
                    return

                if not 0 <= int(intra_problem_key) < len(variable_data):
                    self.logger.warning(
                        f"'intra_problem_key' out of bounds for variable '{var_key}'. "
                        f"Valid range: 0 to {len(variable_data) - 1}."
                    )
                    return

                variable_series = variable_data.iloc[int(intra_problem_key)]

            else:
                if intra_problem_key is not None:
                    self.logger.warning(
                        f"'intra_problem_key' specified for variable '{var_key}', "
                        "but variable has no intra-problem sets defined."
                    )
                    return

                variable_series = variable_data.iloc[0]

            # Building DataFrame with variable values
            variable_values = variable_series[variable_header].value
            if issparse(variable_values):
                variable_values = variable_values.toarray()

        values_dataframe = pd.DataFrame(
            data=variable_values,
            index=df_index,
            columns=df_columns,
        )

        return values_dataframe

    def __repr__(self):
        """Return a string representation of the Index instance."""
        class_name = type(self).__name__
        return f'{class_name}'
