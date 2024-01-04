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
        self.foreign_keys_enabled = None

        self.logger.info(f"'{self}' object Generated.")

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

    def get_primary_column_name(
            self,
            table_name: str,
    ) -> str:

        query = f"PRAGMA table_info({table_name})"
        self.execute_query(query)
        table_info = self.cursor.fetchall()
        primary_key_column_name = [
            column[1] for column in table_info if column[5] == 1
        ]

        if len(primary_key_column_name) == 1:
            return primary_key_column_name[0]
        else:
            raise ValueError(
                f"SQLite table '{table_name}' does not have "
                "a unique primary key column."
            )

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
        self.execute_query(query)
        self.connection.commit()
        self.logger.debug(f"SQLite '{table_name}' - deleted.")

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
            foreign_keys: Dict[str, tuple] = None,
    ) -> None:

        if table_name in self.get_existing_tables_names:

            self.logger.debug(f"SQLite table '{table_name}' already exists.")

            confirm = input(
                f"SQLite table '{table_name}' already exists. Overwrite? (y/[n])"
            )
            if confirm.lower() != 'y':
                self.logger.debug(
                    f"SQLlite table '{table_name}' not overwritten.")
                return

            self.drop_table(table_name)

        fields_str = ", ".join(
            [f'{field_name} {field_type}'
                for field_name, field_type in table_fields.values()]
        )

        if foreign_keys:
            if not self.foreign_keys_enabled:
                self.switch_foreing_keys(switch=True)

            foreign_keys_str = ", ".join(
                [f'FOREIGN KEY ({field_name}) REFERENCES {ref_table}({ref_field})'
                    for field_name, (ref_field, ref_table) in foreign_keys.items()]
            )
            fields_str += f", {foreign_keys_str}"

        query = f"CREATE TABLE {table_name}({fields_str});"
        self.execute_query(query)

        if foreign_keys:
            self.logger.debug(
                f"SQLite table '{table_name}' - created with foreign keys.")
        else:
            self.logger.debug(f"SQLite table '{table_name}' - created.")

    def switch_foreing_keys(
            self,
            switch: bool,
    ) -> None:
        if switch:
            if self.foreign_keys_enabled:
                self.logger.debug('Foreign keys already enabled.')
            else:
                self.execute_query('PRAGMA foreign_keys = ON;')
                self.foreign_keys_enabled = True
                self.logger.debug('Foreign keys enabled.')
        else:
            self.execute_query('PRAGMA foreign_keys = OFF;')
            self.foreign_keys_enabled = False
            self.logger.debug('Foreign keys disabled.')

    def get_foreign_keys(
            self,
            table_name: str,
    ):
        query = f"PRAGMA foreign_key_list({table_name})"
        self.execute_query(query)
        return self.cursor.fetchall()

    def add_table_column(
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

    def count_table_data_entries(
            self,
            table_name: str
    ) -> int:
        self.execute_query(f'SELECT COUNT(*) FROM {table_name}')
        return self.cursor.fetchone()[0]

    def delete_all_table_entries(self, table_name: str) -> None:
        num_entries = self.count_table_data_entries(table_name=table_name)
        self.execute_query(f"DELETE FROM {table_name}")
        self.logger.debug(
            f"SQLite table '{table_name}' - {num_entries} entries deleted.")

    # questo metodo non funziona, perchè prima bisogna fare in modo che i
    # il dataframe e la tabella sql abbiano i valori definiti con gli stessi tipi
    # (str, int, float). Si potrebbe lavorare sull'importazione da excel per far
    # sì che i tipi dei valori siano assegnati sulla base di constants.py
    def update_table_data(
            self,
            table_name: str,
            dataframe: pd.DataFrame,
    ) -> None:

        table_fields = self.get_table_fields(table_name=table_name)

        if dataframe.columns.tolist() != table_fields['labels']:
            error = f"Passed Dataframe and SQLite table '{table_name}' " \
                    "headers mismatch."
            self.logger.error(error)
            raise ValueError(error)

        num_entries = self.count_table_data_entries(table_name)

        if num_entries == 0:
            error = f"SQLite table '{table_name}' is empty. Cannot update values."
            self.logger.error(error)
            raise ValueError(error)

        data_table = self.table_to_dataframe(table_name=table_name)
        different_rows = (data_table != dataframe).any(axis=1)
        data_table.loc[different_rows] = dataframe.loc[different_rows]

        confirm = input(
            f"Update {sum(different_rows)} rows in SQLite table '{table_name}'?"
        )
        if confirm.lower() != 'y':
            self.logger.debug(
                f"SQLite table '{table_name}' update cancelled.")
            return

        primary_key_column = self.get_primary_column_name(table_name)
        update_query = f"""
            UPDATE {table_name}
            SET {', '.join([f'"{col}" = ?' for col in data_table.columns[1:]])} 
            WHERE "{primary_key_column}" = ?
        """

        try:
            self.cursor.executemany(
                update_query,
                [tuple(row[1:]) + (row[0],)
                 for row in data_table.values.tolist()]
            )
            self.connection.commit()
            self.logger.debug(
                f"SQLite table '{table_name}' - {sum(different_rows)}.")
        except sqlite3.IntegrityError as error:
            if str(error).startswith('UNIQUE'):
                error = f"SQLite table '{table_name}' - Updated data " \
                        "violates unique constraint."
            self.logger.error(error)

    # questo può essere migliorato: deve confrontare dataframe e tabella, e
    # tutto quello che c'è già in tabella che è uguale al df non toccarlo, ma
    # aggiungere/cambiare solo elementi diversi.
    # magari si può mettere un parametro che faccia scegliere tra:
    # 1. cancella sostituisci tutto
    # 2. confronta e aggiorna solo elementi diversi da df a tabella
    # alla fine il risultato sarà lo stesso, ma almeno con opzione 2 si ha
    # controllo di cosa è stato cambiato.
    def dataframe_to_table(
            self,
            table_name: str,
            dataframe: pd.DataFrame,
            overwrite: bool = False,
    ) -> None:

        table_fields = self.get_table_fields(table_name=table_name)

        if dataframe.columns.tolist() != table_fields['labels']:
            error = f"Dataframe and SQLite table '{table_name}' headers mismatch."
            self.logger.error(error)
            raise ValueError(error)

        num_entries = self.count_table_data_entries(table_name=table_name)
        data = [tuple(row) for row in dataframe.values.tolist()]

        if num_entries > 0:
            if not overwrite:
                confirm = input(
                    f"SQLite table '{table_name}' already has {num_entries} rows. "
                    "Delete all table entries and substitute with new data? (y/[n])"
                )
                if confirm.lower() != 'y':
                    self.logger.debug(
                        f"SQLite table '{table_name}' - not overwritten.")
                    return

            self.delete_all_table_entries(table_name=table_name)

        placeholders = ', '.join(['?'] * len(dataframe.columns))
        query = f"INSERT INTO {table_name} VALUES ({placeholders})"

        try:
            self.cursor.executemany(query, data)
            self.connection.commit()
            self.logger.debug(
                f"SQLite table '{table_name}' - {len(data)} entries added."
            )
        except sqlite3.IntegrityError as error:
            if str(error).startswith('UNIQUE'):
                error = f"SQLite table '{table_name}' - Data already exist."
            self.logger.error(error)

    def table_to_dataframe(
            self,
            table_name: str,
    ) -> pd.DataFrame:

        self.execute_query(f"SELECT * FROM {table_name}")
        table = self.cursor.fetchall()
        table_fields = self.get_table_fields(table_name=table_name)
        return pd.DataFrame(table, columns=table_fields['labels'])

    def table_to_excel(
            self,
            excel_filename: str,
            excel_dir_path: Path,
            table_name: str,
    ) -> None:
        excel_file_path = Path(excel_dir_path, excel_filename)

        mode = 'a' if excel_file_path.exists() else 'w'
        if_sheet_exists = 'replace' if mode == 'a' else None

        if excel_file_path.exists() and if_sheet_exists != 'replace':
            confirm = input(
                f"File {excel_filename} already exists. \
                    Do you want to overwrite it? (y/[n])"
            )
            if confirm.lower() != 'y':
                self.logger.warning(
                    f"File '{excel_filename}' not overwritten.")
                return

        self.logger.debug(
            f"SQLite table '{table_name}' - exported to {excel_filename}.")

        with pd.ExcelWriter(
            excel_file_path,
            engine=self.xls_engine,
            mode=mode,
            if_sheet_exists=if_sheet_exists,
        ) as writer:
            query = f'SELECT * FROM {table_name}'
            df = pd.read_sql_query(query, self.connection)
            df.to_excel(writer, sheet_name=table_name, index=False)

    def filtered_table_to_dataframe(
            self,
            table_name: str,
            filters_dict: Dict[str, List[str]],
    ) -> pd.DataFrame:

        conditions = " AND ".join(
            [f"{key} IN ({', '.join(['?']*len(values))})"
             for key, values in filters_dict.items()]
        )

        flattened_values = []
        for list_values in filters_dict.values():
            for value in list_values:
                flattened_values.append(value)

        query = f"SELECT * FROM {table_name} WHERE {conditions};"

        result = pd.read_sql_query(
            query, self.connection, params=flattened_values)

        if result.values.tolist() == []:
            self.logger.warning(
                f"Filtered table from '{table_name}' is empty.")

        return result

    def get_related_table_keys(
            self,
            child_column_name: str,
            parent_table_name: str,
            parent_table_fields: Dict[str, List[str]],
    ) -> Dict[str, List[str]]:

        conditions = " AND ".join(
            [f"{key} IN ({' ,'.join('?')*len(values)})"
             for key, values in parent_table_fields.items()]
        )

        flattened_values = []
        for list_values in parent_table_fields.values():
            for value in list_values:
                flattened_values.append(value)

        query = f"SELECT {child_column_name} FROM {parent_table_name} WHERE {conditions}"

        result = pd.read_sql_query(
            query, self.connection, params=flattened_values
        )

        column_values = result[child_column_name].tolist()
        return {child_column_name: column_values}


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
