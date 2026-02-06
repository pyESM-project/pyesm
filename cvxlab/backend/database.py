"""Module defining the Database class.

The Database class handles all interactions with the database and file management 
for a modeling application. It includes functionalities for creating and 
manipulating database tables, handling data input/output operations, and managing 
data files for a modeling system.
The Database class encapsulates methods for creating blank database tables,
loading data from Excel files, generating data input files, and managing the
SQLite database interactions via the SQLManager.
"""
from pathlib import Path
from typing import Dict, List, Literal, Optional

import pandas as pd

from cvxlab.backend.data_table import DataTable
from cvxlab.backend.index import Index
from cvxlab.backend.set_table import SetTable
from cvxlab.backend.variable import Variable
from cvxlab.defaults import Defaults
from cvxlab.log_exc import exceptions as exc
from cvxlab.log_exc.logger import Logger
from cvxlab.support import util
from cvxlab.support.file_manager import FileManager
from cvxlab.support.sql_manager import SQLManager, db_handler


class Database:
    """Database class manages database operations for the modeling application.

    The Database class is responsible for handling all interactions with the
    database and file management for the modeling application. It provides methods
    for creating and manipulating database tables, handling data input/output
    operations, and managing data files.
    The class utilizes instances of Logger, FileManager, SQLManager, and Index to
    perform its operations.

    Attributes:

    - logger (Logger): Logger object for logging information, warnings, and errors.
    - files (FileManager): Manages file-related operations with files.
    - sqltools (SQLManager): Manages SQL database interactions.
    - index (Index): Central index for managing set tables and data tables.
    - paths (Dict): Dictionary mapping of paths used in file operations.
    - settings (Dict): Configuration settings for the application.

    """

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            sqltools: SQLManager,
            index: Index,
            paths: Dict,
            settings: Dict,
    ):
        """Initialize a new instance of the Database class.

        This constructor initializes the Database with a logger, file manager,
        SQL manager, index, paths, and settings. It sets up the necessary attributes
        for managing database operations and file handling.
        In case 'use_existing_data' is False (i.e. when the model instance is created
        for the first time), a blank sets Excel file is created for defining sets 
        when initializing the Database instance.

        Args:
            logger (Logger): Logger object for logging operations.
            files (FileManager): FileManager object for managing file operations.
            sqltools (SQLManager): SQLManager object for managing SQLite database.
            index (Index): Index object for getting information about model structure
                (data tables, variables).
            paths (Dict): Dictionary mapping of paths used in file operations.
            settings (Dict): A dictionary containing configuration settings.
        """
        self.logger = logger.get_child(__name__)

        self.files = files
        self.sqltools = sqltools
        self.index = index
        self.settings = settings
        self.paths = paths

        if not self.settings['use_existing_data']:
            self.create_blank_sets_xlsx_file()

    def create_blank_sets_xlsx_file(self) -> None:
        """Create a blank Excel file for getting sets information.

        This method first checks if the sets Excel file specified in the settings 
        exists. In case it does, the method checks the 'use_existing_data' setting
        to determine whether to erase the existing file or use it as is. If it does and
        'use_existing_data' is False, the method erases the existing file. If
        'use_existing_data' is True or the file does not exist, the method creates
        a new blank Excel file with headers for each set, based on information 
        provided by Index.
        Sets that are defined as copies of other sets (i.e., have a 'copy_from'
        attribute) are not included in the new Excel file.
        """
        sets_file_name = Defaults.ConfigFiles.SETS_FILE

        if Path(self.paths['sets_excel_file']).exists():
            if not self.settings['use_existing_data']:
                erased = self.files.erase_file(
                    dir_path=self.paths['model_dir'],
                    file_name=sets_file_name,
                    force_erase=False,
                    confirm=True,
                )

                if erased:
                    self.logger.info(
                        f"Sets excel file '{sets_file_name}' erased and "
                        "overwritten.")
                else:
                    self.logger.info(
                        f"Relying on existing sets excel file '{sets_file_name}'.")
                    return
            else:
                self.logger.info(
                    f"Relying on existing sets excel file '{sets_file_name}'.")
                return
        else:
            self.logger.info(
                f"Generating new sets excel file '{sets_file_name}'.")

        dict_headers = {
            set_value.table_name: set_value.set_excel_file_headers
            for set_value in self.index.sets.values()
            if getattr(set_value, 'copy_from', None) is None
        }

        self.files.dict_to_excel_headers(
            dict_name=dict_headers,
            excel_dir_path=self.paths['model_dir'],
            excel_file_name=sets_file_name,
        )

    def create_blank_sqlite_database(self) -> None:
        """Create a blank SQLite database.

        This method creates a blank SQLite database with table structures defined 
        in the Index class and with specifications defined by Settings. 
        It then iterates over each set in the index, validates that it is an 
        instance of SetTable, and creates a new table in the database for the set. 
        The table's headers are determined based on the 'table_headers' attribute 
        of the set. In case ID header of the talble is not included in the
        'table_headers' attribute, it is added.

        Raises:
            MissingDataError: If the 'table_headers' attribute of a set is not defined.

        Notes:
            The method logs information about the creation of the database and
                each table.
            If the 'table_headers' attribute of a set does not include the
                standard ID field, the method adds it.
        """
        self.logger.debug(
            f"Generating database '{self.settings['sqlite_database_file']}'.")

        with db_handler(self.sqltools):
            for set_instance in self.index.sets.values():
                set_instance: SetTable

                set_name = set_instance.name
                table_name = set_instance.table_name
                table_headers = set_instance.table_headers
                table_id_header = Defaults.Labels.ID_FIELD['id']

                if table_headers is not None:
                    if table_id_header not in table_headers.values():
                        table_headers = {
                            **Defaults.Labels.ID_FIELD, **table_headers}

                    self.sqltools.create_table(table_name, table_headers)

                else:
                    msg = f"Table fields for set '{set_name}' are not defined."
                    self.logger.error(msg)
                    raise exc.MissingDataError(msg)

    def load_sets_to_sqlite_database(self) -> None:
        """Load sets data into the SQLite database.

        This method parse each set table in the Index, check the presence of the
        data attribute, copy the dataframe in the data attribute and then send the
        dataframe into the related SQLite set table.

        Raises:
            MissingDataError: If the 'data' attribute of a set is None, indicating
                incomplete setup.
        """
        self.logger.debug(
            f"Loading Sets to '{self.settings['sqlite_database_file']}'.")

        with db_handler(self.sqltools):
            for set_instance in self.index.sets.values():
                set_instance: SetTable

                if set_instance.data is not None:
                    table_name = set_instance.table_name
                    dataframe = set_instance.data.copy()
                    table_headers = set_instance.table_headers
                    table_id_header = Defaults.Labels.ID_FIELD['id']
                else:
                    msg = f"Data of set '{set_instance.name}' are not defined."
                    self.logger.error(msg)
                    raise exc.MissingDataError(msg)

                if table_headers is not None:
                    if table_id_header not in table_headers.values():
                        dataframe = util.add_column_to_dataframe(
                            dataframe=dataframe,
                            column_header=table_id_header[0],
                            column_values=None,
                            column_position=0,
                        )

                self.sqltools.dataframe_to_table(table_name, dataframe)

    def update_sets_in_sqlite_database(
            self,
            set_keys_list: List[str] = [],
            update_mode: Literal['all', 'filters', 'aggregations'] = 'all',
    ) -> None:
        """Update sets data in the SQLite database.

        This method updates the data of specified sets in the SQLite database.
        It iterates over each set in the Index, and if the set's key is in the
        provided 'set_keys_list' (or if the list is empty, indicating all sets),
        it updates the corresponding table in the database with the data from
        the set's 'data' attribute.

        Args:
            set_keys_list(List[str], optional): A list of set keys to update.
                If empty, all sets in the Index are updated. Defaults to [].
            update_mode(Literal['all', 'filters', 'aggregations'], optional):
                Specifies the update mode. Defaults to 'all'.

        Raises:
            MissingDataError: If the 'data' attribute of a set is None, indicating
                incomplete setup.
        """
        self.logger.debug(
            f"Updating Sets in '{self.settings['sqlite_database_file']}'.")

        id_header = Defaults.Labels.ID_FIELD['id'][0]

        with db_handler(self.sqltools):
            for set_key, set_instance in self.index.sets.items():
                set_instance: SetTable

                if set_keys_list != [] and set_key not in set_keys_list:
                    continue

                if set_instance.data is None:
                    msg = f"Set table '{set_instance.name}' | Data not found."
                    self.logger.error(msg)
                    raise exc.MissingDataError(msg)

                dataframe_new = set_instance.data.copy()
                dataframe_current = self.sqltools.table_to_dataframe(
                    table_name=set_instance.table_name,
                )

                if update_mode == 'all':
                    columns_to_update = [
                        col for col in dataframe_new.columns
                        if col != id_header
                    ]
                else:
                    if update_mode == 'filters':
                        headers_dict = set_instance.set_filters_headers
                    elif update_mode == 'aggregations':
                        headers_dict = set_instance.set_aggregations_headers

                    if not headers_dict:
                        self.logger.warning(
                            f"Set table '{set_instance.name}' | "
                            f"No '{update_mode}' headers defined. Skipping update."
                        )
                        continue

                    columns_to_update = list(headers_dict.values())

                # check equality of dataframes columns
                if util.check_dataframes_equality(
                    df_list=[dataframe_current, dataframe_new],
                    check_columns=columns_to_update,
                ):
                    self.logger.info(
                        f"Set table '{set_instance.name}' | "
                        "No changes detected. Skipping update."
                    )
                    continue

                # built final dataframe preserving id
                dataframe_final = dataframe_current[[id_header]].copy()

                for column in columns_to_update:
                    if column in dataframe_new.columns:
                        dataframe_final[column] = dataframe_new[column]
                    else:
                        self.logger.warning(
                            f"Column '{column}' not found in new data for set "
                            f"'{set_instance.name}'. Skipping this column."
                        )

                new_columns = set(dataframe_final.columns) - set(
                    dataframe_current.columns)
                if new_columns:
                    self.logger.debug(
                        f"Set table '{set_instance.name}' | "
                        f"Adding new columns: {new_columns}."
                    )
                    for column in new_columns:
                        self.sqltools.add_table_column(
                            table_name=set_instance.table_name,
                            column_name=column,
                            column_type=Defaults.Labels.GENERIC_FIELD_TYPE,
                        )

                self.sqltools.dataframe_to_table(
                    table_name=set_instance.table_name,
                    dataframe=dataframe_final,
                    action='overwrite',
                    force_overwrite=True,
                )

    def generate_blank_sqlite_data_tables(self) -> None:
        """Generate empty data tables in the SQLite database.

        This method iterates over each data table in the Index and create empty
        data tables in the SQLite database for endogenous and exogenous variables.
        Constant tables are skipped as they do not require a separate table in
        the database.
        New tables are created with headers and foreign keys defined in the
        'table_headers' and 'foreign_keys' attributes of each data table.
        """
        self.logger.debug(
            "Generation of empty data tables in "
            f"'{Defaults.ConfigFiles.SQLITE_DATABASE_FILE}'.")

        allowed_var_types = Defaults.SymbolicDefinitions.VARIABLE_TYPES

        with db_handler(self.sqltools):
            for table_key, table in self.index.data.items():
                table: DataTable

                if table.type == allowed_var_types['CONSTANT']:
                    continue

                self.sqltools.create_table(
                    table_name=table_key,
                    table_fields=table.table_headers,
                    foreign_keys=table.foreign_keys,
                )

    def sets_data_to_sql_data_tables(self) -> None:
        """Add sets information to data tables in SQLite database.

        This method parses each data table in the Index. Then, it unpivots the 
        values of the related sets coordinates into a DataFrame, and filters the 
        DataFrame to keep only coordinates defined by the variables within the
        data table (i.e. the method drops the combination of set values that will
        not correspond to any numerical value in variables, for the purpose of 
        making the data table lighter). 
        Finally, it adds an ID column to the DataFrame and loads the dataframe 
        into the corresponding data table in the SQLite database. It finally adds
        a 'values' column to the data table to store numerical values.

        Raises:
            OperationalError: Is raised if the procedure is not filtering
                the dataframe correctly.
        """
        self.logger.debug(
            "Adding sets information to SQLite data tables in "
            f"{Defaults.ConfigFiles.SQLITE_DATABASE_FILE}."
        )

        allowed_var_types = Defaults.SymbolicDefinitions.VARIABLE_TYPES

        with db_handler(self.sqltools):
            for table_key, table in self.index.data.items():
                table: DataTable

                if table.type == allowed_var_types['CONSTANT']:
                    continue

                table_headers_list = [
                    value for value in table.coordinates_headers.values()
                ]

                unpivoted_coords_df = util.unpivot_dict_to_dataframe(
                    data_dict=table.coordinates_values,
                    key_order=table_headers_list
                )

                # data table coordinates dataframe are filtered to keep only
                # coordinates defined by the variables whithin the data table
                dicts_list = []
                for variable in self.index.variables.values():
                    variable: Variable
                    if variable.related_table == table_key:
                        dicts_list.append(
                            variable.all_coordinates_w_headers
                        )

                coords_to_keep_df = pd.DataFrame()
                for item in dicts_list:
                    coords_df = util.unpivot_dict_to_dataframe(
                        data_dict=item,
                        key_order=table_headers_list
                    )
                    coords_to_keep_df = pd.concat(
                        [coords_to_keep_df, coords_df],
                        ignore_index=True
                    )

                coords_to_keep_df = coords_to_keep_df.drop_duplicates()

                unpivoted_coords_df = unpivoted_coords_df.merge(
                    coords_to_keep_df,
                    on=table_headers_list,
                    how='inner'
                )

                if not util.check_dataframes_equality(
                    df_list=[coords_to_keep_df, unpivoted_coords_df]
                ):
                    msg = "Dataframes are not equal after merge operation."
                    self.logger.error(msg)
                    raise exc.OperationalError(msg)

                unpivoted_coords_df = util.add_column_to_dataframe(
                    dataframe=unpivoted_coords_df,
                    column_header=table.table_headers['id'][0],
                    column_values=None,
                    column_position=0,
                )

                self.sqltools.dataframe_to_table(
                    table_name=table_key,
                    dataframe=unpivoted_coords_df,
                )

                self.sqltools.add_table_column(
                    table_name=table_key,
                    column_name=Defaults.Labels.VALUES_FIELD['values'][0],
                    column_type=Defaults.Labels.VALUES_FIELD['values'][1],
                )

    def clear_database_tables(
        self,
        table_names: Optional[List[str] | str] = None,
    ) -> None:
        """Clear specified tables or all tables from the SQLite database.

        This method parse all or a list 'table_names' of the data tables in the
        Index and delete the tables from the SQLite database.

        Args:
            table_names (Optional[List[str] | str]): A list of table names or a
                single table name to clear. If None, all tables in the database
                will be cleared.
        """
        with db_handler(self.sqltools):
            existing_tables = self.sqltools.get_existing_tables_names

            if not table_names:
                tables_to_clear = existing_tables
                self.logger.info(
                    "Clearing all tables from SQLite database "
                    f"{Defaults.ConfigFiles.SQLITE_DATABASE_FILE}"
                )

            else:
                tables_to_clear = list(table_names)
                self.logger.info(
                    f"Clearing tables '{tables_to_clear}' from SQLite database "
                    f"{Defaults.ConfigFiles.SQLITE_DATABASE_FILE}"
                )

            for table_name in tables_to_clear:
                if table_name in self.index.data.keys():
                    self.sqltools.drop_table(table_name)

    def generate_blank_data_input_files(
        self,
        file_extension: Optional[str] = None,
        table_key_list: List[str] = [],
        values_cleanup: bool = True,
    ) -> None:
        """Generate blank data input files for exogenous data tables.

        This method generates blank excel data input file/s for exogenous data 
        tables, to be filled by the user.
        This method iterates over each data table in the Index, or in a list provided
        by the 'table_key_list' argument. If the table's type is 'exogenous', it exports
        the table's data from the SQLite database to an Excel file. 
        If 'multiple_input_files' setting is True, a separate file is created for each
        table. Otherwise, all tables are exported to a single file as separate tabs.

        Args:
            file_extension (Optional[str]): The format of the input data files. 
                Defaults to None. If None, file type is taken from settings.
            table_key_list (List[str], optional): A list of table keys to generate
                input files for. If empty, all exogenous data tables in the Index
                are processed. Defaults to an empty list.
            values_cleanup (bool, optional): Whether to clean up values in the
                input data files. Defaults to True.
        """
        default_file_name = Defaults.ConfigFiles.INPUT_DATA_FILE_NAME
        allowed_var_types = Defaults.SymbolicDefinitions.VARIABLE_TYPES
        value_field = Defaults.Labels.VALUES_FIELD['values'][0]

        if file_extension is None:
            file_extension = self.settings['input_data_files_type']
        else:
            util.validate_selection(
                selection=file_extension,
                valid_options=Defaults.ConfigFiles.AVAILABLE_DATA_FILES_EXTENSIONS,
            )

        if not Path(self.paths['input_data_dir']).exists():
            self.files.create_dir(self.paths['input_data_dir'])

        if not self.settings['multiple_input_files'] and file_extension == 'csv':
            msg = "'csv' data file format is only allowed for multiple input files."
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        with db_handler(self.sqltools):
            for table_key, table in self.index.data.items():
                table: DataTable

                if table_key_list != [] and table_key not in table_key_list:
                    continue

                if table.type in [
                    allowed_var_types['ENDOGENOUS'],
                    allowed_var_types['CONSTANT']
                ]:
                    continue

                if self.settings['multiple_input_files']:
                    output_file_name = f"{table_key}.{file_extension}"
                    force_overwrite = False
                else:
                    output_file_name = f"{default_file_name}.{file_extension}"
                    force_overwrite = True

                dataframe = self.sqltools.table_to_dataframe(table_key)

                if values_cleanup:
                    if value_field in dataframe.columns:
                        dataframe[value_field] = None

                if file_extension == 'xlsx':
                    self.files.dataframe_to_excel(
                        dataframe=dataframe,
                        excel_filename=output_file_name,
                        excel_dir_path=self.paths['input_data_dir'],
                        sheet_name=table_key,
                        force_overwrite=force_overwrite,
                    )
                elif file_extension == 'csv':
                    self.files.dataframe_to_csv(
                        dataframe=dataframe,
                        csv_filename=output_file_name,
                        csv_dir_path=self.paths['input_data_dir'],
                    )
                else:
                    msg = f"File extension '{file_extension}' not supported."
                    self.logger.error(msg)
                    raise exc.SettingsError(msg)

    def load_data_input_files_to_database(
        self,
        table_key_list: list[str] = [],
        force_overwrite: bool = False,
    ) -> None:
        """Load input files data into the SQLite database.

        This method parses all or a list 'table_key_list' of the exogenous data 
        tables in the Index. It collects data from Excel file/s and updates the 
        related SQLite data tables.

        Args:
            table_key_list (list[str], optional): A list of table keys to load
                data for. If empty, all exogenous data tables in the Index are
                processed. Defaults to an empty list.
            force_overwrite (bool, optional): If True, forces the overwrite of
                existing data. Defaults to False.

        Raises:
            ValueError: If one or more passed table keys are not present in the Index.
        """
        self.logger.debug(
            "Loading data from input file/s filled by the user "
            "to SQLite database.")

        file_extension = self.settings['input_data_files_type']
        multiple_data_file = self.settings['multiple_input_files']

        if table_key_list == []:
            table_key_list = self.index.data.keys()
        else:
            if not util.items_in_list(
                items=table_key_list,
                control_list=self.index.data.keys()
            ):
                msg = "One or more passed tables keys not present in the index."
                self.logger.error(msg)
                raise ValueError(msg)

        if not multiple_data_file and file_extension != 'xlsx':
            msg = "Single data file is only allowed in 'xlsx' format."
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        # case 1: load from a single excel file with multiple tabs
        # data are all loaded into a dataframe, then commited to the database
        if not self.settings['multiple_input_files']:
            file_name = Defaults.ConfigFiles.INPUT_DATA_FILE_NAME

            data_dict = self.files.excel_to_dataframes_dict(
                excel_file_dir_path=self.paths['input_data_dir'],
                excel_file_name=f"{file_name}.{file_extension}",
            )

            with db_handler(self.sqltools):
                for table_key, dataframe in data_dict.items():
                    if table_key not in table_key_list:
                        continue

                    dataframe = util.normalize_dataframe(df=dataframe)
                    self.sqltools.dataframe_to_table(
                        table_name=table_key,
                        dataframe=dataframe,
                        force_overwrite=force_overwrite,
                        action='update',
                    )

        # case 2: load from multiple files
        # each data table is loaded from a separate file and committed to the database
        else:
            data_dict = {}

            with db_handler(self.sqltools):
                for table_key, table in self.index.data.items():
                    table: DataTable

                    if table_key not in table_key_list:
                        continue

                    if table.type not in [
                        Defaults.SymbolicDefinitions.VARIABLE_TYPES['ENDOGENOUS'],
                        Defaults.SymbolicDefinitions.VARIABLE_TYPES['CONSTANT']
                    ]:
                        file_name = f"{table_key}.{file_extension}"

                        data_dict[table_key] = self.files.file_to_dataframe(
                            file_name=file_name,
                            file_dir_path=self.paths['input_data_dir'],
                        )

                        dataframe = util.normalize_dataframe(
                            df=data_dict[table_key])

                        self.sqltools.dataframe_to_table(
                            table_name=table_key,
                            dataframe=dataframe,
                            force_overwrite=force_overwrite,
                            action='update',
                        )

    def fill_nan_values_in_database(
            self,
            force_overwrite: bool = False,
            table_key_list: List[str] = [],
    ) -> None:
        """Complete value fields in data tables in the database.

        This method is designed to fill NaN values in the SQLite database after
        loading data from user-filled input files.
        Specifically, the method iterates over variables defined in the Index and 
        fill NaN values in the related data tables (in value field) based on the 
        'blank_fill' attribute of each variable. 
        This feature is intended to facilitate the definition of data in the input 
        files, allowing users to leave certain values blank and have them
        automatically filled based on rules defined in the Index.

        Args:
            force_overwrite (bool, optional): If True, forces the overwrite of
                existing data. Defaults to False.
            table_key_list (List[str], optional): List of table keys to process.
                If empty, all tables in the index are processed. Defaults to [].

        Raises:
            ValueError: If one or more passed table keys are not present in the Index.
        """
        self.logger.debug(
            "Filling blank data in SQLite data tables based on the 'blank_fill' "
            "attribute of each variable.")

        blank_fill_key = Defaults.Labels.BLANK_FILL_KEY
        value_header = Defaults.Labels.VALUES_FIELD['values'][0]

        if table_key_list == []:
            table_key_list = self.index.data.keys()
        else:
            if not util.items_in_list(
                table_key_list,
                self.index.data.keys()
            ):
                msg = "One or more passed tables keys not present in the Index."
                self.logger.error(msg)
                raise ValueError(msg)

        with db_handler(self.sqltools):

            for var_key, variable in self.index.variables.items():
                variable: Variable

                blank_fill_value = variable.var_info.get(blank_fill_key, None)
                related_table = variable.related_table

                if related_table not in table_key_list:
                    continue

                if blank_fill_value is None:
                    continue

                df_query = self.sqltools.table_to_dataframe(
                    table_name=related_table,
                    filters_dict=variable.all_coordinates_w_headers,
                )

                df_query_nan = df_query[df_query[value_header].isna()]

                if df_query_nan.empty:
                    continue

                df_query_nan.loc[
                    df_query[value_header].isna(), value_header
                ] = blank_fill_value

                upstream_msg = (
                    f"| Variable '{var_key}' "
                    f"| Blank fill value: '{blank_fill_value}'"
                )

                self.sqltools.dataframe_to_table(
                    table_name=related_table,
                    dataframe=df_query_nan,
                    action='update',
                    force_overwrite=force_overwrite,
                    upstream_msg=upstream_msg
                )

    def reinit_sqlite_endogenous_tables(
            self,
            force_overwrite: bool = False,
    ) -> None:
        """Clear all values in all endogenous tables in the SQLite database.

        This method iterates over each endogenous data table in the Index and
        clears the table in the SQLite database, re-setting all values to Null.

        Args:
            force_overwrite (bool, optional): If True, forces the overwrite of
                existing data. Defaults to False.
        """
        allowed_var_types = Defaults.SymbolicDefinitions.VARIABLE_TYPES

        with db_handler(self.sqltools):
            for table_key, table in self.index.data.items():
                table: DataTable

                if table.type == allowed_var_types['ENDOGENOUS']:

                    self.logger.debug(
                        f"Reinitializing endogenous table '{table_key}' "
                        "in SQLite database.")

                    self.sqltools.delete_table_column_data(
                        table_name=table_key,
                        force_operation=force_overwrite,
                        column_name=Defaults.Labels.VALUES_FIELD['values'][0],
                    )

    def __repr__(self):
        """Return a string representation of the Database instance."""
        class_name = type(self).__name__
        return f'{class_name}'
