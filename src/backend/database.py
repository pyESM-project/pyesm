import pandas as pd
import xarray as xr

from typing import Dict, List, Any
from pathlib import Path

from log_exc.logger import Logger
from log_exc import exceptions as exc
from util import constants
from util.file_manager import FileManager


class Database:

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            database_dir_path: Path,
            database_settings: Dict[str, str],
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info(f"Generation of '{self}' object.")

        self.files = files

        self.database_dir_path = database_dir_path
        self.database_settings = database_settings

        self.sets_structure = constants._SETS.copy()
        self.sets = None

        self.variables = constants._VARIABLES.copy()
        self.coordinates = None
        self.input_data_hierarchy = None

        self.data = None

        if self.database_settings['generate_blank_sets']:
            self.files.dict_to_excel_headers(
                dict_name=self.sets_structure,
                excel_dir_path=self.database_dir_path,
                excel_file_name=self.database_settings['sets_file_name'],
                table_headers_key='table_headers',
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

    def load_coordinates(
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

        self.logger.info(f"Variables coordinates loaded.")

    def generate_blank_database(
            self,
    ) -> None:

        self.logger.info(f"Generation of blank database.")

        if self.coordinates is None:
            error_msg = f"Variables coordinates not defined for '{self}' object."
            self.logger.error(error_msg)
            raise exc.MissingDataError(error_msg)

        if self.data is not None:
            self.logger.warning(
                f"Database already initialized in '{self}' object.")
            user_input = input(
                f"Overwrite Database? (y/[n]): ")
            if user_input.lower() != 'y':
                self.logger.debug(f"Original Database not overwritten.")
                return

        self.data = {}

        for var_name, var_coords in self.coordinates.items():
            self.logger.debug(f"Creating DataArray for variable '{var_name}'.")
            self.data[var_name] = xr.DataArray(
                data=None,
                coords=var_coords,
                dims=list(var_coords.keys()),
            )

        self.logger.info(f"Blank database generated.")

    def generate_input_hierarchy(
            self,
            hierarchy_map: Dict[str, str],
    ) -> Dict[str, Any]:

        hierarchy = {key: [] for key in hierarchy_map.keys()}

        self.logger.debug(
            f"Loading input data hierarchy labels from settings")

        for key, value in hierarchy_map.items():
            if value in self.sets:
                value_header_name = \
                    self.sets_structure[value]['table_headers']['name'][0]
                hierarchy[key] = list(self.sets[value][value_header_name])
            elif value == 'variables':
                hierarchy[key] = list(self.variables.keys())

        self.logger.debug(f"Input data hierarchy labels loaded from settings.")

        return hierarchy

    def generate_input_files(
            self,
    ) -> None:

        self.logger.info(
            f"Generation of input files for '{self}' object.")

        input_files_dir_path = Path(
            self.database_dir_path /
            self.database_settings['input_data_dir_name'])

        self.files.create_dir(input_files_dir_path)

        self.input_data_hierarchy = self.generate_input_hierarchy(
            self.database_settings['input_data_hierarchy_map'])

        if self.input_data_hierarchy['directories']:

            for directory in self.input_data_hierarchy['directories']:
                self.files.create_dir(Path(input_files_dir_path/directory))
                # qui

        self.logger.info(
            f"Input files for '{self}' object generated.")
