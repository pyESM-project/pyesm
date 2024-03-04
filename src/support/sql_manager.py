from functools import wraps
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import sqlite3

import pandas as pd

from src.log_exc.exceptions import *
from src.log_exc.logger import Logger
from src import constants
from src.support import util


class SQLManager:

    def __init__(
        self,
        logger: Logger,
        database_path: Path,
        database_name: str,
        xls_engine: str = 'openpyxl',
    ) -> None:
        """Initialize the SQLManager.

        Args:
            logger (Logger): Logger object.
            database_path (Path): Path to the SQLite database.
            database_name (str): Name of the SQLite database.
            xls_engine (str, optional): Engine to use for Excel writing. 
                Defaults to 'openpyxl'.
        """
        self.logger = logger.getChild(__name__)
        self.logger.info(f"'{self}' object generation.")

        self.database_sql_path = database_path
        self.database_name = database_name
        self.xls_engine = xls_engine

        self.connection = None
        self.cursor = None
        self.foreign_keys_enabled = None

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def open_connection(self) -> None:
        """Opens a connection to the SQLite database.
        If the connection is not already established, it creates a new 
        connection to the specified SQLite database file. It also initializes a 
        cursor for executing SQL queries. If there is an error during the 
        connection process, it logs the error and raises the caught exception.

        Returns:
            None

        Raises:
            sqlite3.Error: If there is an error in establishing the database 
            connection.
        """
        if self.connection is None:
            try:
                self.connection = sqlite3.connect(f'{self.database_sql_path}')
                self.cursor = self.connection.cursor()
                self.logger.debug(
                    f"Connection to '{self.database_name}' opened.")
            except sqlite3.Error as error:
                self.logger.error(
                    f"Error opening connection to '{self.database_name}'")
                raise

        else:
            self.logger.warning(
                f"Connection to '{self.database_name}' already opened.")

    def close_connection(self) -> None:
        """Closes the connection to the SQLite database.
        If a connection is currently open, it closes the connection and sets
        the connection attribute to None. If no connection exists, it logs a
        warning message indicating that no connection is open.

        Returns:
            None

        Raises:
            sqlite3.Error: If there is an error in closing the database 
            connection.
        """
        if self.connection:
            try:
                self.connection.close()
                self.connection = None
                self.logger.debug(
                    f"Connection to '{self.database_name}' closed.")
            except sqlite3.Error as error:
                self.logger.error(
                    f"Error closing connection to '{self.database_name}'")
                raise

        else:
            self.logger.warning(
                f"Connection to '{self.database_name}' "
                "already closed or does not exist.")

    def execute_query(
            self,
            query: str,
            params: tuple = (),
            many: bool = False,
            fetch: bool = False,
            commit: bool = True,
    ) -> Optional[List[Tuple]]:
        """Executes an SQL query on the SQLite database.

        Args:
            query (str): The SQL query to be executed.
            params (tuple, optional): Parameters to be used in the query. 
                Default is an empty tuple.
            many (bool, optional): Set to True if executing a many-parameter 
                query. Default is False.
            fetch (bool, optional): Set to True if the query returns data that 
            needs to be fetched. Default is False.
            commit (bool, optional): Set to False to skip changes commit, 
                True otherwise. Default is True.

        Returns:
            Optional[List[Tuple]]: A list of tuples containing the fetched data 
            if fetch is True, None otherwise.

        Raises:
            OperationalError: If there is an operational error during query execution.
            IntegrityError: If there is an integrity error during query execution.
        """
        try:
            if many:
                self.cursor.executemany(query, params)
            else:
                self.cursor.execute(query, params)

            if commit:
                self.connection.commit()

            if fetch:
                return self.cursor.fetchall()
            else:
                return None

        except sqlite3.OperationalError as op_error:
            self.logger.error(op_error)
            raise OperationalError(op_error)

        except sqlite3.IntegrityError as int_error:
            self.logger.error(int_error)
            raise IntegrityError(int_error)

    @property
    def get_existing_tables_names(self) -> List[str]:
        """Retrieve a list of existing table names in the SQLite database.

        Returns:
            List[str]: A list containing the names of existing tables in the 
            database.
        """
        query = "SELECT name FROM sqlite_master WHERE type='table'"
        self.execute_query(query)
        tables = self.cursor.fetchall()

        return [table[0] for table in tables]

    def check_table_exists(self, table_name: str) -> None:
        """Check if a table exists in the SQLite database.

        Args:
            table_name (str): The name of the table to check.

        Raises:
            TableNotFoundError: If the specified table does not exist in 
            the database.
        """
        if table_name not in self.get_existing_tables_names:
            msg = f"SQLite table '{table_name}' NOT found."
            self.logger.error(msg)
            raise TableNotFoundError(msg)

    def get_primary_column_name(self, table_name: str) -> str:
        """Retrieve the name of the primary key column for a given SQLite table.

        Args:
            table_name (str): The name of the SQLite table.

        Returns:
            str: The name of the primary key column.

        Raises:
            ValueError: If the table does not have a unique primary key column.
        """
        query = f"PRAGMA table_info({table_name})"
        self.execute_query(query)
        table_info = self.cursor.fetchall()

        primary_key_columns = [
            column[1] for column in table_info if column[5] == 1
        ]

        if len(primary_key_columns) == 1:
            return primary_key_columns[0]
        elif len(primary_key_columns) == 0:
            raise ValueError(
                f"SQLite table '{table_name}' does NOT have a primary key column.")
        else:
            raise ValueError(
                "SQLite table '{table_name}' has multiple primary key "
                f"columns: {primary_key_columns}")

    def drop_table(self, table_name: str) -> None:
        """Drops an SQLite table.

        Args:
            table_name (str): The name of the table to be dropped.

        Returns:
            None

        Raises:
            OperationalError: If there is an operational error during table 
            dropping.
        """
        query = f"DROP TABLE {table_name}"
        self.execute_query(query)
        self.logger.debug(f"SQLite '{table_name}' - deleted.")

    def get_table_fields(self, table_name: str) -> Dict[str, str]:
        """Retrieve the fields and their corresponding types for a given 
        SQLite table.

        Args:
            table_name (str): The name of the SQLite table.

        Returns:
            Dict[str, List[str]]: A dictionary containing two lists:
                - 'labels': List of field names.
                - 'types': List of corresponding field types.
        """
        query = f"PRAGMA table_info('{table_name}')"
        result = self.execute_query(query, fetch=True)

        table_fields = {}
        table_fields['labels'] = [row[1] for row in result]
        table_fields['types'] = [row[2] for row in result]

        return table_fields

    def create_table(
            self,
            table_name: str,
            table_fields: Dict[str, List[str]],
            foreign_keys: Dict[str, tuple] = None,
    ) -> None:
        """Create an SQLite table with the specified name, fields and foreign 
        keys (optional).

        Args:
            table_name (str): The name of the SQLite table.
            table_fields (Dict[str, List[str]]): A dictionary containing 
            two lists:
                - 'labels': List of field names.
                - 'types': List of corresponding field types.
            foreign_keys (Dict[str, tuple], optional): A dictionary 
                representing foreign key constraints. Keys are field names, 
                and values are tuples (referencing_field, referenced_table).

        Returns:
            None

        Raises:
            OperationalError: If there is an operational error during 
            table creation.
        """
        if table_name in self.get_existing_tables_names:
            self.logger.debug(f"SQLite table '{table_name}' already exists.")

            confirm = input(
                f"SQLite table '{table_name}' already exists. "
                "Overwrite? (y/[n])"
            )
            if confirm.lower() != 'y':
                self.logger.debug(
                    f"SQLlite table '{table_name}' NOT overwritten.")
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

    def switch_foreing_keys(self, switch: bool) -> None:
        """Enable or disable foreign keys in the SQLite database.

        Args:
            switch (bool): Set to True to enable foreign keys, False to disable.

        Returns:
            None
        """
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

    def add_table_column(
            self,
            table_name: str,
            column_name: str,
            column_type: str,
            default_value: Any = None,
            commit: bool = True,
    ) -> None:
        """Add a column to an SQLite table.

        Args:
            table_name (str): The name of the SQLite table.
            column_name (str): The name of the column to be added.
            column_type (str): The SQLite data type of the new column.
            default_value (Any, optional): The default value for the new column. 
                Default is None.
            commit (bool, optional): Set to True to commit the changes, 
                False otherwise. Default is True.

        Returns:
            None

        Raises:
            Exception: In case of errors in adding column to SQLite table.
        """
        try:
            query = f"""
                ALTER TABLE {table_name} 
                ADD COLUMN "{column_name}" {column_type}
            """

            if default_value is not None:
                query += f" DEFAULT {default_value}"

            self.execute_query(query, commit=commit)
            self.logger.debug(
                f"SQLite table '{table_name}' - column '{column_name}' added.")

        except Exception as msg:
            self.logger.error(f"Error adding column to table: {msg}")

    def count_table_data_entries(self, table_name: str) -> int:
        """Count the number of entries in an SQLite table.

        Args:
            table_name (str): The name of the SQLite table.

        Returns:
            int: The number of entries in the table.
        """
        query = f'SELECT COUNT(*) FROM {table_name}'
        self.execute_query(query)
        return self.cursor.fetchone()[0]

    def delete_all_table_entries(self, table_name: str) -> bool:
        """Delete all entries in an SQLite table.

        Args:
        table_name (str): The name of the SQLite table.

        Returns:
            True if entries are deleted, False if user chooses not to delete.
        """
        num_entries = self.count_table_data_entries(table_name)

        if num_entries > 0:
            confirm = input(
                f"SQLite table '{table_name}' already has {num_entries} "
                "rows. Delete all table entries? (y/[n])"
            )
            if confirm.lower() != 'y':
                self.logger.debug(
                    f"SQLite table '{table_name}' - NOT overwritten.")
                return False

        query = f"DELETE FROM {table_name}"
        self.execute_query(query)

        self.logger.debug(
            f"SQLite table '{table_name}' - {num_entries} entries deleted.")

        return True

    def validate_table_dataframe_headers(
            self,
            table_name: str,
            dataframe: pd.DataFrame,
            check_id_field: bool = False,
    ) -> None:
        """Validate that the headers of a DataFrame match the headers of an 
        SQLite table.

        Args:
            table_name (str): The name of the SQLite table.
            dataframe (pd.DataFrame): The DataFrame to be validated.
            check_id_field (bool, optional): Set to True to exclude the 
                primary key field from the check. Default is False.

        Raises:
            ValueError: If the headers of the DataFrame and the SQLite table 
                mismatch.
        """
        field_id = self.get_primary_column_name(table_name)
        table_fields = self.get_table_fields(table_name)['labels']
        extra_header = set(table_fields) - set(dataframe.columns.tolist())

        if not check_id_field and extra_header == {field_id}:
            return

        if dataframe.columns.tolist() != table_fields:
            msg = f"Passed DataFrame and SQLite table '{table_name}' headers mismatch."
            self.logger.error(msg)
            raise ValueError(msg)

    def add_primary_keys_from_table(
            self,
            table_name: str,
            dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        """Get primary keys from an SQLite table and add them to a DataFrame.

        Args:
            table_name (str): The name of the SQLite table.
            dataframe (pd.DataFrame): The DataFrame to which primary keys 
                will be added.

        Returns:
            pd.DataFrame: The DataFrame with primary keys added.

        Raises:
            TableNotFoundError: If the specified table does not exist.
            ValueError: If DataFrame and table headers mismatch.
        """
        self.check_table_exists(table_name)
        self.validate_table_dataframe_headers(
            table_name=table_name,
            dataframe=dataframe,
            check_id_field=True
        )

        table_df = self.table_to_dataframe(table_name)
        primary_key_field = self.get_primary_column_name(table_name)
        values_field = constants._STD_VALUES_FIELD['values'][0]
        cols_common = [
            col for col in table_df.columns
            if col not in [primary_key_field, values_field]
        ]

        merged_df = pd.merge(
            left=dataframe,
            right=table_df,
            on=cols_common,
            how='inner',
            suffixes=('_to', '_from'))

        dataframe[primary_key_field] = merged_df[primary_key_field + '_from']
        return dataframe

    def table_to_dataframe(
            self,
            table_name: str,
    ) -> pd.DataFrame:
        """Retrieve data from an SQLite table and convert it to a Pandas DataFrame.

        Args:
            table_name (str): The name of the SQLite table.

        Returns:
            pd.DataFrame: A DataFrame containing the table data.

        Raises:
            TableNotFoundError: If the specified table does not exist.
            OperationalError: If there is an error during query execution.
        """
        self.check_table_exists(table_name)
        table_fields = self.get_table_fields(table_name)

        query = f"SELECT * FROM {table_name}"
        table = self.execute_query(query, fetch=True)

        return pd.DataFrame(data=table, columns=table_fields['labels'])

    def dataframe_to_table(
        self,
        table_name: str,
        dataframe: pd.DataFrame,
        operation: str = 'overwrite',
    ) -> None:
        """Add or update a SQLite table based on data provided by a Pandas 
        DataFrame.

        Args:
            table_name (str): The name of the target SQLite table.
            dataframe (pd.DataFrame): The Pandas DataFrame to be written to 
                the table.
            operation (str, optional): The operation to perform ('overwrite' 
                or 'update'). Defaults to 'overwrite'.

        Returns:
            None

        Raises:
            ValueError: If the specified operation is not valid.
            TableNotFoundError: If the specified table does not exist.
            ValueError: If DataFrame and table headers mismatch.
            OperationalError: If there is an error during query execution.

        Notes:
            - The 'overwrite' operation deletes all existing entries in the table and writes
            the new data.
            - The 'update' operation updates existing entries based on common columns and
            adds new entries if they do not exist.

        """
        valid_operations = ['overwrite', 'update']
        util.validate_selection(valid_operations, operation)

        self.check_table_exists(table_name)
        self.validate_table_dataframe_headers(table_name, dataframe)

        table_fields = self.get_table_fields(table_name)['labels']
        num_entries = self.count_table_data_entries(table_name)
        primary_column_label = self.get_primary_column_name(table_name)

        if operation == 'overwrite' or (operation == 'update' and num_entries == 0):

            if num_entries != 0:
                data_erased = self.delete_all_table_entries(table_name)

                if not data_erased:
                    self.logger.debug(
                        f"SQLite table '{table_name}' - original data NOT erased.")
                    return

            if primary_column_label not in dataframe.columns.tolist():
                dataframe.insert(
                    loc=0,
                    column=primary_column_label,
                    value=range(1, len(dataframe) + 1)
                )

            data = [tuple(row) for row in dataframe.values.tolist()]
            placeholders = ', '.join(['?'] * len(table_fields))
            query = f"INSERT INTO {table_name} VALUES ({placeholders})"
            self.execute_query(query, data, many=True)

            self.logger.debug(
                f"SQLite table '{table_name}' - table overwritten and "
                f"{len(data)} entries added.")

        # this has many problems related to non-homogeneous data types in df columns
        elif operation == 'update' and num_entries > 0:

            id_field = constants._STD_ID_FIELD['id'][0]
            values_field = constants._STD_VALUES_FIELD['values'][0]
            cols_common = [
                field for field in table_fields
                if field not in [id_field, values_field]
            ]
            existing_df = self.table_to_dataframe(table_name)

            df_new_values = util.update_dataframes_on_condition(
                existing_df=existing_df,
                new_df=dataframe,
                col_to_update=values_field,
                cols_common=cols_common,
                case='new_only',
            )

            if not df_new_values.empty:
                df_new_values.insert(loc=0, column=id_field, value='')
                data = [tuple(row) for row in df_new_values.values.tolist()]
                placeholders = ', '.join(['?'] * len(table_fields))
                query = f"INSERT INTO {table_name} VALUES ({placeholders})"
                self.execute_query(query, data, many=True)

                self.logger.debug(
                    f"SQLite table '{table_name}' - {len(data)} entries added.")

            df_existing_values = util.update_dataframes_on_condition(
                existing_df=existing_df,
                new_df=dataframe,
                col_to_update=values_field,
                cols_common=cols_common,
                case='existing_updated',
            )

            data = [
                tuple([*row, row[0]])
                for row in df_existing_values.values.tolist()
            ]
            query = f"""
                UPDATE {table_name}
                SET {', '.join([f'"{col}" = ?' for col in df_existing_values.columns])}
                WHERE "{self.get_primary_column_name(table_name)}" = ?
            """
            self.execute_query(query, data, many=True)

            self.logger.debug(
                f"SQLite table '{table_name}' - {len(data)} entries added.")

    def table_to_excel(
            self,
            excel_filename: str,
            excel_dir_path: Path | str,
            table_name: str,
    ) -> None:
        """Export data from an SQLite table to an Excel file.

        Args:
            excel_filename (str): The name of the Excel file.
            excel_dir_path (Path): The directory path where the Excel file will 
                be saved. If it does not exist, it will be created.
            table_name (str): The name of the SQLite table.

        Returns:
            None

        Raises:
            TableNotFoundError: If the specified table does not exist.
            OperationalError: If there is an error during query execution.
        """
        self.check_table_exists(table_name)

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
            path=excel_file_path,
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
        """Filters a SQL table based on the provided filters and returns the 
        result as a pandas DataFrame.

        Args:
            table_name (str): The name of the SQL table to be filtered.
            filters_dict (Dict[str, List[str]]): A dictionary where the keys are 
                the column names and the values are lists of values to filter by.

        Returns:
            pd.DataFrame: A DataFrame containing the filtered results. 
                If no results are found, an empty DataFrame is returned 
                and a warning is logged.

        Raises:
            ValueError: If the table_name is not found in the database.
            TypeError: If the filters_dict is not a dictionary or if the keys 
                of the dictionary are not strings or if the values of the 
                dictionary are not lists of strings.
            Exception: If there is an error during query execution.
        """
        if not isinstance(filters_dict, dict):
            raise TypeError("filters_dict must be a dictionary.")

        for key, values in filters_dict.items():
            if not isinstance(key, str) or not isinstance(values, list):
                msg = "Keys of filters_dict must be strings, and values must be lists of strings."
                self.logger.error(msg)
                raise TypeError(msg)

        conditions = " AND ".join(
            [f"{key} IN ({', '.join(['?']*len(values))})"
             for key, values in filters_dict.items()]
        )

        flattened_values = []
        for list_values in filters_dict.values():
            for value in list_values:
                flattened_values.append(value)

        query = f"SELECT * FROM {table_name} WHERE {conditions};"

        try:
            result = pd.read_sql_query(
                sql=query,
                con=self.connection,
                params=flattened_values
            )
        except Exception as error:
            self.logger.error(error)
            raise

        if result.empty:
            self.logger.warning(
                f"Filtered table from '{table_name}' is empty.")

        return result

    def get_related_table_keys(
            self,
            child_column_name: str,
            parent_table_name: str,
            parent_table_fields: Dict[str, List[str]],
    ) -> Dict[str, List[str]]:
        """Retrieves related keys from a child table based on specified 
        conditions in the parent table. The related keys are meant to be used 
        as 'filter_dict' parameter in 'filtered_table_to_dataframe' method. 

        Args:
            child_column_name (str): The column in the child table from which 
                to retrieve related keys.
            parent_table_name (str): The name of the parent table.
            parent_table_fields (Dict[str, List[str]]): A dictionary where the 
                keys are the column names, and the values are lists of values 
                to filter by.

        Returns:
            Dict[str, List[str]]: A dictionary containing the related keys from 
                the child table.

        Raises:
            Exception: If there is an error during query execution.
        """
        conditions = " AND ".join(
            [f"{key} IN ({' ,'.join('?')*len(values)})"
             for key, values in parent_table_fields.items()]
        )

        flattened_values = []
        for list_values in parent_table_fields.values():
            for value in list_values:
                flattened_values.append(value)

        query = f"""
            SELECT {child_column_name} 
            FROM {parent_table_name} 
            WHERE {conditions}
        """

        try:
            result = pd.read_sql_query(
                sql=query,
                con=self.connection,
                params=flattened_values
            )
        except Exception as error:
            self.logger.error(error)
            raise

        column_values = result[child_column_name].tolist()
        return {child_column_name: column_values}


def connection(method):
    """Decorator to automatically open and close a database connection for a 
    method in a class.

    Args:
        method (function): The method to be decorated.

    Returns:
        function: The decorated method.
    """
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        self.sqltools.open_connection()
        try:
            result = method(self, *args, **kwargs)
        finally:
            self.sqltools.close_connection()
        return result
    return wrapper
