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
            database_settings: dict,
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

        if self.database_settings['sets_definition_excel'] == True:
            self.files.dict_to_excel(
                dict_name=self.sets_structure,
                excel_dir_path=database_dir_path,
                excel_file_name=self.database_settings['sets_file_name'],
                table_key='Headers',
            )

        self.logger.info(f"'{str(self)}' object initialized.")

    def __str__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def create_table(
            self,
            table_name: str,
            table_fields: dict,
    ) -> None:

        fields_str = ", ".join(
            [f'{field_name} {field_type}'
             for field_name, field_type in table_fields.items()]
        )

        query = f'CREATE TABLE IF NOT EXISTS {table_name}({fields_str})'

        try:
            self.cursor.execute(query)
            self.connection.commit()
            self.logger.debug(f'Table {table_name} created.')
        except sqlite3.OperationalError as error_msg:
            self.logger.error(error_msg)
            raise sqlite3.OperationalError(error_msg)

    def get_table_fields(
            self,
            table_name: str
    ) -> Dict:

        table_fields = {}
        query = f"PRAGMA table_info('{table_name}')"

        self.cursor.execute(query)
        result = self.cursor.fetchall()
        table_fields['labels'] = [row[1] for row in result]
        table_fields['types'] = [row[2] for row in result]

        return table_fields

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

        data = [tuple(row) for row in df.values.tolist()]

        placeholders = ', '.join(['?'] * len(df.columns))
        query = f"INSERT INTO {table_name} VALUES ({placeholders})"

        try:
            self.cursor.executemany(query, data)
            self.logger.debug(
                f'{len(data)} rows inserted into table {table_name}'
            )
        except sqlite3.IntegrityError as error:
            if str(error).startswith('UNIQUE'):
                error = f"Data already exists in database {table_name}."
            self.logger.error(error)

        self.connection.commit()

    def close_connection(self) -> None:
        self.connection.close()
        self.logger.debug(f"'{str(self)}' connection closed.")

    def load_sets(self) -> Dict:
        if self.database_settings['sets_definition_excel'] == True:
            # parse excel sets file, put its tabs into a dict of dataframes
            # generate self.sets property
            # put the dict of dataframes into the database
            # in case database already exists, do nothing (another method
            # will be used to update the database)

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
            return self.sets

        else:
            # define the database sql manually
            # then read the sql database and generate the sets.xlsx file
            # in case the sets.xlsx file already exists, do nothing
            pass

    def update_sets(
            self,
            excel_to_database: bool = True,
    ) -> None:
        # if true, takes the excel sets file and update the database sql
        # (delete entries not in the excel, add entries in the excel not in)
        # the other way around is also possible with False
        pass
