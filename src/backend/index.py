from pathlib import Path
from typing import Dict, Any

from src.log_exc.logger import Logger
from src.log_exc import exceptions as exc
from src.util import constants
from src.util.file_manager import FileManager
from src.util.util import DotDict


class Set:
    def __init__(
            self,
            values: Dict[str, Any] = None,
            **kwargs
    ) -> None:

        for key, value in kwargs.items():
            setattr(self, key, value)

        self.values = values

    def __repr__(self) -> str:
        return '\n'.join(f'{k}: {v}' for k, v in self.__dict__.items())


class Variable:
    def __init__(
            self,
            **kwargs
    ) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

        self.variable_fields = {}
        self.table_headers = {}
        self.coordinates = {}
        self.foreign_keys = {}

    def __repr__(self) -> str:
        return '\n'.join(f'{k}: {v}' for k, v in self.__dict__.items())


class Index:

    def __init__(
            self,
            files: FileManager,
            logger: Logger,
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info(f"'{self}' object initialization...")

        self.files = files

        self.sets = DotDict({
            key: Set(**value)
            for key, value in constants._SETS.items()
        })

        self.variables = DotDict({
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

        if all(set_instance.values is None for set_instance in self.sets.values()):
            self.logger.info(f"'{self}' object: loading new Sets to Index.")
        else:
            self.logger.warning(
                f"'{self}' object: Sets values already "
                "defined for at least one Set in Index.")
            user_input = input("Overwrite Sets? (y/[n]): ")
            if user_input.lower() != 'y':
                self.logger.info(
                    f"'{self}' object: Sets values not overwritten.")
                return
            else:
                self.logger.info(
                    f"'{self}' object: overwriting Sets to Index.")

        sets_values = self.files.excel_to_dataframes_dict(
            excel_file_name=excel_file_name,
            excel_file_dir_path=excel_file_dir_path,
            empty_data_fill=empty_data_fill
        )

        for set_instance in self.sets.values():
            table_name = set_instance.table_name
            if table_name in sets_values.keys():
                set_instance.values = sets_values[table_name]

    def load_vars_coordinates_to_index(self) -> None:

        self.logger.debug(f"Loading variables coordinates to Index.")

        for variable in self.variables.values():

            for set_key, set_filter in variable.coordinates_info.items():

                set_header = variable.variable_fields[set_key][0]

                if set_filter is None:
                    set_values = list(self.sets[set_key].values[set_header])

                elif isinstance(set_filter, dict):

                    if 'set_categories' in set_filter:
                        category_filter_id = set_filter['set_categories']
                        category_filter = self.sets[set_key].set_categories[category_filter_id]
                        category_header_name = self.sets[set_key].table_headers['category'][0]
                        set_filtered = self.sets[set_key].values.query(
                            f'{category_header_name} == "{category_filter}"'
                        )

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

                variable.coordinates[set_key] = set_values

    def load_foreign_keys_to_index(self) -> None:

        self.logger.debug(f"Loading foreign keys to Index.")

        for variable in self.variables.values():
            for set_key, set_header in variable.variable_fields.items():
                variable.foreign_keys[set_header[0]] = \
                    (set_header[0], self.sets[set_key].table_name)
