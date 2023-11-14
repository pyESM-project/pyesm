from functools import wraps
from pathlib import Path
from typing import List, Dict, Any
import sqlite3

import pandas as pd

from src.log_exc.logger import Logger


class SQLManager:

    def __init__(
        self,
        logger: Logger,
        database_dir_path: Path,
        database_name: str,
        xls_engine: str = 'openpyxl',
    ) -> None:

        self.logger = logger.getChild(__name__)

        self.database_sql_path = Path(database_dir_path, database_name)

        self.database_name = database_name
        self.connection = None
        self.cursor = None
        self.xls_engine = xls_engine
        self.foreign_keys_enabled = False

        self.logger.info(f"'{self}' object generated.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def open_connection(self) -> None:
        if self.connection is None:
            self.connection = sqlite3.connect(f'{self.database_sql_path}')
            self.cursor = self.connection.cursor()
            self.logger.debug(f"Connection to '{self.database_name}' opened.")
        else:
            self.logger.debug(
                f"Connection to '{self.database_name}' already opened.")

    def close_connection(self) -> None:
        if self.connection:
            self.connection.close()
            self.connection = None
            self.logger.debug(f"Connection to '{self.database_name}' closed.")
        else:
            self.logger.debug(
                f"Connection to '{self.database_name}' "
                "already closed or does not exist.")

    @property
    def get_existing_tables_names(self) -> List[str]:
        query = "SELECT name FROM sqlite_master WHERE type='table'"
        self.cursor.execute(query)
        tables = self.cursor.fetchall()
        return [table[0] for table in tables]

    def execute_query(
            self,
            query: str,
    ) -> None:
        try:
            self.cursor.execute(query)
            self.connection.commit()
        except sqlite3.OperationalError as error_msg:
            self.logger.error(error_msg)
            raise sqlite3.OperationalError(error_msg)

    def drop_table(self, table_name: str) -> None:
        query = f"DROP TABLE {table_name}"
        self.cursor.execute(query)
        self.connection.commit()
        self.logger.debug(f"Table '{table_name}' deleted.")

    def get_table_fields(
            self,
            table_name: str
    ) -> Dict[str, str]:

        table_fields = {}
        self.execute_query(f"PRAGMA table_info('{table_name}')")
        result = self.cursor.fetchall()
        table_fields['labels'] = [row[1] for row in result]
        table_fields['types'] = [row[2] for row in result]
        return table_fields

    def create_table(
            self,
            table_name: str,
            table_fields: Dict[str, List[str]],
            table_content: pd.DataFrame = None,
    ) -> None:

        if table_name in self.get_existing_tables_names:
            self.logger.debug(
                f"Table '{table_name}' already exists.")

            user_input = input(
                f"Delete and overwrite '{table_name}'? (y/[n]): ")
            if user_input.lower() != 'y':
                self.logger.debug(f"Table '{table_name}' not owerwritten.")
                return
            self.drop_table(table_name=table_name)

        fields_str = ", ".join(
            [f'{field_name} {field_type}'
                for field_name, field_type in table_fields.values()])

        self.execute_query(f'CREATE TABLE {table_name}({fields_str})')

        if table_content is not None:
            table_headers = set(self.get_table_fields(table_name)['labels'])
            if set(table_content.columns) != table_headers:
                self.logger.error(
                    "Passed DataFrame headers do not match fields for table "
                    f"{table_name}. Data not inserted.")
                return

            try:
                table_content.to_sql(
                    table_name,
                    self.connection,
                    if_exists='replace',
                    index=False
                )
                self.logger.debug(f"Data inserted into table '{table_name}'.")

            except sqlite3.OperationalError as error_msg:
                self.logger.error(error_msg)
                raise sqlite3.OperationalError(error_msg)

    def add_column(
            self,
            table_name: str,
            column_name: str,
            column_type: str,
            default_value: Any = None,
    ) -> None:

        if table_name not in self.get_existing_tables_names:
            self.logger.warning(
                f"Table '{table_name}' does NOT exist.")
            return

        try:
            query = (
                f'ALTER TABLE {table_name} ADD COLUMN "{column_name}" {column_type}')
            if default_value is not None:
                query += f" DEFAULT {default_value}"
            self.execute_query(query)
            self.connection.commit()
            self.logger.debug(
                f"Column '{column_name}' added to table '{table_name}'.")
        except Exception as error_msg:
            self.logger.error(f"Error adding column to table: {error_msg}")

    def enable_foreing_keys(self) -> None:
        if not self.foreign_keys_enabled:
            self.execute_query('PRAGMA foreign_keys = ON;')
            self.foreign_keys_enabled = True

    def disable_foreing_keys(self) -> None:
        if self.foreign_keys_enabled:
            self.execute_query('PRAGMA foreign_keys = OFF;')
            self.foreign_keys_enabled = False

    # this is not working cause ALTER TABLE does not work with FOREIGN KEY
    # i should create the table and at the same time the foreing key constraints
    def add_foreign_key(
            self,
            child_table: str,
            child_key: str,
            parent_table: str,
            parent_key: str,
    ) -> None:

        self.enable_foreing_keys()

        self.execute_query(f'''
            ALTER TABLE {child_table} 
            ADD FOREIGN KEY ({child_key}) REFERENCES {parent_table}({parent_key});
        ''')

        self.disable_foreing_keys()

        self.logger.debug(
            "Foreing key assigned: "
            f"'{parent_table}({parent_key})' -> '{child_table}({child_key})'")

    def count_table_data_entries(
            self,
            table_name: str
    ) -> int:
        self.execute_query(f'SELECT COUNT(*) FROM {table_name}')
        return self.cursor.fetchone()[0]

    def delete_table_entries(self, table_name: str) -> None:
        num_entries = self.count_table_data_entries(table_name=table_name)
        self.execute_query(f"DELETE FROM {table_name}")
        self.logger.debug(
            f"{num_entries} rows deleted from table '{table_name}'")

    def dataframe_to_table(
            self,
            table_name: str,
            table_df: pd.DataFrame,
    ) -> None:

        table_fields = self.get_table_fields(table_name=table_name)

        if not table_df.columns.tolist() == table_fields['labels']:
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

        data = [tuple(row) for row in table_df.values.tolist()]

        placeholders = ', '.join(['?'] * len(table_df.columns))
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

        self.execute_query(f"SELECT * FROM {table_name}")
        data = self.cursor.fetchall()

        table_fields = self.get_table_fields(table_name=table_name)
        df = pd.DataFrame(data, columns=table_fields['labels'])

        return df

    def table_to_excel(
            self,
            excel_filename: str,
            excel_dir_path: Path,
            table_name: str,
    ) -> None:
        excel_file_path = Path(excel_dir_path, excel_filename)

        mode = 'a' if excel_file_path.exists() else 'w'
        if_sheet_exists = 'replace' if mode == 'a' else None

        with pd.ExcelWriter(
            excel_file_path,
            engine=self.xls_engine,
            mode=mode,
            if_sheet_exists=if_sheet_exists,
        ) as writer:
            query = f'SELECT * FROM {table_name}'
            df = pd.read_sql_query(query, self.connection)
            df.to_excel(writer, sheet_name=table_name, index=False)


def connection(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        self.sqltools.open_connection()
        try:
            result = method(self, *args, **kwargs)
        finally:
            self.sqltools.close_connection()
        return result
    return wrapper
