from operator import index
from pathlib import Path
from typing import Dict, List, Any

import pandas as pd

from src.backend.index import Index
from src.log_exc.logger import Logger
from src.constants import constants
from src.support import util
from src.support.file_manager import FileManager
from src.support.sql_manager import SQLManager, connection


class Database:

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
                dataframe=set_instance.table
            )

    @connection
    def generate_blank_vars_sql_tables(self) -> None:
        self.logger.info("Generation of empty SQLite database.")

        for var_key, variable in self.index.variables.items():

            table_headers_list = [
                value[0] for value in variable.variable_fields.values()
            ]

            unpivoted_coords_df = util.unpivot_dict_to_dataframe(
                data_dict=variable.coordinates,
                key_order=table_headers_list
            )

            unpivoted_coords_df.insert(
                loc=0,
                column=variable.table_headers['id'][0],
                value=None
            )

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
    def generate_blank_vars_input_files(
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
    def load_data_input_files_to_database(
        self,
        operation: str,
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
                        operation=operation,
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
                    operation=operation,
                )
