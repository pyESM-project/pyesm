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

        self.sets_structure = constants._SETS
        self.sets = None

        self.variables_info = constants._VARIABLES.copy()
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
                return {}

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
            index_key: str = 'coords',
    ) -> None:

        self.logger.info(f"Loading variables coordinates.")

        for var in self.variables_info:
            self.logger.debug(f"Loading coordinates for variable '{var}'.")

            if index_key not in self.variables_info[var]:
                self.variables_info[var][index_key] = {}

            for coord in self.variables_info[var]['coords_structure']:
                set_info = self.variables_info[var]['coords_structure'][coord]
                set_name = set_info['set']

                if 'set_category' in set_info:
                    set_cat = self.sets_structure[set_name]['set_categories'][set_info['set_category']]
                    category_name = self.sets_structure[set_name]['table_headers']['category'][0]
                    index = pd.MultiIndex.from_frame(
                        self.sets[set_name].query(
                            f'{category_name} == "{set_cat}"'
                        )
                    )
                    self.variables_info[var][index_key][coord] = index

                # it must be checked in case of multiple dimensions
                else:
                    index = pd.MultiIndex.from_frame(self.sets[set_name])
                    self.variables_info[var][index_key][coord] = index

    def generate_blank_database(self) -> None:

        if self.data is not None:
            self.logger.warning(
                f"Database already initialized in '{self}' object.")
            user_input = input(
                f"Overwrite Database? (y/[n]): ")
            if user_input.lower() != 'y':
                self.logger.debug(f"Original Database not overwritten.")
                return

        self.data = {}

        for var_name, var_info in self.variables_info.items():
            if var_info['type'] == 'exogenous':
                self.logger.debug(
                    f"Creating DataArray for variable '{var_name}'.")
                coords = var_info['coords']
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

    # def generate_input_files(
    #         self,
    # ) -> None:

    #     if 'coords' not in self.variables_info:
    #         error_msg = f"Variables coordinates not defined in the '{self}' object."
    #         self.logger.error(error_msg)
    #         raise exc.MissingDataError(error_msg)

    #     self.logger.info(
    #         f"Generation of input files for '{self}' object.")

    #     input_files_dir_path = Path(
    #         self.database_dir_path / self.data_dir_settings['data_dir_name'])

    #     self.files.create_dir(input_files_dir_path)

    #     data_hierarchy = self.data_dir_settings['data_hierarchy']

    #     for var_name, var_info in self.variables_info.items():
    #         coords = var_info['coords']
    #         if var_info['type'] == 'exogenous':
    #             self.logger.debug(
    #                 f"Generating input files for variable '{var_name}'.")
    #             for coord in coords:
    #                 pass

    #     self.logger.info(
    #         f"Input files for '{self}' object generated.")
