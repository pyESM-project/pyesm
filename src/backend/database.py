import sqlite3
import pandas as pd

from typing import List, Dict
from pathlib import Path
from src.util import constants
from src.log.logger import Logger
from src.util.file_manager import FileManager


class Database:

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            database_dir_path: Path,
            database_name: str,
            database_settings: Dict[str, str],
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info(f"Generation of '{self}' object.")

        self.files = files

        self.database_name = database_name
        self.database_dir_path = database_dir_path
        self.database_path = Path(database_dir_path, self.database_name)
        self.database_settings = database_settings

        self.connection = None
        self.cursor = None
        self.open_connection()

        self.sets_structure = constants._SETS
        self.sets = None

        if self.database_settings['generate_blank_sets']:
            for table in self.sets_structure:
                self.create_table(
                    table_name=self.sets_structure[table]['table_name'],
                    table_fields=self.sets_structure[table]['table_headers']
                )

            self.files.dict_to_excel(
                dict_name=self.sets_structure,
                excel_dir_path=database_dir_path,
                excel_file_name=self.database_settings['sets_file_name'],
                table_key='table_headers',
            )

        self.logger.info(f"'{self}' object initialized.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def open_connection(self) -> None:
        self.connection = sqlite3.connect(f'{self.database_path}')
        self.cursor = self.connection.cursor()
        self.logger.info(f"'{self}' connection opened.")

    def close_connection(self) -> None:
        self.connection.close()
        self.logger.info(f"'{self}' connection closed.")

    def drop_table(self, table_name: str) -> None:
        user_input = input(
            f"Are you sure you want to delete '{table_name}'? (y/[n]): ")
        if user_input.lower() != 'y':
            self.logger.debug(f"Table '{table_name}' not deleted.")
            return
        query = f"DROP TABLE {table_name}"
        self.cursor.execute(query)
        self.connection.commit()
        self.logger.debug(f"Table '{table_name}' deleted.")

    def create_table(
            self,
            table_name: str,
            table_fields: Dict[str, List[str]],
    ) -> None:

        if table_name in self.get_existing_tables():
            self.logger.debug(
                f"Table '{table_name}' already exists. Overwriting...")
            self.drop_table(table_name=table_name)

        fields_str = ", ".join(
            [f'{field_name} {field_type}'
             for field_name, field_type in table_fields.values()])

        query = f'CREATE TABLE {table_name}({fields_str})'

        try:
            self.cursor.execute(query)
            self.connection.commit()
            self.logger.debug(f"Table '{table_name}' created.")
        except sqlite3.OperationalError as error_msg:
            self.logger.error(error_msg)
            raise sqlite3.OperationalError(error_msg)

    def get_existing_tables(self) -> List[str]:
        query = "SELECT name FROM sqlite_master WHERE type='table'"
        self.cursor.execute(query)
        tables = self.cursor.fetchall()
        return [table[0] for table in tables]

    def get_table_fields(
            self,
            table_name: str
    ) -> Dict[str, str]:

        table_fields = {}
        query = f"PRAGMA table_info('{table_name}')"
        self.cursor.execute(query)
        result = self.cursor.fetchall()
        table_fields['labels'] = [row[1] for row in result]
        table_fields['types'] = [row[2] for row in result]
        return table_fields

    def count_table_data_entries(
            self,
            table_name: str
    ) -> int:
        self.cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
        return self.cursor.fetchone()[0]

    def delete_table_entries(self, table_name: str) -> None:
        num_entries = self.count_table_data_entries(table_name=table_name)
        self.cursor.execute(f"DELETE FROM {table_name}")
        self.logger.debug(
            f"{num_entries} rows deleted from table '{table_name}'")

    def dataframe_to_table(
            self,
            table_name: str,
            dataframe: pd.DataFrame,
    ) -> None:

        table_fields = self.get_table_fields(table_name=table_name)

        if not dataframe.columns.tolist() == table_fields['labels']:
            error = f"Dataframe and table {table_name} headers mismatch."
            self.logger.error(error)
            raise ValueError(error)

        num_entries = self.count_table_data_entries(table_name=table_name)
        if num_entries > 0:
            confirm = input(
                f"Table {table_name} already has {num_entries} rows. Do you \
                    want to delete existing data and insert new data? (y/[n])"
            )
            if confirm.lower() != 'y':
                return
            else:
                self.delete_table_entries(table_name=table_name)

        data = [tuple(row) for row in dataframe.values.tolist()]

        placeholders = ', '.join(['?'] * len(dataframe.columns))
        query = f"INSERT INTO {table_name} VALUES ({placeholders})"

        try:
            self.cursor.executemany(query, data)
            self.logger.debug(
                f"{len(data)} rows inserted into table '{table_name}'"
            )
        except sqlite3.IntegrityError as error:
            if str(error).startswith('UNIQUE'):
                error = f"Data already exists in database {table_name}."
            self.logger.error(error)

        self.connection.commit()

    def table_to_dataframe(
            self,
            table_name: str,
    ) -> pd.DataFrame:

        query = f"SELECT * FROM {table_name}"
        self.cursor.execute(query)
        data = self.cursor.fetchall()

        table_fields = self.get_table_fields(table_name=table_name)
        df = pd.DataFrame(data, columns=table_fields['labels'])

        return df

    def load_sets(self) -> Dict[str, pd.DataFrame]:
        if self.database_settings['sets_definition_excel']:
            self.sets = self.files.excel_to_dataframes_dict(
                excel_file_name=self.database_settings['sets_file_name'],
                excel_file_dir_path=self.database_dir_path,
                empty_data_fill='',
            )
            for table in self.sets:
                self.dataframe_to_table(
                    table_name=self.sets_structure[table]['table_name'],
                    dataframe=self.sets[table],
                )
            self.logger.info(
                "New sets loaded from "
                f"'{self.database_settings['sets_file_name']}'.")
        else:
            self.sets = {table: self.table_to_dataframe(table_name=table)
                         for table in self.sets_structure}

            self.files.dict_to_excel(
                dict_name=self.sets,
                excel_dir_path=self.database_dir_path,
                excel_file_name=self.database_settings['sets_file_name'],
            )
            self.logger.info(
                f"New sets loaded from sqlite '{self.database_name}'.")
