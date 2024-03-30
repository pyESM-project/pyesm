from pathlib import Path
from typing import Dict, List

import pandas as pd

from esm import constants
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
            paths: Dict[str, str],
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info(f"'{self}' object initialization...")

        self.files = files
        self.paths = paths

        self.sets: DotDict[str, SetTable] = self.load_sets_tables()
        self.data: DotDict[str, DataTable] = self.load_data_tables()
        self.variables: DotDict[str, Variable] = self.fetch_variables()

        self.fetch_vars_coordinates_info()

        self.logger.info(f"'{self}' object initialized.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    @property
    def sets_headers_in_other_tables(self) -> Dict[str, str]:
        return {
            key: value.table_headers[constants._STD_TABLE_HEADER][0]
            for key, value in self.sets.items()
        }

    @property
    def sets_split_problem_list(self) -> Dict[str, str]:
        sets_split_problem_list = {
            key: value.table_headers[constants._STD_TABLE_HEADER][0]
            for key, value in self.sets.items()
            if getattr(value, 'split_problem', False)
        }

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
            validation_structure: dict,
            object_class: SetTable | DataTable,
    ) -> DotDict[str, SetTable | DataTable]:

        self.logger.info(
            "Loading and validating data from file, "
            f"generating '{object_class.__name__}' objects.")

        data = self.files.load_file(
            file_name=constants._SETUP_FILES[file_key],
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
                f"Check setup file: '{constants._SETUP_FILES[file_key]}'"
            self.logger.error(msg)
            raise exc.SettingsError(msg)

    def load_sets_tables(self) -> DotDict[str, SetTable]:
        return self._load_and_validate(
            file_key=0,
            validation_structure=constants._SET_DEFAULT_STRUCTURE,
            object_class=SetTable,
        )

    def load_data_tables(self) -> DotDict[str, DataTable]:
        data_tables = self._load_and_validate(
            file_key=1,
            validation_structure=constants._DATA_TABLE_DEFAULT_STRUCTURE,
            object_class=DataTable,
        )

        for table in data_tables.values():
            table: DataTable

            set_headers_key = constants._STD_TABLE_HEADER
            table.table_headers = {
                set_key: self.sets[set_key].table_headers[set_headers_key]
                for set_key in table.coordinates
            }
            table.table_headers = util.add_item_to_dict(
                dictionary=table.table_headers,
                item=constants._STD_ID_FIELD,
                position=0,
            )
            table.coordinates_headers = {
                key: value[0] for key, value in table.table_headers.items()
                if key in table.coordinates
            }

        return data_tables

    def fetch_variables(self) -> DotDict[str, Variable]:
        self.logger.info(
            "Fetching and validating data, generating "
            f"'{Variable.__name__}' objects.")

        variables_info = DotDict({})

        for table_key, data_table in self.data.items():
            data_table: DataTable

            if all([
                util.validate_dict_structure(
                    dictionary=var_info,
                    validation_structure=constants._VARIABLE_DEFAULT_STRUCTURE)
                for var_info in data_table.variables_info.values()
                if var_info is not None
            ]):
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
                header = value[0]

                if key not in constants._STD_ID_FIELD:

                    if key == variable.shape[0]:
                        rows[key] = header

                    if key == variable.shape[1]:
                        cols[key] = header

                    if key not in variable.shape:
                        if key not in self.sets_split_problem_list:
                            intra[key] = header
                        else:
                            inter[key] = header

            variable.coordinates_info = {
                'rows': rows,
                'cols': cols,
                'intra': intra,
                'inter': inter,
            }

    def fetch_foreign_keys_to_data_tables(self) -> None:
        self.logger.info(
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
            self.logger.info(
                f"'{self}' object: loading new Sets data to Index.sets.")
        else:
            self.logger.warning(
                f"'{self}' object: Sets tables already "
                "defined for at least one Set in Index.")
            user_input = input("Overwrite Sets in Index? (y/[n]): ")
            if user_input.lower() != 'y':
                self.logger.info(
                    f"'{self}' object: Sets tables not overwritten.")
                return
            else:
                self.logger.info(
                    f"'{self}' object: overwriting Sets to Index.sets.")

        sets_values = self.files.excel_to_dataframes_dict(
            excel_file_name=excel_file_name,
            excel_file_dir_path=excel_file_dir_path,
            empty_data_fill=empty_data_fill,
            dtype=str
        )

        for set_instance in self.sets.values():
            set_instance: SetTable

            table_name = set_instance.table_name
            if table_name in sets_values.keys():
                set_instance.data = sets_values[table_name]

    def load_coordinates_to_data_index(self) -> None:
        self.logger.info(
            f"'{self}' object: loading variable coordinates to Index.data.")

        for table in self.data.values():
            table: DataTable

            table.coordinates_values.update({
                set_header: self.sets[set_key].set_values
                for set_key, set_header in table.coordinates_headers.items()
            })

    def load_coordinates_to_variables_index(self) -> None:

        self.logger.info(
            f"'{self}' object: loading variable coordinates to "
            "Index.variables.")

        for var_key, variable in self.variables.items():
            variable: Variable

            # replicate coordinates_info with inner values as None
            coordinates = {
                key: {inner_key: None for inner_key in value}
                for key, value in variable.coordinates_info.items()
            }

            # parse coordinates and retrieve each related values
            for coord_group_key, coord_group_value in coordinates.items():

                var_filters = getattr(variable, coord_group_key, {}).copy()
                var_filters.pop('set', None)

                # if rows/cols, coordinates may be filtered
                if coord_group_key in ['rows', 'cols'] and var_filters != {}:

                    set_key = list(coord_group_value.keys())[0]
                    set_value: SetTable = self.sets[set_key]

                    if 'set_categories' in var_filters and \
                            var_filters['set_categories']:

                        name_header = set_value.table_headers[constants._STD_TABLE_HEADER][0]
                        category_header = set_value.table_headers[constants._STD_CATEGORY_HEADER][0]
                        category_filter_id = var_filters['set_categories']
                        category_filter = set_value.set_categories[category_filter_id]

                        set_filtered = set_value.data.query(
                            f'{category_header} == "{category_filter}"'
                        ).copy()

                    coord_group_value.update(
                        {set_key: list(set(set_filtered[name_header]))})

                # for coordinates sets different than 'all', no aggregation nor filtering
                # elif coord_group_key != 'all':
                else:
                    coord_group_value.update({
                        set_key: self.sets[set_key].set_values
                        for set_key in coord_group_value
                    })

            variable.coordinates = coordinates

    def mapping_vars_aggregated_dims(self) -> None:
        for var_key, variable in self.variables.items():
            variable: Variable

            if not variable.type == 'constant':
                continue

            set_items_aggregation_map = pd.DataFrame()
            set_items = pd.DataFrame()

            for dim_key, dim in variable.dims_sets.items():
                dim_set: SetTable = getattr(self.sets, dim, None)

                if not dim_set:
                    break

                std_name = constants._STD_TABLE_HEADER
                std_aggregation = constants._STD_AGGREGATION_HEADER

                name_header_filter = dim_set.table_headers.get(
                    std_name, [None])[0]

                aggregation_header_filter = dim_set.table_headers.get(
                    std_aggregation, [None])[0]

                if std_aggregation in dim_set.table_headers:
                    set_items_aggregation_map = dim_set.data[[
                        name_header_filter, aggregation_header_filter]]
                    set_items_aggregation_map.rename(
                        columns={name_header_filter: dim_key},
                        inplace=True,
                    )
                else:
                    set_items = dim_set.data[[name_header_filter]].copy()
                    set_items.rename(
                        columns={name_header_filter: dim_key},
                        inplace=True,
                    )

                if not set_items_aggregation_map.empty and set_items is not None:
                    if set(set_items_aggregation_map[aggregation_header_filter]) == \
                            set(set_items.values.flatten()):

                        set_items_aggregation_map.rename(
                            columns={
                                aggregation_header_filter: set_items.columns[0]
                            },
                            inplace=True,
                        )
                        variable.related_dims_map = set_items_aggregation_map
                        break
