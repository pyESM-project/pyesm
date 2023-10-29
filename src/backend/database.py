import numpy as np
import pandas as pd
import xarray as xr


from typing import Dict, Any
from pathlib import Path

from log_exc.logger import Logger
from log_exc import exceptions as exc
from util import constants
from util.file_manager import FileManager
from util.database_sql import DatabaseSQL


class Database:

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            database_dir_path: Path,
            database_settings: Dict[str, str],
            data_dir_settings: Dict[str, Dict[str, str]],
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info(f"Generation of '{self}' object.")

        self.files = files

        self.database_dir_path = database_dir_path
        self.database_settings = database_settings
        self.data_dir_settings = data_dir_settings

        self.sets_structure = constants._SETS.copy()
        self.sets = None

        self.variables = constants._VARIABLES.copy()
        self.coordinates = None
        self.data = None
        self.data_sql = None

        if self.database_settings['generate_blank_sets']:
            self.files.dict_to_excel_headers(
                dict_name=self.sets_structure,
                excel_dir_path=database_dir_path,
                excel_file_name=self.database_settings['sets_file_name'],
                table_headers_key='table_headers',
            )

        if self.database_settings['generate_database_sql']:
            self.generate_blank_database_sql(
                database_sql_name=self.database_settings['database_sql_name'],
            )

        self.logger.info(f"'{self}' object initialized.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def load_sets(self) -> Dict[str, pd.DataFrame]:

        if self.sets is not None:
            self.logger.debug(
                f"Sets are already defined in the '{self}' object.")
            user_input = input(
                f"Overwrite Sets? (y/[n]): ")
            if user_input.lower() != 'y':
                self.logger.debug(f"Original Sets not owerwritten.")
                return

        self.sets = self.files.excel_to_dataframes_dict(
            excel_file_name=self.database_settings['sets_file_name'],
            excel_file_dir_path=self.database_dir_path,
            empty_data_fill='',
        )
        self.logger.info(
            "New Sets loaded from "
            f"'{self.database_settings['sets_file_name']}'."
        )

    def load_vars_coordinates(
            self,
    ) -> None:

        self.logger.info(f"Loading variables coordinates.")

        if self.coordinates is not None:
            self.logger.warning(
                f"Variable coordinates already initialized in '{self}' object.")
            user_input = input(
                f"Overwrite variable coordinates? (y/[n]): ")
            if user_input.lower() != 'y':
                self.logger.debug(
                    f"Original variables coordinates not overwritten.")
                return

        self.coordinates = {}

        for variable in self.variables:
            self.logger.debug(
                "Loading coordinates for variable "
                f"'{self.variables[variable]['symbol']}'.")

            self.coordinates[variable] = {}

            for set_key, set_value in self.sets.items():
                if self.sets_structure[set_key]['variables_shape'] is False:
                    index = pd.MultiIndex.from_frame(set_value)
                    self.coordinates[variable][set_key] = index

            for coordinate in self.variables[variable]['shape']:
                set_info = self.variables[variable]['shape'][coordinate]
                set_name = set_info['set']

                if 'set_category' in set_info:
                    set_cat = self.sets_structure[set_name]['set_categories'][set_info['set_category']]
                    category_name = self.sets_structure[set_name]['table_headers']['category'][0]

                    index = pd.MultiIndex.from_frame(
                        self.sets[set_name].query(
                            f'{category_name} == "{set_cat}"'
                        )
                    )
                    self.coordinates[variable][coordinate] = index

                else:
                    index = pd.MultiIndex.from_frame(self.sets[set_name])
                    self.coordinates[variable][coordinate] = index

    def generate_blank_database(
            self,
            coordinates_label: str = 'coordinates',
    ) -> None:

        if self.data is not None:
            self.logger.warning(
                f"Database already initialized in '{self}' object.")
            user_input = input(
                f"Overwrite Database? (y/[n]): ")
            if user_input.lower() != 'y':
                self.logger.debug(f"Original Database not overwritten.")
                return

        self.data = {}

        for var_name, var_info in self.variables.items():

            if coordinates_label not in var_info:
                error_msg = f"Variables coordinates not defined for '{var_name}'."
                self.logger.error(error_msg)
                raise exc.MissingDataError(error_msg)

            if var_info['type'] == 'exogenous':
                self.logger.debug(
                    f"Creating DataArray for variable '{var_name}'.")
                coords = var_info[coordinates_label]
                self.data[var_name] = xr.DataArray(
                    data=None,
                    coords=coords,
                    dims=list(coords.keys()),
                )

        self.logger.info(f"Blank database initialized.")

    def generate_blank_database_sql(
            self,
            database_sql_name: str = 'database.db',
    ) -> None:

        self.database_sql_name = database_sql_name
        self.database_sql_path = Path(
            self.database_dir_path, database_sql_name)

        self.data_sql = DatabaseSQL(
            logger=self.logger,
            database_sql_path=self.database_sql_path,
        )

        for table in self.sets_structure:
            self.data_sql.create_table(
                table_name=self.sets_structure[table]['table_name'],
                table_fields=self.sets_structure[table]['table_headers']
            )

    def generate_input_files(
            self,
    ) -> None:

        self.logger.info(
            f"Generation of input files for '{self}' object.")

        input_files_dir_path = Path(
            self.database_dir_path / self.data_dir_settings['data_dir_name'])

        self.files.create_dir(input_files_dir_path)

        data_hierarchy = self.data_dir_settings['hierarchy']

        if data_hierarchy['directories'] is not None:
            coord_category = data_hierarchy['directories']
            coord_column_label = \
                self.sets_structure[coord_category]['table_headers']['name'][0]

            for coord_name in self.sets[coord_category].get(coord_column_label):
                self.files.create_dir(input_files_dir_path / coord_name)

        if data_hierarchy['files'] is not None:
            pass

        # hierarchy: {directories: None, files: scenarios, sheets: variables}
        # hierarchy: {directories: scenarios, files: variables, sheets: None}
        # hierarchy: {directories: None, files: variables, sheets: scenarios}

        self.logger.info(
            f"Input files for '{self}' object generated.")
