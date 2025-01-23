"""
index.py

@author: Matteo V. Rocco
@institution: Politecnico di Milano

This module defines the Index class, which acts as a central registry for managing
sets, data tables, and variables within the modeling system. It facilitates access
and manipulation of these entities throughout the application.

The Index class loads and initializes set tables, data tables, and variable
objects from configured sources and provides properties to access metadata and
operational characteristics related to these entities.
"""
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import cvxpy as cp

from esm.constants import Constants
from esm.backend.data_table import DataTable
from esm.backend.set_table import SetTable
from esm.backend.variable import Variable
from esm.log_exc import exceptions as exc
from esm.log_exc.logger import Logger
from esm.support import util
from esm.support.file_manager import FileManager
from esm.support.dotdict import DotDict


class Index:
    """
    A central index for managing and accessing sets, data tables, and variables
    within the system.

    Attributes:
        logger (Logger): Logger instance for logging activity within the class.
        files (FileManager): FileManager instance for file operations.
        paths (Dict[str, Path]): Dictionary mapping of paths used in file operations.
        sets (Dict[str, SetTable]): Dictionary of set tables loaded upon initialization.
        data (Dict[str, DataTable]): Dictionary of data tables loaded upon initialization.
        variables (Dict[str, Variable]): Dictionary of variables fetched upon initialization.

    Parameters:
        logger (Logger): Logger instance from the parent or main handler.
        files (FileManager): FileManager instance for handling file operations.
        paths (Dict[str, Path]): Dictionary containing necessary path configurations.
    """

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            settings: Dict[str, str],
            paths: Dict[str, Path],
    ) -> None:
        """
        Initializes the Index object, loads sets, data tables, and variables.
        """
        self.logger = logger.get_child(__name__)

        self.files = files
        self.settings = settings
        self.paths = paths

        structures = Constants.ConfigFiles.SETUP_INFO
        self.sets = self.load_and_validate_structure(structures[0])
        self.data = self.load_and_validate_structure(structures[1])

        self.check_data_coherence()
        self.data_tables_completion()

        self.variables: DotDict[str, Variable] = self.generate_variables()
        self.fetch_vars_coordinates_info()

        self.scenarios_info: pd.DataFrame = None

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    @property
    def sets_split_problem_dict(self) -> Dict[str, str]:
        """
        Provides a dictionary of sets that have a split problem, mapped to
        their respective headers. Returns an empty dictionary if no sets are
        identified with a split problem.

        Returns:
            Dict[str, str]: A dictionary where keys are set identifiers and values
                are headers associated with split problems. Returns an empty
                dictionary if the required information is not available or applicable.
        """
        sets_split_problem_list = {}
        name_header = Constants.Labels.NAME

        for key, set_table in self.sets.items():
            set_table: SetTable

            if getattr(set_table, 'split_problem', False) and \
                    set_table.table_headers is not None:

                headers = set_table.table_headers.get(name_header, [])

                if headers:
                    sets_split_problem_list[key] = headers[0]

        return sets_split_problem_list

    @property
    def list_sets(self) -> List[str]:
        """
        Returns a list of all set identifiers currently loaded in the index.
        Returns an empty list if no sets are loaded.

        Returns:
            List[str]: List of set identifiers.
        """
        return list(self.sets.keys()) if self.sets else []

    @property
    def list_data_tables(self) -> List[str]:
        """
        Returns a list of all data table identifiers currently loaded in the index.
        Returns an empty list if no data tables are loaded.

        Returns:
            List[str]: List of data table identifiers.
        """
        return list(self.data.keys()) if self.sets else []

    @property
    def list_variables(self) -> List[str]:
        """
        Returns a list of all variable identifiers currently loaded in the index.
        Returns an empty list if no variables are loaded.

        Returns:
            List[str]: List of variable identifiers.
        """
        return list(self.variables.keys()) if self.variables else []

    def load_and_validate_structure(
            self,
            data_structure_key: str,
    ) -> DotDict[str, SetTable | DataTable]:

        structures = Constants.DefaultStructures
        config = Constants.ConfigFiles

        source = self.settings['model_settings_from']

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
            dir_path=self.paths['model_dir'],
        )

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
            if self.settings['detailed_validation']:
                self.logger.error(
                    f"Validation error report ===================================")
                for key, error_log in invalid_entries.items():
                    self.logger.error(
                        f"Validation error | {data_structure_key} | '{key}' | {error_log}")
            else:
                self.logger.error(
                    f"Validation | {data_structure_key} | Entries: "
                    f"{list(invalid_entries.keys())}")

            msg = f"'{data_structure_key}' data validation not successful. " \
                f"Check setup '{source}' file. "
            if not self.settings['detailed_validation']:
                msg += "Set 'detailed_validation=True' for more information."

            self.logger.error(msg)
            raise exc.SettingsError(msg)

        data = util.transform_dict_none_to_values(data, none_to={})

        validated_structure = DotDict({
            key: object_class(logger=self.logger, key_name=key, **value)
            for key, value in data.items()
        })

        return validated_structure

    def check_data_coherence(self) -> None:
        allowed_var_types = Constants.SymbolicDefinitions.ALLOWED_VARIABLES_TYPES
        allowed_constants = Constants.SymbolicDefinitions.ALLOWED_CONSTANTS.keys()
        allowed_dims = Constants.SymbolicDefinitions.ALLOWED_DIMENSIONS

        coordinates_key = Constants.Labels.COORDINATES_KEY
        filters_key = Constants.Labels.FILTERS
        variables_info_key = Constants.Labels.VARIABLES_INFO_KEY
        value_key = Constants.Labels.VALUE_KEY

        problems = {}

        for table_key, data_table in self.data.items():
            data_table: DataTable

            # table types must be allowed
            if isinstance(data_table.type, dict):
                table_type = data_table.type.values()
            else:
                table_type = [data_table.type]

            if not all(type in allowed_var_types for type in table_type):
                problems[table_key] = f"Variable type not allowed."

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

                    # value field must be allowed
                    elif property_key == value_key:
                        if property_value and property_value not in allowed_constants:
                            problems[f"{path}.{value_key}"] = \
                                f"Constant type '{property_value}' not allowed."

                    # other properties must be allowed coordinates
                    elif property_key not in data_table.coordinates:
                        problems[path] = f"Coordinate '{property_key}' not found in coordinates."

                    # for each var coordinate
                    elif property_key in data_table.coordinates \
                            and isinstance(property_value, dict):

                        # check if dim is allowed
                        if 'dim' in property_value:
                            if property_value['dim'] not in allowed_dims:
                                problems[f"{path}.{property_key}.dim"] = \
                                    f"Coordinate '{property_key}': " \
                                    f"dimension '{property_value['dim']}' not allowed."

                        # check if filters are allowed
                        if filters_key in property_value:
                            var_filters = dict(property_value[filters_key])
                            set_filters = {
                                key: list(value['values']) for key, value
                                in self.sets[property_key].table_structure[filters_key].items()
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
            if self.settings['detailed_validation']:
                for key, error_log in problems.items():
                    self.logger.error(
                        f"Data coherence check | {key} | {error_log}")
            else:
                self.logger.error(
                    f"Data coherence error | Sets, Data tables | Entries: "
                    f"{list(problems.keys())}")

            msg = "Sets and Data tables coherence check not successful. " \
                "Check setup files."
            if not self.settings['detailed_validation']:
                msg += "Set 'detailed_validation=True' for more information."

            self.logger.error(msg)
            raise exc.SettingsError(msg)

    def data_tables_completion(self) -> None:

        self.logger.debug(
            "Completing data tables with information taken from related Sets.")

        for table in self.data.values():
            table: DataTable
            set_headers_key = Constants.Labels.NAME

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
                item=Constants.Labels.ID_FIELD,
                position=0,
            )
            table.coordinates_headers = {
                key: value[0] for key, value in table.table_headers.items()
                if key in table.coordinates
            }

    def generate_variables(self) -> DotDict[str, Variable]:
        """
        Fetches and validates variable information from all loaded data tables,
        generating 'Variable' objects for each valid entry.
        The method checks each variable's data against a defined structure and
        initializes 'Variable' instances if the data conforms to the expected format.

        Returns:
            Dict[str, Variable]: A dictionary of 'Variable' objects keyed by
                their identifiers, collected across all data tables.

        Raises:
            SettingsError: If any variable data does not conform to the required
                structure, specifying the table and the nature of the validation
                failure.
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
        """
        Populates each variable in the index with detailed coordinate information,
        categorizing data table headers into rows, columns, intra-problem sets,
        and inter-problem sets based on the variable's shape and configuration.
        It derives this information from the related data tables specified for
        each variable.

        Raises:
            ConceptualModelError: If there are multiple intra-problem sets found,
                indicating a configuration error in the variable setup.
        """
        self.logger.debug("Fetching 'coordinates_info' to Index.variables.")

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

                if key in Constants.Labels.ID_FIELD:
                    continue
                if key == variable.shape_sets[0]:
                    rows[key] = table_header
                if key == variable.shape_sets[1]:
                    cols[key] = table_header
                if key not in variable.shape_sets:
                    if key not in self.sets_split_problem_dict:
                        intra[key] = table_header
                    else:
                        inter[key] = table_header

            variable.coordinates_info = {
                'rows': rows,
                'cols': cols,
                'intra': intra,
                'inter': inter,
            }

    def check_variables_coherence(self) -> None:
        """Various checks in how variables have defined. For the moment only
        checks if the variable coordinates are present for all dimensions.
        """
        self.logger.debug(f"Validating variables coherence with coordinates.")

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
            if self.settings['detailed_validation']:
                self.logger.error(
                    f"Validation error report ===================================")
                for key, error_log in problems.items():
                    self.logger.error(
                        f"Variables coherence check | {key} | {error_log}")
            else:
                self.logger.error(
                    f"Variables coherence error | Entries: "
                    f"{list(problems.keys())}")

            msg = "Variables coherence check not successful. " \
                "Check setup files and sets information."
            if not self.settings['detailed_validation']:
                msg += "Set 'detailed_validation=True' for more information."

            self.logger.error(msg)
            raise exc.SettingsError(msg)

    def fetch_foreign_keys_to_data_tables(self) -> None:
        """
        Assigns foreign key relationships to the data tables in the index.
        This is achieved by referencing set tables that are associated with
        each data table based on coordinate headers.
        Each foreign key relationship is defined by matching coordinate headers
        in the data tables with set tables, effectively linking related data
        entities across the model.
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
            empty_data_fill='',
    ) -> None:
        """
        Loads data for sets from an Excel file into the Index. If any set already
        contains data, prompts the user to decide whether to overwrite the existing data.

        Parameters:
            excel_file_name (str): The name of the Excel file to load.
            excel_file_dir_path (Path | str): The directory path where the Excel
                file is located.
            empty_data_fill (str, optional): The value to use for filling in
                empty cells in the Excel data.

        Raises:
            MissingDataError: If a table is referenced in a set but not found
                in the Excel file and not defined to be copied from another set,
                or if necessary headers are missing.
            SettingsError: If the set to be copied does not exist or its data
                is improperly formatted.
        """
        if all(
            set_instance.data is None
            for set_instance in self.sets.values()
        ):
            self.logger.debug("Loading Sets data to Index.sets.")
        else:
            self.logger.warning(
                "At least one Set is already defined in Index.")
            user_input = input("Overwrite Sets in Index? (y/[n]): ")
            if user_input.lower() != 'y':
                self.logger.info("Sets not overwritten in Index.")
                return
            self.logger.info("Overwriting Sets in Index.")

        sets_excel_data = self.files.excel_to_dataframes_dict(
            excel_file_name=excel_file_name,
            excel_file_dir_path=excel_file_dir_path,
            empty_data_fill=empty_data_fill,
        )

        sets_excel_keys = sets_excel_data.keys()

        for set_instance in self.sets.values():
            set_instance: SetTable

            if set_instance.table_name in sets_excel_keys:
                set_instance.data = sets_excel_data[set_instance.table_name]
                continue

            if not set_instance.copy_from:
                msg = f"Table '{set_instance.table_name}' not included in " \
                    "the excel sets file, nor defined as a copy of another " \
                    "existing set. Check sets definition."
                self.logger.error(msg)
                raise exc.MissingDataError(msg)

            if set_instance.table_headers is None:
                msg = f"Headers for table '{set_instance.table_name}' not defined."
                self.logger.error(msg)
                raise exc.MissingDataError(msg)

            set_to_be_copied = set_instance.copy_from

            if set_to_be_copied in self.sets and \
                    self.sets[set_to_be_copied].data is not None and \
                    isinstance(self.sets[set_to_be_copied].data, pd.DataFrame):

                set_instance.data = self.sets[set_to_be_copied].data.copy()
                set_instance.data.columns = [
                    header[0]
                    for header in set_instance.table_headers.values()
                ]
            else:
                msg = f"Table '{set_to_be_copied}' not included in " \
                    "the defined Sets, or data not defined or defined in the " \
                    "wrong format. Check set name and data."
                self.logger.error(msg)
                raise exc.SettingsError(msg)

    def load_coordinates_to_data_index(self) -> None:
        """
        Populates the 'coordinates_values' dictionary of each data table in the
        index with coordinate items from corresponding sets based on headers
        defined in 'coordinates_headers'.
        This method maps set items to their respective data tables,
        facilitating direct access to these items for operations that require
        context-specific data, such as data processing or analysis tasks.
        Ensures that each data table's coordinates are updated with actual items
        from the sets as specified in the table's coordinate headers.
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
        """
        Populates the 'coordinates' attribute of each variable in the index with
        actual set items. This method utilizes 'coordinates_info' from each variable
        to retrieve and assign corresponding set items from the index's sets.
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
        """
        Filters the coordinate data for variables based on predefined filter
        conditions stored in sets. This process adjusts the coordinate values
        for 'rows', 'cols', and 'intra' categories by applying the filters
        specified in the sets' filter headers.
        This method modifies the variable's coordinate data directly, ensuring
        that only relevant items that meet the filter conditions are retained.
        """
        self.logger.debug(
            "Filtering variables coordinates in Index.variables.")

        # only rows, cols and intra problem sets can be filtered
        categories_to_filter = ['rows', 'cols', 'intra']

        for variable in self.variables.values():
            variable: Variable

            # if no var_info are specified, variable is not filtered
            if variable.var_info is None:
                continue

            for coord_category, coord_dict in variable.coordinates.items():
                assert isinstance(coord_dict, dict), \
                    f"Expected dict, got {type(coord_dict)} instead."

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
                        'filters', {})

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

    def map_vars_aggregated_dims(self) -> None:
        """
        Maps aggregated dimensions for variables identified as constants. This
        process involves linking each variable's dimension sets to specific
        aggregated data mappings based on configurations in the sets.
        For each constant variable, the method looks up the corresponding sets,
        extracts necessary header information, and applies any defined aggregation
        logic. If successful, the aggregation map is stored within the variable's
        attributes, enhancing the variable's utility in aggregated data contexts.
        Variables not marked as 'constant' are skipped. If any referenced set
        is missing or improperly configured, the mapping process for that variable
        is aborted.
        """
        self.logger.debug(
            "Identifying aggregated dimensions for constants coordinates.")

        for variable in self.variables.values():
            variable: Variable

            if not variable.type == 'constant':
                continue

            set_items_agg_map = pd.DataFrame()
            set_items = pd.DataFrame()

            for dim_key, dim in variable.dims_sets.items():
                dim_set: SetTable = getattr(self.sets, str(dim), None)

                if not dim_set:
                    break

                name_label = Constants.Labels.NAME
                aggregation_label = Constants.Labels.AGGREGATION

                if dim_set.table_headers is not None:
                    name_header_filter = dim_set.table_headers.get(
                        name_label, [None])[0]

                    aggregation_header_filter = dim_set.table_headers.get(
                        aggregation_label, [None])[0]
                else:
                    name_header_filter = None
                    aggregation_header_filter = None

                if dim_set.data is None:
                    msg = f"Data for set '{dim_set}' are missing."
                    self.logger.error(msg)
                    raise exc.MissingDataError(msg)

                if aggregation_label in dim_set.table_headers and \
                        not all(dim_set.data[aggregation_header_filter].isna()):
                    set_items_agg_map = dim_set.data[[
                        name_header_filter, aggregation_header_filter]].copy()
                    set_items_agg_map.rename(
                        columns={name_header_filter: dim_key},
                        inplace=True,
                    )
                    # renaming column representing filtered dimension
                else:
                    set_items = dim_set.data[[name_header_filter]].copy()
                    set_items.rename(
                        columns={name_header_filter: dim_key},
                        inplace=True,
                    )

                if not set_items_agg_map.empty and set_items is not None:
                    if set(set_items_agg_map[aggregation_header_filter]) == \
                            set(set_items.values.flatten()):

                        # renaming column representing non-filtered dimension
                        set_items_agg_map.rename(
                            columns={
                                aggregation_header_filter: set_items.columns[0]
                            },
                            inplace=True,
                        )

                        # filtering rows and cols (in case of filtered vars)
                        filter_dict = {
                            'rows': variable.dims_items[0],
                            'cols': variable.dims_items[1],
                        }
                        set_items_agg_map_filtered = util.filter_dataframe(
                            df_to_filter=set_items_agg_map,
                            filter_dict=filter_dict,
                        )

                        variable.related_dims_map = set_items_agg_map_filtered
                        break

    def fetch_set_data(
            self,
            set_key: str,
    ) -> Optional[pd.DataFrame]:

        if not isinstance(set_key, str) or set_key not in self.sets:
            self.logger.warning(
                f"Set '{set_key}' not found in Index. "
                f"Available sets: {list(self.sets.keys())}.")
            return

        return self.sets[set_key].data

    def fetch_variable_data(
            self,
            var_key: str,
            problem_index: Optional[int] = None,
            sub_problem_index: Optional[int] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Retrieves the data for a specified variable based on optional problem
        and sub-problem indices.

        Parameters:
            var_key (str): The key of the variable in the variables dictionary.
            problem_index (Optional[int]): Index specifying which problem's data
                to access if data is dictionary-based.
            sub_problem_index (Optional[int]): Index specifying which
                sub-problem's data to access if data is a DataFrame with multiple rows.

        Returns:
            pd.DataFrame: A DataFrame containing the requested variable data, or
                None if any issues are encountered.

        Notes:
            The function logs a warning and returns None if the variable does
                not exist, data is not initialized, problem index is not specified
                when required, or any provided indices are out of bounds.
        """

        variable_header = Constants.Labels.CVXPY_VAR

        if var_key not in self.variables:
            self.logger.warning(
                f"Variable '{var_key}' not found in Index. Available variables: "
                f"{list(self.variables.keys())}."
            )
            return

        variable: Variable = self.variables[var_key]

        if variable.type == 'constant':
            data: cp.Constant = variable.data
            if variable.value == 'set_length':
                values_dataframe = pd.DataFrame(data=data.value)
            else:
                values_dataframe = pd.DataFrame(
                    data=data.value,
                    index=variable.dims_items[0],
                    columns=variable.dims_items[1],
                )

        if variable.data is None:
            self.logger.warning(
                f"Data not initialized for variable '{var_key}'.")
            return

        if isinstance(variable.data, dict):
            if problem_index is None:
                self.logger.warning(
                    f"Variable '{var_key}' is defined for multiple problems. "
                    "A symbolic problem index must be specified.")
                return

            if problem_index not in variable.data.keys():
                self.logger.warning(
                    f"Problem index must be included in {list(variable.data.keys())}.")
                return

            if len(variable.data) == 1 and problem_index is None:
                problem_index = 0

            variable_data = variable.data[problem_index]

        else:
            if problem_index is not None:
                self.logger.warning(
                    f"Variable '{var_key}' is not defined for multiple problems. "
                    "Problem index must be None.")
                return

            variable_data = variable.data

        if isinstance(variable_data, pd.DataFrame):
            if variable_data.empty:
                self.logger.warning(f"Variable '{var_key}' data is empty.")
                return

            if len(variable_data) > 1:
                if sub_problem_index is None:
                    self.logger.warning(
                        f"Variable '{var_key}' is defined for multiple "
                        "sub-problems. A sub-problem index must be specified "
                        f"from 0 to {len(variable_data) - 1}.")
                    return

                if sub_problem_index < 0 or sub_problem_index >= len(variable_data):
                    self.logger.warning(
                        f"Sub-problem index must be between 0 and {len(variable_data)-1}.")
                    return

            if len(variable_data) == 1:
                if sub_problem_index is None:
                    sub_problem_index = 0
                elif sub_problem_index != 0:
                    self.logger.warning(
                        f"A unique sub-problem is defined for variable '{var_key}'. "
                        "Set sub-problem index to 0 or None")
                    return

            variable_series = variable_data.loc[sub_problem_index]
            variable_values = variable_series[variable_header].value

            values_dataframe = pd.DataFrame(
                data=variable_values,
                index=variable.dims_items[0],
                columns=variable.dims_items[1],
            )

        return values_dataframe

    def fetch_scenarios_info(self) -> None:
        """ 
        Fetch scenarios information (these will be the same for all problems and 
        sub-problems). This dataframes serves as the base for building the problems
        dataframes.
        """
        self.logger.info("Fetching scenario/s information to Index.")

        scenarios_coordinates = {}
        list_sets_split_problem = list(self.sets_split_problem_dict.values())
        scenarios_coords_header = Constants.Labels.SCENARIO_COORDINATES

        for set_key, set_header in self.sets_split_problem_dict.items():
            set_table: SetTable = self.sets[set_key]
            set_values = set_table.data[set_header]
            scenarios_coordinates[set_header] = list(set_values)

        scenarios_df = util.unpivot_dict_to_dataframe(
            data_dict=scenarios_coordinates,
            key_order=list_sets_split_problem,
        )

        util.add_column_to_dataframe(
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

        self.scenarios_info = scenarios_df
