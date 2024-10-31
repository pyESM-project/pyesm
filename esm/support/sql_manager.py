"""
sql_manager.py

@author: Matteo V. Rocco
@institution: Politecnico di Milano

This module defines the SQLManager class responsible for managing SQLite database
interactions in Python using the sqlite3 library. It facilitates various database
operations such as connecting to databases, executing SQL queries, and exporting
data to Excel files. The SQLManager class aims to simplify database management
tasks by providing a set of easy-to-use methods for common SQL operations, ensuring
that database interactions are both efficient and safe.
"""

from typing import List, Dict, Any, Literal, Optional, Tuple
from pathlib import Path
import contextlib
import sqlite3

import pandas as pd

from esm.log_exc import exceptions as exc
from esm.log_exc.logger import Logger
from esm.constants import Constants
from esm.support import util


class SQLManager:
    """
    Manages SQLite database interactions and facilitates data export to Excel files.

    This class simplifies the process of database management by providing methods to
    open and close database connections, execute SQL queries, handle transactions,
    and export tables to Excel files using specific engines. It ensures that all database
    operations are conducted securely and efficiently, leveraging Python's sqlite3
    library functionalities.

    Attributes:
        logger (Logger): An instance of a logging class for logging messages.
        database_sql_path (Path): Path to the SQLite database file.
        database_name (str): Descriptive name of the database used in logs.
        xls_engine (Literal['openpyxl', 'xlsxwriter']): Engine for exporting
            data to Excel.
        connection (Optional[sqlite3.Connection]): Active database connection,
            None if not connected.
        cursor (Optional[sqlite3.Cursor]): Database cursor for executing SQL
            queries, None if not connected.
        foreign_keys_enabled (Optional[bool]): Status of SQLite foreign key
            enforcement in the session.

    Methods:
        - open_connection: Establishes a connection to the SQLite database.
        - close_connection: Closes the current database connection.
        - execute_query: Executes a SQL query with optional parameters.
        - check_table_exists: Checks existence of a table in the database.
        - get_existing_tables_names: Retrieves a list of all tables in the database.
        - table_to_excel: Exports a database table to an Excel file.
        - get_primary_column_name: Finds the primary key column of a table.
        - drop_table: Removes a table from the database.
        - get_table_fields: Fetches field names and types of a table.
        - create_table: Creates a table with specified fields and foreign keys.
        - switch_foreign_keys: Enables or disables foreign key enforcement.
        - add_table_column: Adds a new column to an existing table.
        - count_table_data_entries: Counts entries in a table.
        - delete_all_table_entries: Deletes all entries from a table.
        - validate_table_dataframe_headers: Validates DataFrame headers against
            table schema.
        - add_primary_keys_from_table: Appends primary key values from a table
            to a DataFrame.
        - table_to_dataframe: Converts table contents into a DataFrame.
        - dataframe_to_table: Inserts or updates data from a DataFrame into a table.
        - filtered_table_to_dataframe: Filters a table and returns the results
            as a DataFrame.
        - get_related_table_keys: Retrieves related keys based on parent table filters.

    Examples:
        >>> logger = Logger()
        >>> sql_manager = SQLManager(logger, Path('/path/to/database.db'),
                'MyDatabase', 'openpyxl')
        >>> sql_manager.open_connection()
        >>> sql_manager.execute_query("SELECT * FROM my_table")
        >>> sql_manager.close_connection()

    Note:
        Assumes a valid SQLite database path is provided and that the database
        file is accessible and correctly formatted.
    """

    def __init__(
        self,
        logger: Logger,
        database_path: Path,
        database_name: str,
        xls_engine: Literal['openpyxl', 'xlswriter'] = 'openpyxl',
    ) -> None:
        """
        Initializes the SQLManager instance with necessary database details
        and configurations.

        Args:
            logger (Logger): Logger object for logging database operations.
            database_path (Path): File system path to the SQLite database file.
            database_name (str): Descriptive name of the database for logging
                purposes.
            xls_engine (Literal['openpyxl', 'xlsxwriter']): Preferred engine
                for exporting data to Excel, defaults to 'openpyxl'.

        Sets up the initial state of the SQLManager, preparing it for database
            operations. It logs the creation of the SQLManager instance.
        """
        self.logger = logger.get_child(__name__)
        self.logger.debug(f"'{self}' object generation.")

        self.database_sql_path: Path = database_path
        self.database_name: str = database_name
        self.xls_engine = xls_engine

        self.connection: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
        self.foreign_keys_enabled = None

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def open_connection(self) -> None:
        """
        Opens a connection to the SQLite database.
        Establishes a connection to the specified database file and initializes
        a cursor for executing SQL queries. Logs and re-raises any sqlite3.Error
        encountered during the connection process.

        Raises:
            OperationalError: If there is an error establishing the database
                connection, captured and logged.
        """
        if self.connection is None:
            try:
                self.connection = sqlite3.connect(f'{self.database_sql_path}')
                self.cursor = self.connection.cursor()
                self.logger.debug(
                    f"Connection to '{self.database_name}' opened.")
            except sqlite3.Error as error:
                msg = f"Error opening connection to '{self.database_name}'."
                self.logger.error(msg)
                raise exc.OperationalError(msg) from error

        else:
            self.logger.warning(
                f"Connection to '{self.database_name}' already opened.")

    def close_connection(self) -> None:
        """
        Closes the currently open database connection.
        Terminates the database connection and resets the connection and cursor
        attributes to None. Logs a warning if no connection is open at the time
        of the call.

        Raises:
            OperationalError: If there is an error closing the database connection,
                which is logged.
        """
        if self.connection:
            try:
                self.connection.close()
                self.connection = None
                self.logger.debug(
                    f"Connection to '{self.database_name}' closed.")
            except sqlite3.Error as error:
                msg = f"Error closing connection to '{self.database_name}'."
                self.logger.error(msg)
                raise exc.OperationalError(msg) from error

        else:
            self.logger.warning(
                f"Connection to '{self.database_name}' "
                "already closed or does not exist.")

    def execute_query(
            self,
            query: str,
            params: tuple | List[tuple] = (),
            many: bool = False,
            fetch: bool = False,
            commit: bool = True,
    ) -> Optional[List[Tuple]]:
        """
        Executes a specified SQL query using provided parameters.
        This method supports executing single or multiple SQL commands with
        optional parameterization, fetching results, and committing changes to
        the database. Handles and logs specific sqlite3 exceptions related to
        operation, integrity, database, and programming errors. Rolls back the
        transaction if an error occurs.

        Args:
            query (str): SQL query to be executed.
            params (tuple | List[tuple], optional): Parameters for the SQL query.
            many (bool, optional): Whether to execute the query with multiple
                parameter sets.
            fetch (bool, optional): Whether to fetch and return the query results.
            commit (bool, optional): Whether to commit the transaction after
                query execution.

        Returns:
            Optional[List[Tuple]]: Results of the query if fetched; otherwise,
                None.

        Raises:
            exc.OperationalError: If there is an operational issue during query
                execution.
            exc.IntegrityError: If there is an integrity issue during query
                execution.
            exc.DatabaseError: If there is a database issue during query
                execution.
            exc.ProgrammingError: If there is a programming issue during query
                execution.
        """
        if self.connection is None or self.cursor is None:
            msg = "Database connection or cursor not initialized."
            self.logger.error(msg)
            raise exc.OperationalError(msg)

        try:
            if many:
                self.cursor.executemany(query, params)
            else:
                self.cursor.execute(query, params)

            if commit:
                self.connection.commit()

            if fetch:
                return self.cursor.fetchall()

        except sqlite3.OperationalError as op_error:
            self.connection.rollback()
            msg = str(op_error)
            self.logger.error(msg)
            raise exc.OperationalError(msg) from op_error

        except sqlite3.IntegrityError as int_error:
            self.connection.rollback()
            msg = str(int_error)
            self.logger.error(msg)
            raise exc.IntegrityError(msg) from int_error

        except sqlite3.DatabaseError as db_error:
            self.connection.rollback()
            msg = str(db_error)
            self.logger.error(msg)
            raise exc.MissingDataError(msg) from db_error

    @property
    def get_existing_tables_names(self) -> List[str]:
        """
        Retrieve a list of existing table names in the SQLite database.
        This method queries the database to extract the names of all tables and
        logs any related errors.

        Returns:
            List[str]: A list containing the names of existing tables in the
            database.
        """
        query = "SELECT name FROM sqlite_master WHERE type='table'"
        self.execute_query(query)

        if self.cursor:
            tables = self.cursor.fetchall()

        return [table[0] for table in tables]

    def check_table_exists(self, table_name: str) -> None:
        """
        Verifies the existence of a specified table within the SQLite database.
        Checks against the list of existing tables and logs an error if the
        specified table is not found.

        Args:
            table_name (str): Name of the table to check.

        Raises:
            exc.TableNotFoundError: If the specified table does not exist in
                the database.
        """
        if table_name not in self.get_existing_tables_names:
            msg = f"SQLite table '{table_name}' NOT found."
            self.logger.error(msg)
            raise exc.TableNotFoundError(msg)

    def get_primary_column_name(self, table_name: str) -> str:
        """
        Determines the primary key column name for a specified table.
        This method retrieves and analyzes the table schema to identify the
        primary key column. It raises an error if the table lacks a unique
        primary key.

        Args:
            table_name (str): The name of the table to inspect.

        Returns:
            str: The name of the primary key column.

        Raises:
            ValueError: If the table does not have a unique primary key column
                or has multiple primary key columns.
        """
        query = f"PRAGMA table_info({table_name})"
        self.execute_query(query)

        if self.cursor:
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
        """
        Deletes a specified table from the SQLite database.
        This method constructs and executes a SQL command to drop the table and
        logs the action. It checks for operational errors during the execution.

        Args:
            table_name (str): The name of the table to be dropped.
        """
        query = f"DROP TABLE {table_name}"
        self.execute_query(query)
        self.logger.debug(f"SQLite '{table_name}' - deleted.")

    def get_table_fields(self, table_name: str) -> Dict[str, str]:
        """
        Fetches and returns the field names and data types for a specified table.
        Queries the database schema to determine the structure of the given table,
        providing insights into its composition.

        Args:
            table_name (str): The name of the table to query.

        Returns:
            Dict[str, List[str]]: A dictionary with lists of field names
                ('labels') and their corresponding data types ('types').

        Raises:
            exc.MissingDataError: If the table fields are not available or
                the query fails.
        """
        query = f"PRAGMA table_info('{table_name}')"
        result = self.execute_query(query, fetch=True)

        if result is not None:
            table_fields = {}
            table_fields['labels'] = [row[1] for row in result]
            table_fields['types'] = [row[2] for row in result]
        else:
            msg = f"Table fields missing in table '{table_name}'"
            self.logger.warning(msg)
            raise exc.MissingDataError(msg)

        return table_fields

    def create_table(
            self,
            table_name: str,
            table_fields: Dict[str, List[str]],
            foreign_keys: Optional[Dict[str, tuple]] = None,
    ) -> None:
        """
        Creates a new table in the SQLite database with specified fields and
        optional foreign keys.
        This method constructs a SQL command to create a table based on provided
        field definitions and foreign key constraints. It logs the creation
        process and handles potential errors.

        Args:
            table_name (str): The name of the table to create.
            table_fields (Dict[str, List[str]]): Dictionary of field names and
                types to define the table structure.
            foreign_keys (Optional[Dict[str, tuple]]): Dictionary specifying
                foreign key constraints. Default is None.
        """
        if table_name in self.get_existing_tables_names:
            self.logger.info(f"SQLite table '{table_name}' already exists.")

            confirm = input(
                f"SQLite table '{table_name}' already exists. "
                "Overwrite? (y/[n])"
            )
            if confirm.lower() != 'y':
                self.logger.info(
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
        """
        Enables or disables the enforcement of foreign key constraints within
        the SQLite database session.
        This method adjusts the foreign key constraint settings based on the
        specified parameter and logs the state change.

        Args:
            switch (bool): True to enable, False to disable foreign key constraints.
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
        """
        Adds a new column to an existing table in the SQLite database.
        This method constructs and executes an ALTER TABLE command to add a
        new column with specified properties. It logs the addition and any
        errors encountered.

        Args:
            table_name (str): The table to modify.
            column_name (str): The name of the new column.
            column_type (str): The data type of the new column.
            default_value (Any, optional): Default value for the new column.
            commit (bool, optional): Whether to commit the transaction immediately.

        Raises:
            OperationalError: If there is an error during the execution of the
                command.
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

        except sqlite3.Error as error:
            msg = f"Error adding column to table: {error}"
            self.logger.error(msg)
            raise exc.OperationalError(msg) from error

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

    def delete_table_entries(
            self,
            table_name: str,
            force_operation: bool = False,
            column_name: Optional[str] = None,
    ) -> bool:
        """
        Deletes values from a specified column in a table in the SQLite database.
        This method executes an UPDATE command to set the values in the specified
        column to NULL, with an optional confirmation to proceed based on user input.
        If no column name is provided, all entries in the table are deleted.

        Args:
            table_name (str): The name of the table from which to delete column entries.
            force_operation (bool, optional): If True, bypasses user confirmation
                and deletes column entries.
            column_name (str, optional): The name of the column from which to
                delete values.

        Returns:
            bool: True if column entries were successfully deleted, False if the
                operation was aborted by the user.

        Notes:
            If there are entries in the column and force_operation is False,
                the method will prompt the user to confirm deletion.
        """
        num_entries = self.count_table_data_entries(table_name)

        if num_entries > 0 and not force_operation:
            confirm = input(
                f"SQLite table '{table_name}' already has {num_entries} rows. Delete all "
                f"{'entries' if column_name is None else f'entries in column {column_name}'}? "
                "(y/[n])")

            if confirm.lower() != 'y':
                self.logger.debug(
                    f"SQLite table '{table_name}' - NOT overwritten.")
                return False

        if column_name:
            query = f"UPDATE {table_name} SET '{column_name}' = NULL"
        else:
            query = f"DELETE FROM {table_name}"

        self.execute_query(query)

        self.logger.debug(
            f"SQLite table '{table_name}' - {num_entries} "
            f"{'entries' if column_name is None else f'entries in column {column_name}'} "
            "deleted.")

        return True

    def validate_table_dataframe_headers(
            self,
            table_name: str,
            dataframe: pd.DataFrame,
            check_id_field: bool = False,
    ) -> None:
        """
        Validates that the headers of a DataFrame match the schema of a specified
        SQLite table.
        This method ensures that the DataFrame columns align with the table's
        field names, optionally excluding the primary key field from the validation.

        Args:
            table_name (str): The table against which to validate the DataFrame
                headers.
            dataframe (pd.DataFrame): The DataFrame to validate.
            check_id_field (bool, optional): Whether to exclude the primary key
                field from validation.

        Raises:
            ValueError: If the DataFrame headers do not match the table schema.
        """
        field_id = self.get_primary_column_name(table_name)
        table_fields = self.get_table_fields(table_name)['labels']
        extra_header = set(table_fields) - set(dataframe.columns.tolist())

        if not check_id_field and extra_header == {field_id}:
            return

        if dataframe.columns.tolist() != table_fields:
            mismatched_headers = set(dataframe.columns) - set(table_fields)
            msg = f"Passed DataFrame and SQLite table '{table_name}' headers " \
                f"mismatch. Mismatched headers: '{mismatched_headers}'"
            self.logger.error(msg)
            raise ValueError(msg)

    def add_primary_keys_from_table(
            self,
            table_name: str,
            dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Adds primary key values from a specified SQLite table to a DataFrame
        based on common columns.
        This method merges primary key values from the table into the DataFrame,
        ensuring that the DataFrame headers are properly aligned with the table
        schema before proceeding.

        Args:
            table_name (str): The name of the table from which to add primary keys.
            dataframe (pd.DataFrame): The DataFrame to which primary keys will
                be added.

        Returns:
            pd.DataFrame: The modified DataFrame with primary keys included.
        """
        self.check_table_exists(table_name)
        self.validate_table_dataframe_headers(
            table_name=table_name,
            dataframe=dataframe,
            check_id_field=True
        )

        table_df = self.table_to_dataframe(table_name)
        primary_key_field = self.get_primary_column_name(table_name)
        values_field = Constants.get('_STD_VALUES_FIELD')['values'][0]
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

    def dataframe_to_table(
        self,
        table_name: str,
        dataframe: pd.DataFrame,
        force_overwrite: bool = False,
        suppress_warnings: bool = False,
    ) -> None:
        """
        Inserts or updates the given DataFrame into the specified SQLite table.

        Args:
            table_name (str): The name of the SQLite table.
            dataframe (pd.DataFrame): The DataFrame to be inserted into the 
                table.
            force_overwrite (bool, optional): If True, existing table entries 
                will be overwritten without asking user permission. Defaults to 
                False.
            suppress_warnings (bool, optional): If True, suppresses warning 
                messages. Defaults to False.
        """
        self.check_table_exists(table_name)
        self.validate_table_dataframe_headers(table_name, dataframe)

        id_field = Constants.get('_STD_ID_FIELD')['id'][0]
        values_field = Constants.get('_STD_VALUES_FIELD')['values'][0]
        table_fields = self.get_table_fields(table_name)['labels']
        table_primary_column = self.get_primary_column_name(table_name)
        table_existing_entries = self.count_table_data_entries(table_name)
        dataframe_existing = self.table_to_dataframe(table_name)
        existing_values: pd.Series = dataframe_existing[values_field]

        # add primary key column if not present
        if table_primary_column not in dataframe.columns.tolist():
            dataframe.insert(
                loc=0,
                column=table_primary_column,
                value=range(1, len(dataframe) + 1)
            )

        # check if table is already up to date
        if util.check_dataframes_equality(
            df_list=[dataframe_existing, dataframe],
            skip_columns=[id_field],
        ):
            if not suppress_warnings:
                self.logger.warning(
                    f"SQLite table {table_name} already up to date.")
            return

        # reorder columns to match table schema
        if not all(dataframe.columns == table_fields):
            dataframe = dataframe[table_fields]

        data = [tuple(row) for row in dataframe.values.tolist()]
        placeholders = ', '.join(['?'] * len(table_fields))

        # define appropriate query based on table state
        if table_existing_entries == 0:
            query = f"INSERT INTO {table_name} VALUES ({placeholders})"

        elif table_existing_entries > 0:
            if existing_values.isnull().all():
                query = f"INSERT OR REPLACE INTO {table_name} VALUES ({placeholders})"
            else:
                if not self.delete_table_entries(table_name, force_overwrite):
                    self.logger.debug(
                        f"SQLite table '{table_name}' - original data NOT erased.")
                    return
                query = f"INSERT INTO {table_name} VALUES ({placeholders})"

        self.execute_query(query=query, params=data, many=True)

        self.logger.debug(
            f"SQLite table '{table_name}' - table values overwritten: "
            f"{len(data)} new entries added.")

    def table_to_excel(
            self,
            excel_filename: str,
            excel_dir_path: Path | str,
            table_name: str,
    ) -> None:
        """
        Exports the data from a specified SQLite table to an Excel file using
        the configured Excel engine.
        This method prepares the data from the table and writes it to an Excel
        file at the specified location, offering options to overwrite existing
        files based on user input.

        Args:
            excel_filename (str): The filename for the Excel export.
            excel_dir_path (Path | str): The directory path where the Excel file
                will be saved.
            table_name (str): The name of the table whose data is being exported.

        Returns:
            None
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

    def table_to_dataframe(
            self,
            table_name: str,
            filters_dict: Optional[Dict[str, List[str]]] = None,
    ) -> pd.DataFrame:
        """
        Filters a specified SQLite table based on given conditions and returns
        the filtered data as a pandas DataFrame.
        This method constructs a SQL query using the provided filter conditions
        and retrieves the matching records. It handles data type validation
        for the filter conditions and logs any errors or warnings if the resulting
        DataFrame is empty.

        Args:
            table_name (str): The name of the table to filter.
            filters_dict (Optional[Dict[str, List[str]]]): Conditions for filtering 
                the table, with column names as keys and lists of acceptable values
                as values.

        Returns:
            pd.DataFrame: A DataFrame containing the filtered results. Returns
                an empty DataFrame if no records match.

        Raises:
            TypeError: If the filters_dict is incorrectly structured.
            OperationalError: If there is an error during query execution.
        """
        self.check_table_exists(table_name)
        table_fields = self.get_table_fields(table_name)
        table_columns_labels = list(table_fields['labels'])

        if not filters_dict:
            query = f"SELECT * FROM {table_name}"
            flattened_values = []
        else:
            if not isinstance(filters_dict, dict):
                raise TypeError(
                    "Passed filters_dict must be a dictionary. "
                    f"{type(filters_dict)} was passed instead.")

            for key, values in filters_dict.items():
                if not isinstance(key, str) or not isinstance(values, list):
                    msg = "Keys of filters_dict must be strings, and values " \
                        "must be lists of strings."
                    self.logger.error(msg)
                    raise TypeError(msg)

            conditions = " AND ".join(
                [f"{key} IN ({', '.join(['?']*len(values))})"
                 for key, values in filters_dict.items()]
            )

            flattened_values = [
                str(value) for values in filters_dict.values()
                for value in values
            ]

            query = f"SELECT * FROM {table_name} WHERE {conditions};"

        table = self.execute_query(
            query=query,
            params=tuple(flattened_values),
            fetch=True
        )

        dataframe = pd.DataFrame(data=table, columns=table_columns_labels)

        if filters_dict and dataframe.empty:
            self.logger.warning(
                f"Filtered table from '{table_name}' is empty.")

        return dataframe

    def get_related_table_keys(
            self,
            child_column_name: str,
            parent_table_name: str,
            parent_table_fields: Dict[str, List[str]],
    ) -> Dict[str, List[str]]:
        """
        Retrieves keys from a child table that correspond to filtering criteria
        specified in a parent table.
        This method constructs a query to extract keys from the child table
        based on conditions defined for the parent table, which can then be used
        to filter data in subsequent operations.

        Args:
            child_column_name (str): The column name in the child table from
                which to retrieve keys.
            parent_table_name (str): The name of the parent table where filtering
                conditions are specified.
            parent_table_fields (Dict[str, List[str]]): Dictionary specifying the
                filter conditions for the parent table.

        Returns:
            Dict[str, List[str]]: A dictionary containing the retrieved keys from
                the child table.

        Raises:
            OperationalError: If there is an error during query execution.
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
            msg = f"Error retrieving related keys: {error}."
            self.logger.error(msg)
            raise exc.OperationalError(msg) from error

        column_values = result[child_column_name].tolist()
        return {child_column_name: column_values}

    def check_databases_equality(
            self,
            other_db_dir_path: Path | str,
            other_db_name: str,
            check_values: bool = True,
            tolerance_percentage: Optional[float] = None,
    ) -> None:
        """
        Compares the current database with another SQLite database to check
        if they are identical.

        This method checks for the following:
            1. Existence of tables in the source database.
            2. Structure of the tables (schema).
            3. Contents of the tables (coordinates).
            4. Numerical values in the 'values' column with a specified tolerance.

        If any of these checks fail, the method raises a ResultsError and logs the
        details of the failure. If all checks pass, the method logs a success message.

        Args:
            other_db_dir_path (Path | str): Directory path of the other SQLite database.
            other_db_name (str): The name of the other database to compare.
            check_values (bool, optional): Whether to include a comparison of the
                numerical values in the tables. Default is True.
            tolerance_percentage (Optional[float], optional): Tolerance for
                numerical value comparison. Default is None.

        Raises:
            OperationalError: If the connection or cursor of the database to be
                checked are not initialized.
            ModelFolderError: If the other database does not exist or is not correctly named.
            ResultsError: If the databases are not identical in terms of table
                presence, structure, or contents.
        """

        if self.connection is None or self.cursor is None:
            msg = "Connection or cursor of the database to be checked are " \
                "not initialized."
            self.logger.error(msg)
            raise exc.OperationalError(msg)

        other_db_path = Path(other_db_dir_path) / other_db_name

        if not other_db_path.exists():
            msg = "Database with expected results not found or not correctly named."
            self.logger.error(msg)
            raise exc.ModelFolderError(msg)

        other_db_connection = sqlite3.connect(other_db_path)
        other_db_cursor = other_db_connection.cursor()

        try:
            # 1. Check existance of tables in source
            current_tables = self.get_existing_tables_names
            other_db_cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")
            other_tables = [table[0] for table in other_db_cursor.fetchall()]

            tables_not_expected = set(current_tables) - set(other_tables)
            tables_missing = set(other_tables) - set(current_tables)

            if tables_not_expected:
                msg = "Source database has more tables than " \
                    f"expected: {tables_not_expected}."
                self.logger.error(msg)
                raise exc.ResultsError(msg)

            if tables_missing:
                msg = "Source database has less tables than " \
                    f"expected: {tables_missing}."
                self.logger.error(msg)
                raise exc.ResultsError(msg)

            # 2. Compare tables structure (schema)
            tables_wrong_structures = []

            for table in current_tables:
                self.cursor.execute(f"PRAGMA table_info({table})")
                current_table_info = self.cursor.fetchall()

                other_db_cursor.execute(f"PRAGMA table_info({table})")
                other_table_info = other_db_cursor.fetchall()

                if current_table_info != other_table_info:
                    tables_wrong_structures.append(table)

            if tables_wrong_structures:
                msg = f"Wrong structures for tables: {tables_wrong_structures}."
                self.logger.error(msg)
                raise exc.ResultsError(msg)

            # 3. Compare table contents (except "values" column)
            tables_wrong_coordinates = []
            values_header = Constants.get('_STD_VALUES_FIELD')['values'][0]

            for table in current_tables:
                self.cursor.execute(f"PRAGMA table_info({table})")
                coords_columns = [
                    info[1]
                    for info in self.cursor.fetchall()
                    if info[1] != values_header
                ]
                columns = ', '.join(coords_columns) if coords_columns else '*'
                query = f"SELECT {columns} FROM {table}"

                self.cursor.execute(query)
                current_rows = [tuple(row) for row in self.cursor.fetchall()]

                other_db_cursor.execute(query)
                other_rows = [tuple(row) for row in other_db_cursor.fetchall()]

                if current_rows != other_rows:
                    tables_wrong_coordinates.append(table)

            if tables_wrong_coordinates:
                msg = "Source and expected coordinates not matching for " \
                    f"tables: {tables_wrong_coordinates}."
                self.logger.error(msg)
                raise exc.ResultsError(msg)

            # 4. Compare "values" column with numerical tolerance
            if not check_values:
                self.logger.debug(
                    "Passed SQLite databases are equal (excluding values).")
                return

            if tolerance_percentage is None:
                msg = "Tolerance percentage not provided for numerical values."
                self.logger.error(msg)
                raise exc.SettingsError(msg)

            tables_wrong_values = {}

            for table in current_tables:
                self.cursor.execute(f"PRAGMA table_info({table})")
                columns = [info[1] for info in self.cursor.fetchall()]

                if values_header not in columns:
                    continue

                query = f"SELECT \"{values_header}\" FROM \"{table}\""

                self.cursor.execute(query)
                current_values = [row[0] for row in self.cursor.fetchall()]

                other_db_cursor.execute(query)
                other_values = [row[0] for row in other_db_cursor.fetchall()]

                relative_differences = [
                    util.calculate_values_difference(
                        value_1=cv,
                        value_2=ov,
                        modules_difference=True,
                        ignore_nan=True,
                    )
                    for cv, ov in zip(current_values, other_values)
                ]

                rounding_digits = Constants.get(
                    '_ROUNDING_DIGITS_RELATIVE_DIFFERENCE_DB')

                if any([
                    rd > tolerance_percentage
                    for rd in relative_differences
                    if rd is not None
                ]):
                    tables_wrong_values[table] = round(
                        max(relative_differences), rounding_digits)

            if tables_wrong_values:
                msg = "Maximum numerical differences in 'values' column " \
                    "exceeding maximum tolerance for tables: " \
                    f"{tables_wrong_values}."
                self.logger.error(msg)
                raise exc.ResultsError(msg)

            self.logger.debug(
                "Passed SQLite databases are equal (including values).")

        finally:
            other_db_connection.close()

    def get_tables_values_relative_difference(
            self,
            other_db_dir_path: Path | str,
            other_db_name: str,
            tables_names: Optional[List[str]] = None,
    ) -> Dict[str, float]:
        """
        Compare the values in specified tables of two SQLite databases and return
        the maximum relative difference for each table. The relative difference
        is calculated as the absolute difference between the values divided by
        the absolute value of the 'other database' values.

        Parameters:
            other_db_dir_path (Path | str): The directory path of the other
                SQLite database.
            other_db_name (str): The name of the other SQLite database.
            tables_names (Optional[List[str]], optional): Specific tables to
                compare; if None, all tables are compared.

        Returns:
            Dict[str, float]: A dictionary where the keys are the table names
                and the values are the maximum relative differences.

        Raises:
            exc.OperationalError: If the connection or cursor is not initialized.
            exc.ModelFolderError: If the comparison database does not exist or
                is misnamed.
            exc.TableNotFoundError: If specified tables are not found in the database.
        """
        if self.connection is None or self.cursor is None:
            msg = "Connection or cursor of the database to be checked are "
            "not initialized."
            self.logger.error(msg)
            raise exc.OperationalError(msg)

        other_db_path = Path(other_db_dir_path) / other_db_name

        if not other_db_path.exists():
            msg = "Database necessary for comparison not found or not "
            "correctly named."
            self.logger.error(msg)
            raise exc.ModelFolderError(msg)

        other_db_connection = sqlite3.connect(other_db_path)
        other_db_cursor = other_db_connection.cursor()

        self.check_databases_equality(
            other_db_dir_path=other_db_dir_path,
            other_db_name=other_db_name,
            check_values=False,
        )

        if tables_names is None:
            tables_names = self.get_existing_tables_names
        else:
            if not all([
                table in self.get_existing_tables_names
                for table in tables_names
            ]):
                msg = "One or more tables not found in the database."
                self.logger.error(msg)
                raise exc.TableNotFoundError(msg)

        max_relative_difference = {}

        try:
            for table in tables_names:
                self.cursor.execute(f"SELECT \"values\" FROM \"{table}\"")
                current_values = [row[0] for row in self.cursor.fetchall()]

                other_db_cursor.execute(f"SELECT \"values\" FROM \"{table}\"")
                other_values = [row[0] for row in other_db_cursor.fetchall()]

                relative_differences = [
                    util.calculate_values_difference(
                        value_1=cv,
                        value_2=ov,
                        modules_difference=True,
                        ignore_nan=True,
                    )
                    for cv, ov in zip(current_values, other_values)
                ]

                max_relative_difference[table] = max(relative_differences)

            return max_relative_difference

        finally:
            other_db_connection.close()


@ contextlib.contextmanager
def db_handler(sql_manager: SQLManager):
    """
    A context manager for handling database connections and providing a cursor
    for database operations using a SQLManager object.

    Args:
        sql_manager (SQLManager): The SQLManager object used for managing
            the database connection and operations.

    Yields:
        cursor (sqlite3.Cursor): A cursor for executing SQL commands.

    Raises:
        sqlite3.Error: Any exceptions raised during connection management or
        during SQL operations are logged and re-raised to be handled externally.
    """
    try:
        sql_manager.open_connection()
        yield sql_manager.cursor
    except sqlite3.Error as e:
        sql_manager.logger.error(f"Database error: {e}")
        raise
    finally:
        sql_manager.close_connection()
