from itertools import product
from pathlib import Path
from typing import Dict, List, Any

import pandas as pd
import xarray as xr

from src.log_exc.logger import Logger
from src.log_exc import exceptions as exc
from src.util import constants
from src.util import util
from src.util.file_manager import FileManager
from src.util.sql_manager import SQLManager, connection


class Database:

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            database_settings: Dict[str, str],
            database_dir_path: Path,
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info(f"'{self}' object initialization...")

        self.files = files

        self.sets_structure = constants._SETS.copy()
        self.variables = constants._VARIABLES.copy()
        self.sets = None
        self.coordinates = None

        self.database_settings = database_settings
        self.database_dir_path = database_dir_path

        self.sqltools = SQLManager(
            logger=self.logger,
            database_dir_path=self.database_dir_path,
            database_name=database_settings['database_name']
        )

        if not Path(
            self.database_dir_path,
            self.database_settings['sets_excel_file_name']
        ).exists():
            self.create_blank_sets()

        # self.input_data_hierarchy = None

        self.logger.info(f"'{self}' object initialized.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    @connection
    def create_blank_sets(self) -> None:
        for value in self.sets_structure.values():
            self.sqltools.create_table(
                table_name=value['table_name'],
                table_fields=value['table_headers']
            )
            self.sqltools.table_to_excel(
                excel_filename=self.database_settings['sets_excel_file_name'],
                excel_dir_path=self.database_dir_path,
                table_name=value['table_name'],
            )

    @connection
    def load_sets(self) -> None:
        if self.sets is not None:
            self.logger.debug(
                f"Sets are already defined in the '{self}' object.")
            user_input = input(
                "Overwrite Sets? (y/[n]): ")
            if user_input.lower() != 'y':
                self.logger.debug("Original Sets not owerwritten.")
                return

        self.sets = self.files.excel_to_dataframes_dict(
            excel_file_name=self.database_settings['sets_excel_file_name'],
            excel_file_dir_path=self.database_dir_path,
            empty_data_fill='',
        )

        for table_key, table in self.sets.items():
            self.sqltools.dataframe_to_table(
                table_name=table_key,
                table_df=table
            )

        self.logger.info(
            f"New Sets loaded in {self} class and "
            f"'{self.database_settings['database_name']}' from "
            f"'{self.database_settings['sets_excel_file_name']}'."
        )

    @connection
    def generate_blank_database(self) -> None:

        self.logger.info(f"Generation of empty database...")

        self.load_variables_coordinates()

        for var_key, var_info in self.variables.items():
            set_field = var_info['set_headers']
            table_fields = util.generate_dict_with_none_values(
                var_info['coordinates'])

            for field_key in table_fields.keys():
                table_fields[field_key] = \
                    self.sets_structure[field_key]['table_headers'][set_field]

            unpivoted_coordinates = None
            if self.coordinates[var_key]:
                unpivoted_coordinates = self.unpivot_coordinates(
                    self.coordinates[var_key])

            self.sqltools.create_table(
                table_name=var_key,
                table_fields=table_fields,
                table_content=unpivoted_coordinates
            )

        self.logger.info(f"Empty database generated.")

    def load_variables_coordinates(self) -> None:

        self.logger.info(f"Loading variables coordinates...")

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

        for var_key, var_info in self.variables.items():
            self.logger.debug(
                "Loading coordinates for variable "
                f"'{var_info['symbol']}'.")

            self.coordinates[var_key] = {}

            for coord_key, coord_info in var_info['coordinates'].items():
                set_label = self.sets_structure[coord_key]['table_name']
                header_label_type = var_info['set_headers']
                header_label = self.sets_structure[coord_key]['table_headers'][header_label_type][0]

                if coord_info == 'all':
                    set_values = list(self.sets[set_label][header_label])

                elif isinstance(coord_info, dict) and coord_info['set_categories']:
                    category_filter_id = coord_info['set_categories']
                    category_filter = self.sets_structure[coord_key]['set_categories'][category_filter_id]
                    category_header_name = self.sets_structure[coord_key]['table_headers']['category'][0]
                    set_filtered = self.sets[set_label].query(
                        f'{category_header_name} == "{category_filter}"'
                    )
                    set_values = list(set_filtered[header_label])
                else:
                    error_msg = f"Missing or wrong data in 'sets_structure' parameter."
                    self.logger.error(error_msg)
                    raise exc.MissingDataError(error_msg)

                self.coordinates[var_key][header_label] = set_values

        self.logger.info(f"Variables coordinates loaded.")

    def unpivot_coordinates(
            self,
            coordinates_dict: Dict[str, List[str]],
    ) -> pd.DataFrame:

        df = pd.DataFrame()
        cartesian_product = list(product(*coordinates_dict.values()))
        df = pd.DataFrame(
            cartesian_product,
            columns=coordinates_dict.keys()
        )
        return df

    # design method to read a pivot map in settings,
    # then pivot blank input data tables
    # then print to excel
    # the same pivot map is supposed to be an argument of the load data method

    def generate_input_hierarchy(
            self,
            hierarchy_map: Dict[str, Dict[str, str]],
    ) -> Dict[str, Dict[str, Any]]:

        hierarchy = util.generate_dict_with_none_values(hierarchy_map)

        self.logger.debug(
            "Loading input data hierarchy labels from settings")

        for item_key, item_value in hierarchy_map.items():
            for key, value in item_value.items():

                if value in self.sets:
                    value_header_name = \
                        self.sets_structure[value]['table_headers']['name'][0]
                    hierarchy[item_key][key] = \
                        list(self.sets[value][value_header_name])
                elif value == 'variables':
                    hierarchy[item_key][key] = list(self.variables.keys())

        self.logger.debug("Input data hierarchy labels loaded from settings.")

        return hierarchy

    def generate_input_files(self) -> None:

        self.logger.info(
            f"Generation of input files for '{self}' object.")

        input_files_dir_path = Path(
            self.database_dir_path /
            self.database_settings['input_data_dir_name'])

        self.logger.info(
            f"Input files for '{self}' object generated.")
