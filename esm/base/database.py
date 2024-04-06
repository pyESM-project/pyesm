from pathlib import Path
from typing import Dict, List

from esm.base.data_table import DataTable
from esm.base.index import Index
from esm.base.set_table import SetTable
from esm.log_exc.logger import Logger
from esm import constants
from esm.support import util
from esm.support.file_manager import FileManager
from esm.support.sql_manager import SQLManager, db_handler


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

        with db_handler(self.sqltools):
            for set_instance in self.index.sets.values():
                set_instance: SetTable

                table_name = set_instance.table_name
                table_fields = set_instance.table_headers

                if constants._STD_ID_FIELD['id'] not in table_fields.values():
                    table_fields = {**constants._STD_ID_FIELD, **table_fields}

                self.sqltools.create_table(table_name, table_fields)

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

        dict_headers = {
            set_value.table_name: set_value.excel_file_set_headers
            for set_value in self.index.sets.values()
        }

        self.files.dict_to_excel_headers(
            dict_name=dict_headers,
            excel_dir_path=self.paths['model_dir'],
            excel_file_name=self.settings['sets_xlsx_file'],
        )

    def load_sets_to_database(self) -> None:
        self.logger.info(
            f"Loading Sets to '{self.settings['sqlite_database_file']}'.")

        with db_handler(self.sqltools):
            for set_instance in self.index.sets.values():
                set_instance: SetTable

                table_name = set_instance.table_name
                dataframe = set_instance.data.copy()

                if constants._STD_ID_FIELD['id'] not in \
                        getattr(set_instance, 'table_headers').values():

                    util.add_column_to_dataframe(
                        dataframe=dataframe,
                        column_header=constants._STD_ID_FIELD['id'][0],
                        column_position=0,
                        column_values=None,
                    )

                self.sqltools.dataframe_to_table(table_name, dataframe)

    # MODIFY HERE TO PUT ALSO CONSTANTS IN DB
    def generate_blank_data_sql_tables(self) -> None:
        self.logger.info(
            "Generation of empty SQLite database data tables.")

        with db_handler(self.sqltools):
            for table_key, table in self.index.data.items():
                table: DataTable

                if table.type == 'constant':
                    continue

                self.sqltools.create_table(
                    table_name=table_key,
                    table_fields=table.table_headers,
                    foreign_keys=table.foreign_keys,
                )

    def sets_data_to_vars_sql_tables(self) -> None:
        self.logger.info(
            "Filling empty SQLite database variables tables with sets data.")

        with db_handler(self.sqltools):
            for table_key, table in self.index.data.items():
                table: DataTable

                # MODIFY HERE TO PUT ALSO CONSTANTS IN DB
                if table.type == 'constant':
                    continue

                table_headers_list = [
                    value for value in table.coordinates_headers.values()
                ]

                unpivoted_coords_df = util.unpivot_dict_to_dataframe(
                    data_dict=table.coordinates_values,
                    key_order=table_headers_list
                )

                util.add_column_to_dataframe(
                    dataframe=unpivoted_coords_df,
                    column_header=table.table_headers['id'][0],
                    column_position=0,
                    column_values=None
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

    def clear_database_tables(
        self,
        table_names: List[str] | str = None,
    ) -> None:
        """
        Clears the specified tables or all tables from the SQLite database.

        Args:
            table_names (List[str] | str, optional): A list of table names or 
                a single table name to clear. If not provided, all tables in 
                the database will be cleared. Defaults to None.
        """
        with db_handler(self.sqltools):
            existing_tables = self.sqltools.get_existing_tables_names

            if not table_names:
                tables_to_clear = existing_tables
                self.logger.info(
                    "Clearing all tables from SQLite database "
                    f"{self.settings['sqlite_database_file']}"
                )

            else:
                tables_to_clear = list(table_names)
                self.logger.info(
                    f"Clearing tables '{tables_to_clear}' from SQLite database "
                    f"{self.settings['sqlite_database_file']}"
                )

            for table_name in tables_to_clear:
                if table_name in self.index.data.keys():
                    self.sqltools.drop_table(table_name)

    def generate_blank_data_input_files(
        self,
        file_extension: str = data_file_extension,
    ) -> None:

        self.logger.info(f"Generation of data input file/s.")

        if not Path(self.paths['input_data_dir']).exists():
            self.files.create_dir(self.paths['input_data_dir'])

        with db_handler(self.sqltools):
            tables_names_list = self.sqltools.get_existing_tables_names

            for table_key, table in self.index.data.items():
                table: DataTable

                if table.type != 'exogenous' and \
                        table_key not in tables_names_list:
                    continue

                if self.settings['multiple_input_files']:
                    output_file_name = table_key + file_extension
                else:
                    output_file_name = self.settings['input_data_file']

                self.sqltools.table_to_excel(
                    excel_filename=output_file_name,
                    excel_dir_path=self.paths['input_data_dir'],
                    table_name=table_key,
                )

    def load_data_input_files_to_database(
        self,
        operation: str,
        file_extension: str = data_file_extension,
        force_overwrite: bool = False,
    ) -> None:
        self.logger.info(
            "Loading data from input file/s filled by the user "
            "to SQLite database.")

        if self.settings['multiple_input_files']:
            data = {}

            with db_handler(self.sqltools):
                for table_key, table in self.index.data.values():
                    table: DataTable

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

            with db_handler(self.sqltools):
                for table_key, table in data.items():
                    self.sqltools.dataframe_to_table(
                        table_name=table_key,
                        dataframe=table,
                        operation=operation,
                        force_operation=force_overwrite,
                    )

    def empty_data_completion(
        self,
        operation: str,
    ):
        self.logger.info(
            "Auto-completion of blank data in SQLite database.")

        with db_handler(self.sqltools):
            pass
