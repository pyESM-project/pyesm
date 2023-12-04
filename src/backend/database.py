from itertools import product
from pathlib import Path
from typing import Dict, List, Any

import pandas as pd

from src.log_exc.logger import Logger
from src.log_exc import exceptions as exc
from src.util import constants
from src.util import util
from src.util.file_manager import FileManager
from src.util.sql_manager import SQLManager, connection


class Database:

    std_id_field = constants._STD_ID_FIELD.copy()
    std_values_nametype = constants._STD_VALUES_FIELD.copy()
    var_dict_hierarchy = constants._VAR_DICT_HIERARCHY.copy()

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            sqltools: SQLManager,
            database_dir_path: Path,
            settings: Dict,
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info(f"'{self}' object initialization...")

        self.files = files
        self.sqltools = sqltools
        self.settings = settings
        self.database_dir_path = database_dir_path
        self.database_settings = self.settings['database']

        self.sets_structure = constants._SETS.copy()
        self.variables_info = constants._VARIABLES.copy()
        self.variables_data = None
        self.sets = None
        self.coordinates = None

        if not Path(
            self.database_dir_path,
            self.database_settings['sets_excel_file_name']
        ).exists():
            self.create_blank_sets()

        self.logger.info(f"'{self}' object initialized.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    @connection
    def create_blank_sets(self) -> None:
        for value in self.sets_structure.values():
            self.sqltools.create_table(
                table_name=value['table_name'],
                table_fields=value['table_headers']
            )
            self.sqltools.table_to_excel(
                excel_filename=self.database_settings['sets_excel_file_name'],
                excel_dir_path=self.database_dir_path,
                table_name=value['table_name'],
            )

    @connection
    def load_sets(self) -> None:
        if self.sets is not None:
            self.logger.info(
                f"Sets are already defined in the '{self}' object.")
            user_input = input(
                "Overwrite Sets? (y/[n]): ")
            if user_input.lower() != 'y':
                self.logger.info("Original Sets not owerwritten.")
                return

        self.sets = self.files.excel_to_dataframes_dict(
            excel_file_name=self.database_settings['sets_excel_file_name'],
            excel_file_dir_path=self.database_dir_path,
            empty_data_fill='',
        )

        for table_key, table in self.sets.items():
            self.sqltools.dataframe_to_table(
                table_name=table_key,
                dataframe=table
            )

        self.logger.info(
            f"New Sets loaded in {self} class and "
            f"'{self.database_settings['database_name']}' from "
            f"'{self.database_settings['sets_excel_file_name']}'."
        )

    def load_variables_coordinates(self) -> None:

        self.logger.info(f"Loading variables coordinates...")

        if self.coordinates is not None:
            self.logger.warning(
                f"Variable coordinates already initialized in '{self}' object.")
            user_input = input(
                f"Overwrite variable coordinates? (y/[n]): ")
            if user_input.lower() != 'y':
                self.logger.info(
                    f"Original variables coordinates not overwritten.")
                return

        self.coordinates = {}

        for var_key, var_info in self.variables_info.items():
            self.logger.debug(
                "Loading coordinates for variable "
                f"'{var_info['symbol']}'.")

            self.coordinates[var_key] = {}

            for coord_key, coord_info in var_info['coordinates'].items():
                set_label = self.sets_structure[coord_key]['table_name']
                header_label_type = var_info['set_headers']
                header_label = self.sets_structure[coord_key]['table_headers'][header_label_type][0]

                if coord_info == 'all':
                    set_values = list(self.sets[set_label][header_label])

                elif isinstance(coord_info, dict) and 'set_categories' in coord_info:
                    category_filter_id = coord_info['set_categories']
                    category_filter = self.sets_structure[coord_key]['set_categories'][category_filter_id]
                    category_header_name = self.sets_structure[coord_key]['table_headers']['category'][0]
                    set_filtered = self.sets[set_label].query(
                        f'{category_header_name} == "{category_filter}"'
                    )

                    if 'aggregation_key' in coord_info:
                        aggregation_key = coord_info['aggregation_key']
                        aggregation_key_name = \
                            self.sets_structure[coord_key]['table_headers'][aggregation_key][0]

                        set_filtered.loc[
                            set_filtered[aggregation_key_name] != '', header_label
                        ] = set_filtered[aggregation_key_name]

                    set_values = list(set(set_filtered[header_label]))

                else:
                    error_msg = f"Missing or wrong data in 'sets_structure' parameter."
                    self.logger.error(error_msg)
                    raise exc.MissingDataError(error_msg)

                self.coordinates[var_key][header_label] = set_values

        self.logger.info(f"Variables coordinates loaded.")

    @connection
    def generate_blank_database(
        self,
        std_values_nametype: List[str] = std_values_nametype,
    ) -> None:

        self.logger.info("Generation of empty SQLite database...")

        if not self.coordinates:
            self.load_variables_coordinates()

        for var_key, var_info in self.variables_info.items():
            set_field = var_info['set_headers']
            table_fields = util.generate_dict_with_none_values(
                var_info['coordinates'])

            foreign_keys = {}
            for field_key in table_fields.keys():
                table_fields[field_key] = \
                    self.sets_structure[field_key]['table_headers'][set_field]
                foreign_keys[table_fields[field_key][0]] = \
                    (table_fields[field_key][0],
                     self.sets_structure[field_key]['table_name'])

            unpivoted_coordinates = None
            if self.coordinates[var_key]:
                unpivoted_coordinates = self.unpivot_coordinates(
                    self.coordinates[var_key])

            table_fields = {'id': self.std_id_field} | table_fields
            id_column_name = table_fields['id'][0]
            id_column_values = pd.Series(
                range(0, len(unpivoted_coordinates)+1))
            unpivoted_coordinates.insert(0, id_column_name, id_column_values)

            self.sqltools.create_table(
                table_name=var_key,
                table_fields=table_fields,
                foreign_keys=foreign_keys,
            )

            self.sqltools.dataframe_to_table(
                table_name=var_key,
                dataframe=unpivoted_coordinates,
            )

            self.sqltools.add_table_column(
                table_name=var_key,
                column_name=std_values_nametype[0],
                column_type=std_values_nametype[1],
            )

        self.logger.info(f"Empty SQLite database generated.")

    def unpivot_coordinates(
            self,
            coordinates_dict: Dict[str, List[str]],
    ) -> pd.DataFrame:

        df = pd.DataFrame()
        cartesian_product = list(product(*coordinates_dict.values()))
        df = pd.DataFrame(
            cartesian_product,
            columns=coordinates_dict.keys()
        )
        return df

    def clear_database_variables(self) -> None:
        existing_tables = self.sqltools.get_existing_tables_names

        for table_name in existing_tables:
            if table_name in self.variables_info.keys():
                self.sqltools.drop_table(table_name=table_name)

        self.logger.info(
            "Variables tables dropped from SQLite database "
            f"{self.database_settings['database_name']}"
        )

    @connection
    def generate_input_files(self) -> None:

        self.logger.info(
            f"Generation of input file/s for '{self}' object.")

        input_files_dir_path = Path(
            self.database_dir_path /
            self.database_settings['input_data_dir_name'])

        if not input_files_dir_path.exists():
            self.files.create_dir(input_files_dir_path)

        tables_names_list = self.sqltools.get_existing_tables_names

        for _, var_info in self.variables_info.items():

            if var_info['type'] == 'exogenous' and \
                    var_info['symbol'] in tables_names_list:

                if self.database_settings['multiple_input_files']:
                    output_file_name = var_info['symbol']+".xlsx"
                else:
                    output_file_name = self.database_settings['input_file_name']

                self.sqltools.table_to_excel(
                    excel_filename=output_file_name,
                    excel_dir_path=input_files_dir_path,
                    table_name=var_info['symbol'],
                )

        self.logger.info(
            f"Input file/s for '{self}' object generated.")

    @connection
    def load_input_files(self) -> None:

        self.logger.info(f"Loading input file/s for '{self}' object.")

        input_files_dir_path = Path(
            self.database_dir_path /
            self.database_settings['input_data_dir_name'])

        if self.database_settings['multiple_input_files']:
            data = {}
            for _, var_info in self.variables_info.items():
                if var_info['type'] == 'exogenous':
                    var_name = var_info['symbol']
                    file_name = var_name + '.xlsx'
                    data.update(
                        self.files.excel_to_dataframes_dict(
                            excel_file_dir_path=input_files_dir_path,
                            excel_file_name=file_name
                        )
                    )
                    self.sqltools.dataframe_to_table(
                        table_name=var_name,
                        dataframe=data[var_name],
                    )
        else:
            data = self.files.excel_to_dataframes_dict(
                excel_file_dir_path=input_files_dir_path,
                excel_file_name=self.database_settings['input_file_name']
            )
            for data_key, data_values in data.items():
                self.sqltools.dataframe_to_table(
                    table_name=data_key,
                    dataframe=data_values
                )

        self.logger.info(f"Input file/s loaded into '{self}' object.")

    def generate_variables_data_dict(self) -> Dict[str, Any]:

        self.logger.info("Generating empty dictionary of variables data...")

        variables_data = {}

        for var_key, var_info in self.variables_info.items():
            variables_data[var_key] = {}
            keys_parsing_order = []

            if self.variables_info[var_key]['var_dict_hierarchy'] is None:
                dict_hierarchy = self.var_dict_hierarchy
            else:
                dict_hierarchy = self.variables_info[var_key]['var_dict_hierarchy']

            for level in dict_hierarchy:
                level_header_key = var_info['set_headers']
                level_header = self.sets_structure[level]['table_headers'][level_header_key][0]
                keys_parsing_order.append(level_header)

                variables_data[var_key][level_header] = \
                    self.coordinates[var_key][level_header]

            variables_data[var_key] = \
                util.pivot_dict(variables_data[var_key])

        self.logger.info("Empty dictionary of variables data generated.")

        return variables_data
