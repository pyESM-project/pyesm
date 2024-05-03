from pathlib import Path
from typing import Dict, List, Type

import pandas as pd

from esm.constants import Constants
from esm.base.data_table import DataTable
from esm.base.set_table import SetTable
from esm.base.variable import Variable
from esm.log_exc import exceptions as exc
from esm.log_exc.logger import Logger
from esm.support import util
from esm.support.file_manager import FileManager
from esm.support.dotdict import DotDict


class Index:

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            paths: Dict[str, Path],
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.debug("Object initialization...")

        self.files = files
        self.paths = paths

        self.sets: Dict[str, SetTable] = self.load_sets_tables()
        self.data: Dict[str, DataTable] = self.load_data_tables()
        self.variables: Dict[str, Variable] = self.fetch_variables()

        self.fetch_vars_coordinates_info()

        self.logger.debug("Object initialized.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    @property
    def sets_split_problem_list(self) -> Dict[str, str]:
        sets_split_problem_list = {}
        name_header = Constants.get('_STD_NAME_HEADER')

        for key, value in self.sets.items():
            if getattr(value, 'split_problem', False):
                headers = value.table_headers.get(name_header)

                if headers is not None and len(headers) > 0:
                    sets_split_problem_list[key] = headers[0]

        if not sets_split_problem_list:
            msg = "At least one Set must identify a problem. " \
                f"Check 'split_problem' properties in 'sets_structure.yml'"
            self.logger.error(msg)
            raise exc.NumericalProblemError(msg)

        return sets_split_problem_list

    @property
    def list_sets(self) -> List[str]:
        return list(self.sets.keys())

    @property
    def list_data_tables(self) -> List[str]:
        return list(self.data.keys())

    @property
    def list_variables(self) -> List[str]:
        return list(self.variables.keys())

    def _load_and_validate(
            self,
            file_key: int,
            validation_structure: Dict,
            object_class: Type[SetTable | DataTable],
    ) -> DotDict[str, SetTable | DataTable]:

        self.logger.debug(
            "Loading and validating data from file, "
            f"generating '{object_class.__name__}' objects.")

        data = self.files.load_file(
            file_name=Constants.get('_SETUP_FILES')[file_key],
            dir_path=self.paths['model_dir']
        )

        if all([
            util.validate_dict_structure(
                dictionary=dictionary,
                validation_structure=validation_structure)
            for dictionary in data.values()
        ]):
            return DotDict({
                key: object_class(logger=self.logger, **value)
                for key, value in data.items()
            })
        else:
            msg = f"'{object_class.__name__}' data validation not successful: " \
                f"input data must comply with default structure. " \
                f"Check setup file: '{Constants.get('_SETUP_FILES')[file_key]}'"
            self.logger.error(msg)
            raise exc.SettingsError(msg)

    def load_sets_tables(self) -> Dict[str, SetTable]:
        return self._load_and_validate(
            file_key=0,
            validation_structure=Constants.get('_SET_DEFAULT_STRUCTURE'),
            object_class=SetTable,
        )

    def load_data_tables(self) -> Dict[str, DataTable]:
        data_tables = self._load_and_validate(
            file_key=1,
            validation_structure=Constants.get(
                '_DATA_TABLE_DEFAULT_STRUCTURE'),
            object_class=DataTable,
        )

        for table in data_tables.values():
            table: DataTable

            set_headers_key = Constants.get('_STD_NAME_HEADER')
            table.table_headers = {
                set_key: self.sets[set_key].table_headers[set_headers_key]
                for set_key in table.coordinates
            }
            table.table_headers = util.add_item_to_dict(
                dictionary=table.table_headers,
                item=Constants.get('_STD_ID_FIELD'),
                position=0,
            )
            table.coordinates_headers = {
                key: value[0] for key, value in table.table_headers.items()
                if key in table.coordinates
            }

        return data_tables

    def fetch_variables(self) -> Dict[str, Variable]:
        self.logger.debug(
            "Fetching and validating data, generating "
            f"'{Variable.__name__}' objects.")

        variables_info = DotDict({})

        for table_key, data_table in self.data.items():
            data_table: DataTable

            if not all([
                util.validate_dict_structure(
                    dictionary=var_info,
                    validation_structure=Constants.get('_VARIABLE_DEFAULT_STRUCTURE'))

                for var_info in data_table.variables_info.values()
                if var_info is not None
            ]):
                msg = f"Invalid variables structures for table '{table_key}': " \
                    "variables fields does not match the expected default format."
                self.logger.error(msg)
                raise exc.SettingsError(msg)

            variable = DotDict({
                var_key: Variable(
                    logger=self.logger,
                    related_table=table_key,
                    type=data_table.type,
                    **(var_info or {}),
                )
                for var_key, var_info in data_table.variables_info.items()
            })
            variables_info.update(variable)

        return variables_info

    def fetch_vars_coordinates_info(self) -> None:
        self.logger.debug(
            f"Fetching 'coordinates_info' to Index.variables.")

        for variable in self.variables.values():
            variable: Variable

            related_table = variable.related_table
            related_table_headers: dict = self.data[related_table].table_headers

            rows, cols, intra, inter = {}, {}, {}, {}

            for key, value in related_table_headers.items():
                table_header = value[0]

                if key not in Constants.get('_STD_ID_FIELD'):

                    if key == variable.shape[0]:
                        rows[key] = table_header

                    if key == variable.shape[1]:
                        cols[key] = table_header

                    if key not in variable.shape:
                        if key not in self.sets_split_problem_list:
                            intra[key] = table_header
                        else:
                            inter[key] = table_header

            if len(intra) > 1:
                msg = "Only one intra-problem set allowed. Current " \
                    f"intra-problem sets: '{intra}'."
                self.logger.error(msg)
                raise exc.ConceptualModelError(msg)

            variable.coordinates_info = {
                'rows': rows,
                'cols': cols,
                'intra': intra,
                'inter': inter,
            }

    def fetch_foreign_keys_to_data_tables(self) -> None:
        self.logger.debug(
            f"Loading tables 'foreign_keys' to Index.data_tables.")

        for table in self.data.values():
            table: DataTable

            for set_key, set_header in table.coordinates_headers.items():
                table.foreign_keys[set_header] = \
                    (set_header, self.sets[set_key].table_name)

    def load_sets_data_to_index(
            self,
            excel_file_name: str,
            excel_file_dir_path: Path | str,
            empty_data_fill='',
    ) -> None:

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
            else:
                self.logger.info("Overwriting Sets in Index.")

        sets_values = self.files.excel_to_dataframes_dict(
            excel_file_name=excel_file_name,
            excel_file_dir_path=excel_file_dir_path,
            empty_data_fill=empty_data_fill,
            dtype=str
        )

        for set_instance in self.sets.values():
            assert isinstance(set_instance, SetTable)

            table_name = set_instance.table_name
            if table_name in sets_values.keys():
                set_instance.data = sets_values[table_name]
            else:
                msg = f"Table '{table_name}' from sets excel file not " \
                    "inclued in the defined Sets."
                self.logger.error(msg)
                raise exc.SettingsError(msg)

    def load_coordinates_to_data_index(self) -> None:
        self.logger.debug("Loading variable coordinates to Index.data.")

        for table in self.data.values():
            table: DataTable

            table.coordinates_values.update({
                set_header: self.sets[set_key].set_items
                for set_key, set_header in table.coordinates_headers.items()
            })

    def load_all_coordinates_to_variables_index(self) -> None:

        self.logger.debug("Loading variable coordinates to Index.variables.")

        for var_key, variable in self.variables.items():
            assert isinstance(variable, Variable)

            # Replicate coordinates_info with inner values as None
            coordinates = {
                category: {key: None for key in coord_values}
                for category, coord_values in variable.coordinates_info.items()
            }

            # Populating the coordinates with actual set names and values
            # from the index's sets
            for category, coord_dict in coordinates.items():
                for coord_key in coord_dict:
                    try:
                        coordinates: Dict
                        coordinates[category][coord_key] = self.sets[coord_key].set_items
                    except KeyError:
                        msg = f"Set key '{coord_key}' not found in Index set for " \
                            f"variable '{var_key}'."
                        self.logger.error(msg)
                        raise exc.SettingsError(msg)

            variable.coordinates = coordinates

    def filter_coordinates_in_variables_index(self) -> None:

        self.logger.debug(
            "Filtering variables coordinates in Index.variables.")

        for var_key, variable in self.variables.items():
            assert isinstance(variable, Variable), \
                f"Expected Variable type, got {type(variable)} instead."

            for coord_category, coord_dict in variable.coordinates.items():
                assert isinstance(coord_dict, dict), \
                    f"Expected dict, got {type(coord_dict)} instead."

                coord_key = next(iter(coord_dict), None)

                if coord_key is None:
                    continue

                set_filters_headers = self.sets[coord_key].set_filters_headers

                if not set_filters_headers:
                    continue

                var_coord_filter: Dict = getattr(
                    variable, coord_category, {}
                ).get('filters', {})

                var_coord_filter = {
                    set_filters_headers[num]: var_coord_filter[num]
                    for num in set_filters_headers.keys()
                    if num in var_coord_filter.keys()
                }

                # only rows, cols and intra problem sets can be filtered
                if var_coord_filter and coord_category in ['rows', 'cols', 'intra']:
                    set_data = self.sets[coord_key].data.copy()

                    for column, conditions in var_coord_filter.items():
                        if isinstance(conditions, list):
                            set_data = set_data[
                                set_data[column].isin(conditions)
                            ]
                        else:
                            set_data = set_data[
                                set_data[column] == conditions
                            ]

                    items_column_header = self.sets[coord_key].set_name_header
                    variable.coordinates[coord_category][coord_key] = \
                        list(set_data[items_column_header])

    def map_vars_aggregated_dims(self) -> None:

        self.logger.debug(
            "Identifying aggregated dimensions for constants coordinates.")

        for var_key, variable in self.variables.items():
            variable: Variable

            if not variable.type == 'constant':
                continue

            set_items_agg_map = pd.DataFrame()
            set_items = pd.DataFrame()

            for dim_key, dim in variable.dims_sets.items():
                dim_set: SetTable = getattr(self.sets, str(dim), None)

                if not dim_set:
                    break

                key_name = Constants.get('_STD_NAME_HEADER')
                key_aggregation = Constants.get('_STD_AGGREGATION_HEADER')

                name_header_filter = dim_set.table_headers.get(
                    key_name, [None])[0]

                aggregation_header_filter = dim_set.table_headers.get(
                    key_aggregation, [None])[0]

                if key_aggregation in dim_set.table_headers:
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
