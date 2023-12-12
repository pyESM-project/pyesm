from operator import index
from pathlib import Path
from typing import Dict, List, Any

import pandas as pd

from src.backend.index import Index
from src.log_exc.logger import Logger
from src.util import constants
from src.util import util
from src.util.file_manager import FileManager
from src.util.sql_manager import SQLManager, connection


class Database:

    var_dict_hierarchy = constants._VAR_DICT_HIERARCHY.copy()
    data_file_extension = '.xlsx'

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            sqltools: SQLManager,
            settings: Dict,
            database_dir_path: Path,
            index: Index,
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info(f"'{self}' object initialization...")

        self.files = files
        self.sqltools = sqltools
        self.index = index
        self.settings = settings
        self.database_dir_path = database_dir_path
        self.database_settings = self.settings['database']

        if not Path(
            self.database_dir_path,
            self.settings['database']['sets_excel_file_name']
        ).exists():
            self.create_blank_sets()

        self.input_files_dir_path = Path(
            self.database_dir_path /
            self.settings['database']['input_data_dir_name'])

        self.logger.info(f"'{self}' object initialized.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    @connection
    def create_blank_sets(self) -> None:
        for set_instance in self.index.sets.values():
            self.sqltools.create_table(
                table_name=set_instance.table_name,
                table_fields=set_instance.table_headers
            )
            self.sqltools.table_to_excel(
                excel_filename=self.database_settings['sets_excel_file_name'],
                excel_dir_path=self.database_dir_path,
                table_name=set_instance.table_name,
            )

    @connection
    def load_sets_to_database(self) -> None:

        self.logger.info(f"'{self}' object: loading Sets.")

        for set_instance in self.index.sets.values():
            self.sqltools.dataframe_to_table(
                table_name=set_instance.table_name,
                dataframe=set_instance.values
            )

    @connection
    def generate_blank_sql_database(
        self,
        foreign_keys_on: bool = True,
    ) -> None:

        self.logger.info("Generation of empty SQLite database.")

        self.index.load_vars_coordinates_to_index()

        if foreign_keys_on:
            self.index.load_foreign_keys_to_index()

        for var_key, variable in self.index.variables.items():

            table_headers_list = [
                value[0] for value in variable.variable_fields.values()
            ]
            unpivoted_coords_df = util.unpivot_dict_to_dataframe(
                dict=variable.coordinates,
                headers=table_headers_list
            )

            variable.table_headers = variable.variable_fields.copy()
            variable.table_headers = util.add_item_to_dict(
                dictionary=variable.table_headers,
                item=constants._STD_ID_FIELD,
                position=0,
            )

            id_column_name = constants._STD_ID_FIELD['id'][0]
            id_column_values = pd.Series(
                range(0, len(unpivoted_coords_df)+1))
            unpivoted_coords_df.insert(0, id_column_name, id_column_values)

            self.sqltools.create_table(
                table_name=var_key,
                table_fields=variable.table_headers,
                foreign_keys=variable.foreign_keys,
            )

            self.sqltools.dataframe_to_table(
                table_name=var_key,
                dataframe=unpivoted_coords_df,
            )

            self.sqltools.add_table_column(
                table_name=var_key,
                column_name=constants._STD_VALUES_FIELD['values'][0],
                column_type=constants._STD_VALUES_FIELD['values'][1],
            )

    @connection
    def clear_database_variables(self) -> None:
        existing_tables = self.sqltools.get_existing_tables_names

        for table_name in existing_tables:
            if table_name in self.variables_info.keys():
                self.sqltools.drop_table(table_name=table_name)

        self.logger.info(
            "All variables tables dropped from SQLite database "
            f"{self.database_settings['database_name']}"
        )

    @connection
    def generate_blank_data_input_files(
        self,
        file_extension: str = data_file_extension,
    ) -> None:

        self.logger.info(f"Generation of data input file/s.")

        if not self.input_files_dir_path.exists():
            self.files.create_dir(self.input_files_dir_path)

        tables_names_list = self.sqltools.get_existing_tables_names

        for variable in self.index.variables.values():

            if variable.type == 'exogenous' and \
                    variable.symbol in tables_names_list:

                if self.settings['database']['multiple_input_files']:
                    output_file_name = variable.symbol + file_extension
                else:
                    output_file_name = self.settings['database']['input_file_name']

                self.sqltools.table_to_excel(
                    excel_filename=output_file_name,
                    excel_dir_path=self.input_files_dir_path,
                    table_name=variable.symbol,
                )

    @connection
    def load_data_input_files(
        self,
        file_extension: str = data_file_extension,
    ) -> None:

        self.logger.info(
            "Loading data input file/s filled by the user to SQLite database.")

        if self.settings['database']['multiple_input_files']:
            data = {}
            for variable in self.index.variables.values():
                if variable.type == 'exogenous':

                    var_name = variable.symbol
                    file_name = var_name + file_extension

                    data.update(
                        self.files.excel_to_dataframes_dict(
                            excel_file_dir_path=self.input_files_dir_path,
                            excel_file_name=file_name,
                        )
                    )
                    self.sqltools.dataframe_to_table(
                        table_name=var_name,
                        dataframe=data[var_name],
                    )

        else:
            data = self.files.excel_to_dataframes_dict(
                excel_file_dir_path=self.input_files_dir_path,
                excel_file_name=self.database_settings['input_file_name']
            )
            for data_key, data_values in data.items():
                self.sqltools.dataframe_to_table(
                    table_name=data_key,
                    dataframe=data_values,
                )

    # da qui, ragionare su come è meglio creare le variabili e il problema.
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
