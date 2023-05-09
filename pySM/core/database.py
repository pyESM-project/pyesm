import sqlite3
import pandas as pd

from typing import List, Dict
from pySM.util import constants
from pathlib import Path
from pySM.log_exc.logger import Logger
from pySM.util.file_manager import FileManager


class Database:

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            database_dir_path: str,
            database_name: str,
            database_settings: Dict[str, str],
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info(f"Generation of '{str(self)}' object.")

        self.files = files

        self.database_dir_path = database_dir_path
        self.database_path = Path(database_dir_path, database_name)

        self.database_settings = database_settings
        self.connection = sqlite3.connect(f'{self.database_path}')
        self.cursor = self.connection.cursor()

        self.sets_structure = constants._SETS

        for table in self.sets_structure:
            self.create_table(
                table_name=table,
                table_fields=self.sets_structure[table]['Headers']
            )

        self.files.dict_to_excel(
            dict_name=self.sets_structure,
            excel_dir_path=database_dir_path,
            excel_file_name=self.database_settings['sets_file_name'],
            table_key='Headers',
        )

        self.logger.info(f"'{str(self)}' object initialized.")

    def __str__(self) -> None:
        class_name = type(self).__name__
        return f'{class_name}'

    def create_table(
            self,
            table_name: str,
            table_fields: Dict[str, str],
    ) -> None:

        fields_str = ", ".join(
            [f'{field_name} {field_type}'
             for field_name, field_type in table_fields.items()]
        )

        query = f'CREATE TABLE IF NOT EXISTS {table_name}({fields_str})'

        try:
            self.cursor.execute(query)
            self.connection.commit()
            self.logger.debug(f"Table '{table_name}' created.")
        except sqlite3.OperationalError as error_msg:
            self.logger.error(error_msg)
            raise sqlite3.OperationalError(error_msg)

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

    def count_table_data_entries(self, table_name: str) -> int:
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
            df: pd.DataFrame,
    ) -> None:

        table_fields = self.get_table_fields(table_name=table_name)

        if not df.columns.tolist() == table_fields['labels']:
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

        data = [tuple(row) for row in df.values.tolist()]

        placeholders = ', '.join(['?'] * len(df.columns))
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

    def close_connection(self) -> None:
        self.connection.close()
        self.logger.debug(f"'{str(self)}' connection closed.")

    def load_new_sets(self) -> Dict[str, pd.DataFrame]:
        if self.database_settings['sets_definition_excel'] == True:
            self.sets = self.files.excel_to_dataframes_dict(
                excel_file_name=self.database_settings['sets_file_name'],
                excel_file_dir_path=self.database_dir_path,
                empty_data_fill='',
            )
            for table in self.sets:
                self.dataframe_to_table(
                    table_name=table,
                    df=self.sets[table],
                )
        else:
            self.sets = {table: self.table_to_dataframe(table_name=table)
                         for table in self.sets_structure}

            self.files.dict_to_excel(
                dict_name=self.sets,
                excel_dir_path=self.database_dir_path,
                excel_file_name=self.database_settings['sets_file_name'],
            )

    def update_sets(
            self,
            excel_to_database: bool = True,
    ) -> None:
        # if true, takes the excel sets file and update the database sql
        # (delete entries not in the excel, add entries in the excel not in)
        # the other way around is also possible with False
        pass
