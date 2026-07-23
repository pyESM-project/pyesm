"""Module defining the SQLManager class for SQLite database management.

The SQLManager class provides methods to handle SQLite database operations such as
connecting to the database, executing queries, importing and exporting data from
and to various sources.
The SQLManager class interacts with SQLite database in Python using the sqlite3 
library.
"""
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import contextlib
import sqlite3

import pandas as pd

from cvxlab.log_exc import exceptions as exc
from cvxlab.log_exc.logger import Logger
from cvxlab.defaults import Defaults
from cvxlab.support import util


class SQLManager:
    """SQLManager class allows interactions with SQLite databases.

    This class simplifies the process of database management by providing methods to
    open and close database connections, execute SQL queries, handle transactions,
    and export tables to Excel files using specific engines. It ensures that all database
    operations are conducted securely and efficiently, leveraging Python's sqlite3
    library functionalities.

    Attributes:
    - logger (Logger): Logger object for logging information.
    - database_sql_path (Path): Path to the SQLite database file.
    - database_name (str): Descriptive name of the database used in logs.
    - xls_engine (Defaults.LiteralTypes.ExcelEngine): Engine for exporting data to Excel.
    - connection (Optional[sqlite3.Connection]): Active database connection, None if not connected.
    - cursor (Optional[sqlite3.Cursor]): Database cursor for executing SQL queries, None if not connected.
    - foreign_keys_enabled (Optional[bool]): Status of SQLite foreign key enforcement in the session.

    """

    def __init__(
        self,
        logger: Logger,
        database_path: Path,
        database_name: str,
        settings: Dict,
        xls_engine: Defaults.LiteralTypes.ExcelEngine = 'openpyxl',
    ):
        """Initialize the SQLManager class.

        Args:
            logger (Logger): Logger object for logging database operations.
            database_path (Path): File system path to the SQLite database file.
            database_name (str): Descriptive name of the database for logging purposes.
            xls_engine (Defaults.LiteralTypes.ExcelEngine): Preferred engine for exporting 
                data to Excel, defaults to 'openpyxl'.
        """
        self.logger = logger.get_child(__name__)

        self.database_sql_path: Path = database_path
        self.database_name: str = database_name
        self.xls_engine = xls_engine

        self.connection: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
        self.foreign_keys_enabled = None
        self.settings = settings

    @property
    def get_existing_tables_names(self) -> List[str]:
        """Retrieve a list of existing table names in the SQLite database.

        Returns:
            List[str]: A list containing the names of existing tables in the database.
        """
        query = "SELECT name FROM sqlite_master WHERE type='table'"
        result = self.execute_query(query)

        if result is not None:
            return [table[0] for table in result]

        return []

    @property
    def is_uncertainty_enabled(self) -> bool:
        """Return whether uncertainty-analysis functionality is enabled."""
        return self.settings.uncertainty

    def open_connection(self) -> None:
        """Open a connection to the SQLite database.

        This method establishes a connection to the specified database file and 
        initializes a cursor for executing SQL queries. If a connection is already
        open, it logs a warning and does not attempt to reopen the connection.

        Raises:
            OperationalError: If there is an error establishing the database
                connection, captured and logged.
        """
        if self.connection is None:
            try:
                self.connection = sqlite3.connect(f'{self.database_sql_path}')
                self.cursor = self.connection.cursor()
            except sqlite3.Error as error:
                msg = f"Error opening connection to '{self.database_name}'."
                self.logger.error(msg)
                raise exc.OperationalError(msg) from error

        else:
            self.logger.warning(
                f"Connection to '{self.database_name}' already opened.")

    def close_connection(
            self,
            suppress_warning: bool = False,
    ) -> None:
        """Close the currently open database connection.

        Args:
            suppress_warning (bool): If True, suppresses warning messages when
                attempting to close an already closed connection. Defaults to False.

        This method terminates the database connection and resets the connection 
        and cursor attributes to None. If no connection is open, it logs a warning.

        Raises:
            OperationalError: If there is an error closing the database connection,
                which is logged.
        """
        if self.cursor is not None:
            try:
                self.cursor.close()
            except sqlite3.Error as error:
                msg = f"Error closing cursor for '{self.database_name}'."
                self.logger.error(msg)
                raise exc.OperationalError(msg) from error
            finally:
                self.cursor = None

        if self.connection is not None:
            try:
                self.connection.close()
            except sqlite3.Error as error:
                msg = f"Error closing connection to '{self.database_name}'."
                self.logger.error(msg)
                raise exc.OperationalError(msg) from error
            finally:
                self.connection = None
        elif not suppress_warning:
            self.logger.warning(
                f"Connection to '{self.database_name}' "
                "already closed or does not exist.")

    def _infer_query_intent(self, query: str) -> tuple[bool, bool]:
        """Infer default commit and fetch behavior from SQL query string.

        Analyzes the SQL query to detect the leading verb and returns sensible
        defaults for commit and fetch parameters. This reduces boilerplate and
        minimizes programmer error.

        Args:
            query (str): The SQL query to analyze.

        Returns:
            tuple[bool, bool]: A tuple of (default_commit, default_fetch):
                (False, True) for read-only queries (SELECT, PRAGMA, EXPLAIN)
                (True, False) for write queries (INSERT, UPDATE, DELETE, CREATE, ALTER, DROP)
                (True, False) as fallback for unknown verbs (defensive)

        Example:
            >>> mgr._infer_query_intent("SELECT * FROM table")
            (False, True)
            >>> mgr._infer_query_intent("INSERT INTO table VALUES (?)")
            (True, False)
        """
        # Strip leading whitespace and comments
        cleaned = query.strip()
        if cleaned.startswith('--'):
            # Skip comment lines
            cleaned = '\n'.join(
                line.strip() for line in cleaned.split('\n')
                if not line.strip().startswith('--')
            ).strip()
        if cleaned.startswith('/*'):
            # Skip block comments
            cleaned = cleaned[cleaned.find('*/') + 2:].strip()

        # Extract leading SQL verb (case-insensitive)
        verb_match = cleaned.split()[0].upper() if cleaned else ''

        # Read-only verbs: no commit needed, fetch results
        if verb_match in (
            'SELECT', 'PRAGMA', 'EXPLAIN', 'WITH'
        ):
            inferred_commit, inferred_fetch = False, True
        # Write verbs: commit needed, no fetch
        elif verb_match in (
            'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP'
        ):
            inferred_commit, inferred_fetch = True, False
        # Defensive default: assume write operation
        else:
            inferred_commit, inferred_fetch = True, False

        return inferred_commit, inferred_fetch

    def _calculate_optimal_batch_size(
            self,
            dataframe: pd.DataFrame,
            max_batch_memory_mb: Optional[float] = None,
    ) -> int:
        """Calculate optimal batch size based on DataFrame memory footprint.

        Adapts batch size to avoid excessive memory usage while maintaining
        performance. Falls back to sensible default if calculation fails.

        Args:
            dataframe (pd.DataFrame): The data to be batched.
            max_batch_memory_mb (Optional[float]): Maximum memory per batch in MB.
                If None, uses Defaults.NumericalSettings.SQL_MAX_BATCH_MEMORY_MB.

        Returns:
            int: Optimal batch size (rows per batch).
        """
        if dataframe.empty:
            return Defaults.NumericalSettings.SQL_BATCH_SIZE

        if not max_batch_memory_mb:
            max_batch_memory_mb = Defaults.NumericalSettings.SQL_MAX_BATCH_MEMORY_MB

        # Estimate memory per row in bytes
        row_memory_bytes = dataframe.memory_usage(
            deep=True).sum() / len(dataframe)

        # Convert max memory MB to bytes
        max_batch_bytes = max_batch_memory_mb * 1024 * 1024

        # Calculate optimal batch size
        optimal_size = max(1, int(max_batch_bytes / row_memory_bytes))

        # Clamp to reasonable bounds [100, 10000]
        min_batch = Defaults.NumericalSettings.SQL_BATCH_SIZE_MIN
        max_batch = Defaults.NumericalSettings.SQL_BATCH_SIZE_MAX

        return max(min_batch, min(optimal_size, max_batch))

    def execute_query(
            self,
            query: str,
            params: tuple | List[tuple] = (),
            fetch: Optional[bool] = None,
            commit: Optional[bool] = None,
            batch_size: Optional[int] = None,
    ) -> Optional[List[Tuple]]:
        """Execute a specified SQL query using provided parameters.

        This method supports executing single or multiple SQL commands with
        optional parameterization, fetching results, and committing changes to
        the database. Query intent is automatically inferred from the SQL verb,
        so you typically do not need to specify commit/fetch explicitly.

        Explicit commit/fetch values override inferred defaults, allowing full
        control when needed.

        Handles and logs specific sqlite3 exceptions related to operation,
        integrity, database, and programming errors. Rolls back the transaction
        if an error occurs.

        Args:
            query (str): SQL query to be executed.
            params (tuple | List[tuple], optional): Parameters for the SQL query.
                Defaults to empty tuple.
            many (bool, optional): Whether to execute the query with multiple
                parameter sets. Defaults to False.
            fetch (Optional[bool], optional): Whether to fetch and return query
                results. If None, inferred from query verb. Defaults to None.
            commit (Optional[bool], optional): Whether to commit the transaction
                after query execution. If None, inferred from query verb.
                Defaults to None.
            batch_size (Optional[int], optional): Size of batches for executing
                multiple parameter sets. If None, uses default batch size from
                Defaults.NumericalSettings.SQL_BATCH_SIZE.

        Returns:
            Optional[List[Tuple]]: Results of the query if fetched; None otherwise.

        Raises:
            exc.OperationalError: If there is an operational issue during query
                execution.
            exc.IntegrityError: If there is an integrity issue during query execution.
            exc.MissingDataError: If there is a database issue during query execution.
        """
        if self.connection is None or self.cursor is None:
            msg = "Database connection or cursor not initialized."
            self.logger.error(msg)
            raise exc.OperationalError(msg)

        # Infer commit/fetch intent if not explicitly provided
        inferred_commit, inferred_fetch = self._infer_query_intent(query)
        final_commit = commit if commit is not None else inferred_commit
        final_fetch = fetch if fetch is not None else inferred_fetch

        # Infer if executing many parameter sets
        many = (
            isinstance(params, (list, tuple))
            and len(params) > 0
            and isinstance(params[0], (list, tuple))
        )

        if not batch_size:
            batch_size = Defaults.NumericalSettings.SQL_BATCH_SIZE

        try:
            if many and batch_size is not None:
                for i in range(0, len(params), batch_size):
                    batch_params = params[i:i + batch_size]
                    self.cursor.executemany(query, batch_params)
            elif many:
                self.cursor.executemany(query, params)
            else:
                self.cursor.execute(query, params)

            if final_commit:
                self.connection.commit()

            if final_fetch:
                return self.cursor.fetchall()

        except sqlite3.OperationalError as op_error:
            self.connection.rollback()
            msg = f"OperationalError (query: {query[:100]}...): {str(op_error)}"
            self.logger.error(msg)
            raise exc.OperationalError(msg) from op_error

        except sqlite3.IntegrityError as int_error:
            self.connection.rollback()
            msg = f"IntegrityError (query: {query[:100]}...): {str(int_error)}"
            self.logger.error(msg)
            raise exc.IntegrityError(msg) from int_error

        except sqlite3.DatabaseError as db_error:
            self.connection.rollback()
            msg = f"DatabaseError (query: {query[:100]}...): {str(db_error)}"
            self.logger.error(msg)
            raise exc.MissingDataError(msg) from db_error

    def check_table_exists(self, table_name: str) -> None:
        """Verifu the existence of a specified table within the SQLite database.

        This method checks against the list of existing tables and logs an error 
        if the specified table is not found.

        Args:
            table_name (str): Name of the table to check.

        Raises:
            exc.TableNotFoundError: If the specified table does not exist in the 
                database.
        """
        if table_name not in self.get_existing_tables_names:
            msg = f"SQLite table '{table_name}' NOT found."
            self.logger.error(msg)
            raise exc.TableNotFoundError(msg)

    def get_primary_column_name(self, table_name: str) -> str:
        """Determine the primary key column name for a specified table.

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
        table_info = self.execute_query(query)

        if table_info is None:
            raise exc.MissingDataError(
                f"SQLite table '{table_name}' | No schema information.")

        primary_key_columns = [
            column[1] for column in table_info if column[5] == 1
        ]

        if len(primary_key_columns) == 1:
            return primary_key_columns[0]
        elif len(primary_key_columns) == 0:
            raise ValueError(
                f"SQLite table '{table_name}' | No primary key column.")
        else:
            raise ValueError(
                f"SQLite table '{table_name}' | Multiple primary key "
                f"columns: {primary_key_columns}")

    def drop_table(self, table_name: str) -> None:
        """Delete a specified table from the SQLite database.

        Args:
            table_name (str): The name of the table to be dropped.
        """
        query = f"DROP TABLE {table_name}"
        self.execute_query(query)
        self.logger.debug(f"SQLite '{table_name}' - deleted.")

    def get_table_fields(self, table_name: str) -> Dict[str, str]:
        """Fetch and return the fields and types for a specified table.

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
        result = self.execute_query(query)

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
        """Create a new table in the SQLite database.

        This method creates a new table in the SQLite database with specified 
        name, fields and optional foreign keys.

        Args:
            table_name (str): The name of the table to create.
            table_fields (Dict[str, List[str]]): Dictionary of field names and
                types to define the table structure.
            foreign_keys (Optional[Dict[str, tuple]]): Dictionary specifying
                foreign key constraints. Default is None.
        """
        if table_name in self.get_existing_tables_names:
            self.logger.warning(f"SQLite table '{table_name}' already exists.")
            if not util.get_user_confirmation(
                f"Overwrite SQLite table '{table_name}'?"
            ):
                self.logger.info(
                    f"SQLlite table '{table_name}' NOT overwritten.")
                return

            self.drop_table(table_name)

        if foreign_keys:
            self.logger.debug(
                f"SQLite table generation with foreign keys | Table name: '{table_name}'")
        else:
            self.logger.debug(
                f"SQLite table generation | Table name: '{table_name}'")

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

    def switch_foreing_keys(self, switch: bool) -> None:
        """Enable/disable the enforcement of foreign key constraints.

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
    ) -> None:
        """Add a new column to an existing table in the SQLite database.

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
            OperationalError: If there is an error during the execution of the command.
        """
        try:
            query = f"""
                ALTER TABLE {table_name}
                ADD COLUMN "{column_name}" {column_type}
            """

            if default_value is not None:
                query += f" DEFAULT {default_value}"

            self.execute_query(query)

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
        result = self.execute_query(query)

        if result is None:
            return 0

        return result[0][0]

    def delete_table_column_data(
            self,
            table_name: str,
            force_operation: bool = False,
            column_name: Optional[str] = None,
    ) -> bool:
        """Delete values from a specified column in a table.

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
        """
        num_entries = self.count_table_data_entries(table_name)

        if num_entries > 0 and not force_operation:
            self.logger.warning(
                f"SQLite table '{table_name}' already has {num_entries} rows.")
            if not util.get_user_confirmation(
                f"Delete all {'entries' if column_name is None else f'entries in column {column_name}'} from {table_name}?"
            ):
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
        """Check DataFrame headers against a table schema.

        Validates that the headers of a DataFrame match the schema of a specified
        SQLite table, ignoring columns order. This method ensures that the DataFrame 
        columns align with the table's field names, optionally excluding the 
        primary key field from the validation.

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

        mismatched_headers = set(dataframe.columns) - set(table_fields)

        if mismatched_headers:
            msg = f"SQLite table '{table_name}' | headers mismatch with " \
                f"passed dataframe. Mismatched headers: '{mismatched_headers}'"
            self.logger.error(msg)
            raise ValueError(msg)

    def add_primary_keys_from_table(
            self,
            table_name: str,
            dataframe: pd.DataFrame,
    ) -> pd.DataFrame:
        """Add primary key values from a table to a DataFrame.

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
        values_field = Defaults.Labels.VALUES_FIELD['values'][0]
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
        action: Defaults.LiteralTypes.TableHandling = 'overwrite',
        other_coordinate_cols: Optional[List[str]] = None,
        force_overwrite: bool = False,
        suppress_warnings: bool = False,
        batch_size: Optional[int] = None,
        upstream_msg: Optional[str] = None,
    ) -> None:
        """Insert or update a SQLite table based on a DataFrame entries.

        This method inserts or updates entries in a specified SQLite table
        based on the contents of a provided pandas DataFrame. It checks for
        column consistency between the DataFrame and the table, and handles
        different actions such as 'update' or 'overwrite'. It also provides
        options to force overwrite existing data and suppress warning messages.

        This is a critical method in SQLite database handling. Modify it carefully.

        Args:
            table_name (str): The name of the SQLite table.
            dataframe (pd.DataFrame): The DataFrame to be inserted into the 
                table.
            action (Defaults.LiteralTypes.TableHandling, optional): The action to
                perform: 'update' to modify existing entries, 'overwrite' to
                replace all entries. Defaults to 'overwrite'.
            other_coordinate_cols (Optional[List[str]], optional): Columns to
                exclude from structural coordinate matching when
                `action='update' other than the ID and values
                fields.
            force_overwrite (bool, optional): If True, existing table entries 
                will be overwritten without asking user permission. Defaults to 
                False.
            suppress_warnings (bool, optional): If True, suppresses warning 
                messages. Defaults to False.
            batch_size (Optional[int], optional): The number of entries to
                process in each batch during query execution. If None, an
                optimal batch size is calculated based on the DataFrame size.
            upstream_msg (Optional[str], optional): An optional message to
                prepend to log entries for context.

        Raises:
            exc.MissingDataError: If there is a mismatch in columns between
                the DataFrame and the table.
            exc.OperationalError: If there is an error during query execution
                or if there is a length mismatch when updating entries.
            exc.SettingsError: If an invalid action is specified.
        """
        self.check_table_exists(table_name)

        if dataframe.empty:
            msg = "Passed DataFrame is empty. No data inserted into table."
            self.logger.warning(msg)
            return

        dataframe = dataframe.copy(deep=True)

        id_field = Defaults.Labels.ID_FIELD['id'][0]
        values_field = Defaults.Labels.VALUES_FIELD['values'][0]
        lb_field = Defaults.UncertaintySettings.LOWER_BOUND_FIELD[
            Defaults.UncertaintySettings.LOWER_BOUND_KEY
        ][0]
        ub_field = Defaults.UncertaintySettings.UPPER_BOUND_FIELD[
            Defaults.UncertaintySettings.UPPER_BOUND_KEY
        ][0]
        is_uncertain_field = Defaults.UncertaintySettings.IS_UNCERTAIN_FIELD[
            Defaults.UncertaintySettings.IS_UNCERTAIN_KEY
        ][0]
        group_name_field = (
            Defaults.UncertaintySettings.UNCERTAINTY_GROUP_NAME_FIELD[
                Defaults.UncertaintySettings.UNCERTAINTY_GROUP_NAME_KEY
            ][0]
        )
        table_existing_entries = self.count_table_data_entries(table_name)
        df_existing = self.table_to_dataframe(table_name)

        # check if dataframes columns are matching (except id_field)
        if not util.check_dataframe_columns_equality(
            df_list=[dataframe, df_existing],
            skip_columns=[id_field],
        ):
            c_passed = [col for col in dataframe.columns if col != id_field]
            c_existing = [
                col for col in df_existing.columns if col != id_field]

            msg = \
                f"SQLite table '{table_name}' | " \
                f"action '{action}' | " \
                f"columns mismatch (passed: {c_passed}, existing: {c_existing})"
            self.logger.error(msg)
            raise exc.MissingDataError(msg)

        # check if table is already up to date
        if id_field in dataframe.columns or id_field in df_existing.columns:
            skip_columns = [id_field]
        else:
            skip_columns = []

        if util.check_dataframes_equality(
            df_list=[df_existing, dataframe],
            skip_columns=skip_columns,
        ):
            if not suppress_warnings:
                self.logger.warning(
                    f"SQLite table '{table_name}' | "
                    f"action '{action}' | "
                    f"data already up to date."
                )
            return

        # case of no entries in existing table or case of 'overwrite' action
        if table_existing_entries == 0 or action == 'overwrite':

            if table_existing_entries > 0:
                if not self.delete_table_column_data(
                    table_name,
                    force_overwrite
                ):
                    self.logger.debug(
                        f"SQLite table '{table_name}' | "
                        f"action '{action}' | "
                        f"original data NOT erased."
                    )
                    return

            if id_field not in dataframe.columns:
                dataframe = util.add_column_to_dataframe(
                    dataframe=dataframe,
                    column_header=id_field,
                    column_values=range(len(dataframe)),
                    column_position=0,
                )

            data = [tuple(row) for row in dataframe.values.tolist()]
            placeholders = ', '.join(['?'] * len(dataframe.columns))
            query = f"""
                INSERT INTO {table_name} ({', '.join(
                    f'"{col}"' for col in dataframe.columns
                )}) 
                VALUES ({placeholders})
            """

        # case where all or a part of data entries need to be replaced
        elif table_existing_entries > 0 or action == 'update':

            non_coordinate_cols = [
                id_field, values_field]

            if self.is_uncertainty_enabled:
                non_coordinate_cols.extend(
                    [ub_field, lb_field, is_uncertain_field, group_name_field])

            if other_coordinate_cols:
                non_coordinate_cols.extend(other_coordinate_cols)

            # case of passed dataframe has more entry then existing table
            if len(dataframe) > len(df_existing):
                msg = \
                    f"SQLite table '{table_name}' | " \
                    f"action '{action}' | " \
                    f"length mismatch (existing table: {len(df_existing)}, " \
                    f"passed data: {len(dataframe)})"
                self.logger.error(msg)
                raise exc.OperationalError(msg)

            non_coordinate_cols = [
                col for col in non_coordinate_cols
                if col in df_existing.columns
            ]

            coordinates_cols = [
                col for col in df_existing.columns
                if col not in non_coordinate_cols
            ]

            # merge dataframes to get a resulting dataframe with updated values
            # from dataframe and id from dataframe_existing
            if id_field in dataframe.columns:
                dataframe = dataframe.drop(columns=id_field)

            dataframe_with_id = dataframe.merge(
                df_existing[[id_field, *coordinates_cols]],
                on=coordinates_cols,
                how='left',
            )

            # reorder columns to match table schema
            if not all(dataframe_with_id.columns == df_existing.columns):
                dataframe_with_id = dataframe_with_id[df_existing.columns]

            # auto-calculate batch_size in query execution
            if batch_size is None:
                batch_size = self._calculate_optimal_batch_size(
                    dataframe_with_id)

            data = [tuple(row) for row in dataframe_with_id.values.tolist()]
            placeholders = ', '.join(['?'] * len(dataframe_with_id.columns))
            query = f"""
                INSERT OR REPLACE INTO {table_name} 
                VALUES ({placeholders})
            """

        else:
            msg = f"Action '{action}' not allowed. Available actions: "\
                "'update', 'overwrite'."
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        self.execute_query(query=query, params=data, batch_size=batch_size)

        msg = (
            f"SQLite table '{table_name}' | "
            f"action '{action}' | "
            f"entries: {len(data)} "
        )
        if upstream_msg:
            msg += upstream_msg

        self.logger.debug(msg)

    def table_to_dataframe(
            self,
            table_name: str,
            filters_dict: Optional[Dict[str, List[str]]] = None,
    ) -> pd.DataFrame:
        """Filter and return a SQLite table as a pandas DataFrame.

        This method constructs a SQL query using the provided filter conditions
        and retrieves the matching records. 
        If no filters are provided, the entire table is returned.
        If no records match the filters, an empty DataFrame is returned.
        If NaN values are present in the table, they are replaced with None
        in the resulting DataFrame.

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
                [
                    f"{key} IN ({', '.join(['?']*len(values))})"
                    for key, values in filters_dict.items()
                ]
            )

            flattened_values = [
                str(value) for values in filters_dict.values()
                for value in values
            ]

            query = f"SELECT * FROM {table_name} WHERE {conditions};"

        table = self.execute_query(
            query=query,
            params=tuple(flattened_values),
        )

        dataframe = pd.DataFrame(data=table, columns=table_columns_labels)

        # replace NaN with None
        dataframe = dataframe.where(pd.notna(dataframe), None)

        if filters_dict and dataframe.empty:
            self.logger.warning(
                f"Filtered table from '{table_name}' is empty.")

        return dataframe

    def get_null_values(
            self,
            table_name: str,
            column_to_inspect: str,
            column_with_info: str,
    ) -> List:
        """Find rows with NULL values in a specified column.

        This method retrieves rows with NULL values in a specified column and 
        returns a list of corresponding items in another column of the same table.

        Args:
            table_name (str): The name of the table to inspect.
            column_to_inspect (str): The column to check for NULL values.
            column_with_info (str): The column whose values will be used as keys 
                in the result.

        Returns:
            List: A list with values from 'column_with_info'

        Raises:
            exc.OperationalError: If the specified columns do not exist in the table.

        """
        self.check_table_exists(table_name)
        table_fields = self.get_table_fields(table_name)

        if column_to_inspect not in table_fields['labels']:
            msg = f"Column '{column_to_inspect}' not found in table '{table_name}'."
            self.logger.error(msg)
            raise exc.OperationalError(msg)

        if column_with_info not in table_fields['labels']:
            msg = f"Column '{column_with_info}' not found in table '{table_name}'."
            self.logger.error(msg)
            raise exc.OperationalError(msg)

        query = f"""
            SELECT "{column_with_info}"
            FROM {table_name}
            WHERE "{column_to_inspect}" IS NULL
        """
        rows = self.execute_query(query)

        if rows is None:
            return []

        return [row[0] for row in rows]

    def get_related_table_keys(
            self,
            child_column_name: str,
            parent_table_name: str,
            parent_table_fields: Dict[str, List[str]],
    ) -> Dict[str, List[str]]:
        """Get related keys from a child table based on parent table filters.

        This method retrieves keys from a child table that correspond to filtering 
        criteria specified in a parent table.
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
            exc.OperationalError: If there is an error during query execution.
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
        """Compare two SQLite databases to check their equality.

        This method compares the current database with another SQLite database 
        to check if they are identical. This method is used to for testing purposes.

        This method checks for the following:

        - Existence of tables in the source database.
        - Structure of the tables (schema).
        - Contents of the tables (coordinates).
        - Numerical values in the 'values' column with a specified tolerance.

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
            exc.OperationalError: If the connection or cursor of the database to be
                checked are not initialized.
            exc.ModelFolderError: If the other database does not exist or is not correctly named.
            exc.ResultsError: If the databases are not identical in terms of table
                presence, structure, or contents.
            exc.SettingsError: If tolerance_percentage is not provided when 
                check_values is True.
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
            values_header = Defaults.Labels.VALUES_FIELD['values'][0]

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

                rounding_digits = \
                    Defaults.NumericalSettings.ROUNDING_DIGITS_RELATIVE_DIFFERENCE_DB

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

    def get_tables_values_scale(
        self,
        norm_type: Defaults.LiteralTypes.NormType,
        tables_names: Optional[List[str]] = None,
    ) -> Dict[str, float]:
        """Get norm of values in specified tables of the current SQLite database.

        This method computes the norm (scale) of numerical values in specified 
        tables. This is useful for understanding the magnitude of data in tables
        and for scaling/normalization purposes during integrated solving.

        Args:
            norm_type (Defaults.LiteralTypes.NormType): 
                The type of norm to use for calculating the scale of values.
            tables_names (Optional[List[str]], optional): Specific tables to
                analyze; if None, all tables are analyzed.

        Returns:
            Dict[str, float]: A dictionary where keys are table names and values 
                are the computed norms.

        Raises:
            exc.OperationalError: If the connection or cursor is not initialized.
            exc.TableNotFoundError: If specified tables are not found in the database.
        """
        if self.connection is None or self.cursor is None:
            msg = "Connection or cursor of the database are not initialized."
            self.logger.error(msg)
            raise exc.OperationalError(msg)

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

        scales: Dict[str, float] = {}

        try:
            for table in tables_names:
                self.cursor.execute(f"SELECT \"values\" FROM \"{table}\"")
                table_values = [row[0] for row in self.cursor.fetchall()]

                scales[table] = util.calculate_change_norm(
                    seq1=table_values,
                    seq2=None,
                    metric=norm_type,
                    ignore_nan=True,
                )

            return scales

        except sqlite3.Error as error:
            msg = f"Error retrieving table scales: {error}"
            self.logger.error(msg)
            raise exc.OperationalError(msg) from error

    def get_tables_values_norm_changes(
            self,
            other_db_dir_path: Path | str,
            other_db_name: str,
            norm_type: Defaults.LiteralTypes.NormType,
            tables_names: Optional[List[str]] = None,
    ) -> Dict[str, float]:
        """Get data tables norm changes between two SQLite databases.

        This method compares the values in specified tables of two SQLite databases 
        and returns the norm changes for each table. 
        This method is used to check the convergence of subsequent iterations in 
        running the alternate optimization algorithm to solve integrated models.
        The norm type can be specified to calculate the differences.

        Args:
            other_db_dir_path (Path | str): The directory path of the other
                SQLite database.
            other_db_name (str): The name of the other SQLite database.
            tables_names (Optional[List[str]], optional): Specific tables to
                compare; if None, all tables are compared.
            norm_type (Defaults.LiteralTypes.NormType, 
                optional): The type of norm to use for calculating differences.

        Returns:
            Dict[str, float]: A dictionary where the keys are the table names
                and the values are the related maximum relative differences.

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

        try:
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

            changes: Dict[str, float] = {}

            for table in tables_names:
                self.cursor.execute(f"SELECT \"values\" FROM \"{table}\"")
                current_values = [row[0] for row in self.cursor.fetchall()]

                other_db_cursor.execute(f"SELECT \"values\" FROM \"{table}\"")
                other_values = [row[0] for row in other_db_cursor.fetchall()]

                changes[table] = util.calculate_change_norm(
                    seq1=current_values,
                    seq2=other_values,
                    metric=norm_type,
                    ignore_nan=True,
                )

            return changes

        finally:
            other_db_connection.close()

    def __repr__(self):
        """Return a string representation of the SQLManager instance."""
        class_name = type(self).__name__
        return f'{class_name}'


@contextlib.contextmanager
def db_handler(sql_manager: SQLManager):
    """Context manager for database connection and cursor.

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
