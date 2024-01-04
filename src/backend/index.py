from pathlib import Path
from typing import Union, Dict, List, Any

import numpy as np
import pandas as pd

from src.log_exc.logger import Logger
from src.log_exc import exceptions as exc
from src.util import constants
from src.util.file_manager import FileManager
from src.util import util


class BaseItem:
    def __init__(self, **kwargs) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self) -> str:
        output = ''
        for key, value in self.__dict__.items():
            if key in ['data', 'table']:
                pass
            elif key != 'values':
                output += f'\n{key}: {value}'
            else:
                output += f'\n{key}: \n{value}'
        return output


class Set(BaseItem):
    def __init__(
            self,
            table: pd.DataFrame = None,
            **kwargs,
    ) -> None:
        super().__init__(**kwargs)

        self.table = table


class Variable(BaseItem):
    def __init__(
            self,
            **kwargs,
    ) -> None:
        super().__init__(**kwargs)

        self.variable_fields = {}
        self.table_headers = {}
        self.coordinates = {}
        self.foreign_keys = {}
        self.sets_parsing_hierarchy = {}
        self.data = {}

    @property
    def shape_size(self) -> List[int]:
        shape_size = []

        for item in self.shape:
            if isinstance(item, str):
                if item not in self.variable_fields.keys():
                    error = f"'{item}' is not a variable coordinate."
                    raise ValueError(error)
                coordinate_key = self.variable_fields[item][0]
                shape_size.append(len(self.coordinates[coordinate_key]))

            elif isinstance(item, int):
                shape_size.append(item)

            else:
                error = "Wrong shape format: valid formats are 'str' or 'int'"
                raise ValueError(error)

        return shape_size


class Index:

    def __init__(
            self,
            files: FileManager,
            logger: Logger,
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info(f"'{self}' object initialization...")

        self.files = files

        self.sets = util.DotDict({
            key: Set(**value)
            for key, value in constants._SETS.items()
        })

        self.variables = util.DotDict({
            key: Variable(**value)
            for key, value in constants._VARIABLES.items()
        })

        self.load_variables_fields()

        self.logger.info(f"'{self}' object initialized.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def load_variables_fields(self) -> None:

        self.logger.debug(
            f"Loading variables table headers and label headers to Index.")

        for variable in self.variables.values():
            set_headers_key = variable.set_headers_key

            for set_key in variable.coordinates_info.keys():
                set_headers = self.sets[set_key].table_headers[set_headers_key]
                variable.variable_fields[set_key] = set_headers

    def load_sets_to_index(
            self,
            excel_file_name: str,
            excel_file_dir_path: Path,
            empty_data_fill='',
    ) -> None:

        if all(set_instance.table is None for set_instance in self.sets.values()):
            self.logger.info(f"'{self}' object: loading new Sets to Index.")
        else:
            self.logger.warning(
                f"'{self}' object: Sets tables already "
                "defined for at least one Set in Index.")
            user_input = input("Overwrite Sets? (y/[n]): ")
            if user_input.lower() != 'y':
                self.logger.info(
                    f"'{self}' object: Sets tables not overwritten.")
                return
            else:
                self.logger.info(
                    f"'{self}' object: overwriting Sets to Index.")

        sets_values = self.files.excel_to_dataframes_dict(
            excel_file_name=excel_file_name,
            excel_file_dir_path=excel_file_dir_path,
            empty_data_fill=empty_data_fill,
            dtype=str
        )

        for set_instance in self.sets.values():
            table_name = set_instance.table_name
            if table_name in sets_values.keys():
                set_instance.table = sets_values[table_name]

    def load_vars_coordinates_to_index(self) -> None:

        self.logger.debug(f"Loading variables 'coordinates' to Index.")

        for variable in self.variables.values():

            for set_key, set_filter in variable.coordinates_info.items():

                set_header = variable.variable_fields[set_key][0]

                if set_filter is None:
                    set_values = list(self.sets[set_key].table[set_header])

                elif isinstance(set_filter, dict):

                    if 'set_categories' in set_filter:
                        category_filter_id = set_filter['set_categories']
                        category_filter = self.sets[set_key].set_categories[category_filter_id]
                        category_header_name = self.sets[set_key].table_headers['category'][0]
                        set_filtered = self.sets[set_key].table.query(
                            f'{category_header_name} == "{category_filter}"'
                        )

                    set_filtered = self.sets[set_key].table.query(
                        f'{category_header_name} == "{category_filter}"'
                    ).copy()

                    if 'aggregation_key' in set_filter:
                        aggregation_key = set_filter['aggregation_key']
                        aggregation_key_name = self.sets[set_key].table_headers[aggregation_key][0]

                        set_filtered.loc[
                            set_filtered[aggregation_key_name] != '', set_header
                        ] = set_filtered[aggregation_key_name]

                    set_values = list(set(set_filtered[set_header]))

                else:
                    error_msg = f"Missing or wrong data in 'constants/_VARIABLES'."
                    self.logger.error(error_msg)
                    raise exc.MissingDataError(error_msg)

                variable.coordinates[set_header] = set_values

    def load_vars_table_headers_to_index(self) -> None:

        self.logger.debug(f"Loading variables 'table_headers' to Index.")

        for var_key, variable in self.variables.items():
            if variable.variable_fields is None:
                error = f"'variable_fields' is empty for variable '{var_key}'."
                self.logger.error(error)
                raise ValueError(error)

            variable.table_headers = variable.variable_fields.copy()
            variable.table_headers = util.add_item_to_dict(
                dictionary=variable.table_headers,
                item=constants._STD_ID_FIELD,
                position=0,
            )

    def load_foreign_keys_to_vars_index(self) -> None:

        self.logger.debug(f"Loading tables 'foreign_keys' to Index.")

        for variable in self.variables.values():
            for set_key, set_header in variable.variable_fields.items():
                variable.foreign_keys[set_header[0]] = \
                    (set_header[0], self.sets[set_key].table_name)

    def load_sets_parsing_hierarchy(self) -> None:

        self.logger.debug(
            f"Loading variables 'sets_parsing_hierarchy' to Index.")

        for variable in self.variables.values():
            variable.sets_parsing_hierarchy = {
                item: variable.variable_fields[item][0]
                for item in constants._SETS_PARSING_HIERARCHY
            }
