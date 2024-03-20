from pathlib import Path
from typing import Dict

import pandas as pd

from esm.base.index import Index
from esm.log_exc.logger import Logger
from esm import constants
from esm.support import util
from esm.support.file_manager import FileManager
from esm.support.sql_manager import SQLManager, connection


class Database:

    data_file_extension = '.xlsx'

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            paths: Dict,
            sqltools: SQLManager,
            settings: Dict,
            index: Index,
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info(f"'{self}' object initialization...")

        self.files = files
        self.sqltools = sqltools
        self.index = index
        self.settings = settings
        self.paths = paths

        if not self.settings['use_existing_data']:
            self.initialize_blank_database()
            self.create_blank_sets_xlsx_file()

        self.logger.info(f"'{self}' object initialized.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    @connection
    def initialize_blank_database(self) -> None:
        sqlite_database_name = self.settings['sqlite_database_file']

        if Path(self.paths['sqlite_database']).exists():
            if not self.settings['use_existing_data']:
                self.logger.info(
                    f"Overwriting database '{sqlite_database_name}'")
            else:
                self.logger.info(
                    f"Relying on existing database '{sqlite_database_name}'")
                return
        else:
            self.logger.info(
                f"Generating new database '{sqlite_database_name}'")

        for set_instance in self.index.sets.values():
            self.sqltools.create_table(
                table_name=set_instance.table_name,
                table_fields=set_instance.table_headers
            )

    @connection
    def create_blank_sets_xlsx_file(self) -> None:
        sets_file_name = self.settings['sets_xlsx_file']

        if Path(self.paths['sets_excel_file']).exists():
            if not self.settings['use_existing_data']:
                self.logger.info(
                    f"Overwriting sets excel file '{sets_file_name}'")
            else:
                self.logger.info(
                    f"Relying on existing sets excel file '{sets_file_name}'")
                return
        else:
            self.logger.info(
                f"Generating new sets excel file '{sets_file_name}'")

        for set_instance in self.index.sets.values():
            self.sqltools.table_to_excel(
                excel_filename=self.settings['sets_xlsx_file'],
                excel_dir_path=self.paths['model_dir'],
                table_name=set_instance.table_name,
            )

    @connection
    def load_sets_to_database(self) -> None:
        self.logger.info(
            f"Loading Sets to '{self.settings['sqlite_database_file']}'.")

        for set_instance in self.index.sets.values():
            self.sqltools.dataframe_to_table(
                table_name=set_instance.table_name,
                dataframe=set_instance.data
            )

    @connection
    def generate_blank_data_sql_tables(self) -> None:
        self.logger.info(
            "Generation of empty SQLite database data tables.")

        for table_key, table in self.index.data.items():

            if table.type == 'constant':
                continue

            self.sqltools.create_table(
                table_name=table_key,
                table_fields=table.table_headers,
                foreign_keys=table.foreign_keys,
            )

    @connection
    def sets_data_to_vars_sql_tables(self) -> None:
        self.logger.info(
            "Filling empty SQLite database variables tables with sets data.")

        for table_key, table in self.index.data.items():

            if table.type == 'constant':
                continue

            table_headers_list = [
                value for value in table.coordinates_headers.values()
            ]

            unpivoted_coords_df = util.unpivot_dict_to_dataframe(
                data_dict=table.coordinates_values,
                key_order=table_headers_list
            )

            unpivoted_coords_df.insert(
                loc=0,
                column=table.table_headers['id'][0],
                value=None
            )

            self.sqltools.dataframe_to_table(
                table_name=table_key,
                dataframe=unpivoted_coords_df,
            )

            self.sqltools.add_table_column(
                table_name=table_key,
                column_name=constants._STD_VALUES_FIELD['values'][0],
                column_type=constants._STD_VALUES_FIELD['values'][1],
            )

    @connection
    def clear_database_table(self) -> None:
        existing_tables = self.sqltools.get_existing_tables_names

        for table_name in existing_tables:
            if table_name in self.variables_info.keys():
                self.sqltools.drop_table(table_name)

        self.logger.info(
            "All variables tables dropped from SQLite database "
            f"{self.settings['sqlite_database_file']}"
        )

    @connection
    def generate_blank_data_input_files(
        self,
        file_extension: str = data_file_extension,
    ) -> None:

        self.logger.info(f"Generation of data input file/s.")

        if not Path(self.paths['input_data_dir']).exists():
            self.files.create_dir(self.paths['input_data_dir'])

        tables_names_list = self.sqltools.get_existing_tables_names

        for table_key, table in self.index.data.items():

            if table.type == 'exogenous' and \
                    table_key in tables_names_list:

                if self.settings['multiple_input_files']:
                    output_file_name = table_key + file_extension
                else:
                    output_file_name = self.settings['input_data_file']

                self.sqltools.table_to_excel(
                    excel_filename=output_file_name,
                    excel_dir_path=self.paths['input_data_dir'],
                    table_name=table_key,
                )

    @connection
    def load_data_input_files_to_database(
        self,
        operation: str,
        file_extension: str = data_file_extension,
    ) -> None:
        self.logger.info(
            "Loading data input file/s filled by the user to SQLite database.")

        if self.settings['multiple_input_files']:
            data = {}
            for table_key, table in self.index.data.values():
                if table.type == 'exogenous':

                    file_name = table_key + file_extension

                    data.update(
                        self.files.excel_to_dataframes_dict(
                            excel_file_dir_path=self.paths['input_data_dir'],
                            excel_file_name=file_name,
                        )
                    )
                    self.sqltools.dataframe_to_table(
                        table_name=table_key,
                        dataframe=data[table_key],
                        operation=operation,
                    )

        else:
            data = self.files.excel_to_dataframes_dict(
                excel_file_dir_path=self.paths['input_data_dir'],
                excel_file_name=self.settings['input_data_file'],
            )
            for table_key, table in data.items():
                self.sqltools.dataframe_to_table(
                    table_name=table_key,
                    dataframe=table,
                    operation=operation,
                )

    @connection
    def empty_data_completion(
        self,
        operation: str,
    ):
        self.logger.info(
            "Auto-completion of blank data in SQLite database.")
        pass
