"""
file_manager.py 

@author: Matteo V. Rocco
@institution: Politecnico di Milano

This module provides a FileManager class designed to handle file and directory 
operations such as creating and erasing directories, copying files, and handling 
different types of data files like JSON, YAML, and Excel within a model management 
system. The FileManager facilitates robust management of file operations required 
in model setups, ensuring data integrity and ease of data manipulation across 
various components of the application.
"""

from ast import Constant
from types import NoneType
from typing import List, Dict, Any, Literal, Optional
from pathlib import Path

import os
import shutil
import json
import yaml

import pandas as pd

from esm.constants import Constants
from esm.log_exc import exceptions as exc
from esm.log_exc.logger import Logger
from esm.support import util


class FileManager:
    """
    A class to manage file operations, providing methods to handle directories 
    and file interactions including creating, deleting, loading, and copying 
    files across directories. This class simplifies managing file operations 
    required in various parts of a modeling application, ensuring that file
    manipulations are handled efficiently and reliably.

    Attributes:
        logger (Logger): A logger object for logging information and errors.
        xls_engine (str, optional): The default Excel engine to use. Defaults 
            to 'openpyxl'.

    Methods:
        create_dir: Creates a directory with an option to overwrite.
        erase_dir: Removes a directory and its contents.
        load_file: Loads a file from a specified directory.
        erase_file: Deletes a specific file.
        copy_file_to_destination: Copies a file from one directory to another.
        copy_all_files_to_destination: Copies all files from one directory to 
            another.
        dataframe_to_excel: Exports a DataFrame to an Excel file.
        excel_to_dataframes_dict: Converts an Excel file with multiple sheets 
            to a dictionary of DataFrames.
    """

    def __init__(
        self,
        logger: Logger,
        xls_engine: Literal['openpyxl', 'xlsxwriter', None] = None,
    ) -> None:
        """
        Initializes the FileManager object with a specified logger and an 
        optional Excel engine.

        Args:
            logger (Logger): The logger object used to log messages in the FileManager.
            xls_engine (Literal['openpyxl', 'xlsxwriter', None], optional): 
                The Excel engine to use for reading and writing Excel files. 
                Defaults to 'openpyxl'.
        """
        self.logger = logger.get_child(__name__)

        if xls_engine is None:
            self.xls_engine: Literal['openpyxl', 'xlsxwriter'] = 'openpyxl'
        else:
            self.xls_engine: Literal['openpyxl', 'xlsxwriter'] = xls_engine

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def create_dir(
            self,
            dir_path: Path,
            force_overwrite: bool = False,
    ) -> None:
        """
        Creates a directory at the specified path. Optionally overwrites the 
        existing directory.

        Args:
            dir_path (Path): The path where the directory will be created.
            force_overwrite (bool): If True, the existing directory will be 
                overwritten without confirmation.

        Returns:
            None: The method creates the directory or logs a message if it 
                already exists.
        """

        dir_name = dir_path.name

        if os.path.exists(dir_path) and not force_overwrite:
            self.logger.warning(f"Directory '{dir_name}' already exists.")
            response = input(
                'Overwrite directory 'f"'{dir_name}'(y/[n]): "
            ).lower()

            if response != 'y':
                self.logger.debug(
                    f"Directory '{dir_name}' not overwritten.")
                return

        if os.path.exists(dir_path) and force_overwrite:
            shutil.rmtree(dir_path)

        os.makedirs(dir_path, exist_ok=True)
        self.logger.debug(f"Directory '{dir_name}' created.")

    def erase_dir(
            self,
            dir_path: Path,
            force_erase: bool = False,
    ) -> bool:
        """
        Erases the directory specified by the path.

        Args:
            dir_path (Path): The path of the directory to erase.
            force_erase (bool): If True, the directory will be erased without 
                confirmation.

        Returns:
            bool: True if the directory was erased, False otherwise.
        """

        dir_name = str(dir_path).rsplit('\\', maxsplit=1)[-1]

        if os.path.exists(dir_path):
            if not force_erase:
                response = input(
                    'Do you really want to erase the directory '
                    f"'{dir_name}'(y/[n]): "
                ).lower()

                if response != 'y':
                    self.logger.debug(
                        f"Directory '{dir_name}' and its content not erased.")
                    return False

            try:
                shutil.rmtree(dir_path)
            except OSError as error:
                self.logger.error(f"Error: '{dir_name}' : {error.strerror}")
                return False
            else:
                self.logger.debug(f"Directory '{dir_name}' have been erased.")
                return True

        else:
            self.logger.warning(
                f"Folder '{dir_name}' does not exist. The folder cannot be erased.")
            return False

    def load_file(
            self,
            file_name: str,
            dir_path: Path,
            file_type: str = 'yml',
    ) -> Dict[str, Any]:
        """
        Loads a JSON or YAML file from the specified directory into a dictionary.

        Args:
            file_name (str): The name of the file to load.
            dir_path (Path): The path to the directory containing the file.
            file_type (str): The format of the file ('json' or 'yml').

        Returns:
            Dict[str, Any]: The contents of the file loaded into a dictionary.
        """

        if file_type == 'json':
            loader = json.load
        elif file_type in {'yml', 'yaml'}:
            loader = yaml.safe_load
        else:
            self.logger.error(
                'Invalid file type. Only JSON and YAML are allowed.')
            return {}

        file_path = Path(dir_path, file_name)

        try:
            with open(file_path, 'r', encoding='utf-8') as file_obj:
                file_contents = loader(file_obj)
                self.logger.debug(f"File '{file_name}' loaded.")
                return file_contents
        except FileNotFoundError as error:
            self.logger.error(
                f"Could not load file '{file_name}': {str(error)}")
            return {}

    def erase_file(
            self,
            dir_path: Path | str,
            file_name: str,
            force_erase: bool = False,
            confirm: bool = True,
    ) -> bool:
        """
        Erases a specified file from a directory.

        Args:
            dir_path (Path): The directory from which the file will be erased.
            file_name (str): The name of the file to erase.
            force_erase (bool): If True, erases the file without confirmation.
            confirm (bool): If True, prompts for user confirmation before erasing the file.

        Returns:
            bool: True if the file was successfully erased, False otherwise.
        """
        file_path = Path(dir_path) / file_name

        if not os.path.exists(file_path):
            self.logger.warning(
                f"File '{file_name}' does not exist. The file cannot be erased.")
            return False

        if confirm and not force_erase:
            if not util.confirm_action(
                    f"Do you really want to erase file '{file_name}'? "
            ):
                self.logger.debug(f"File '{file_name}' not erased.")
                return False

        try:
            os.remove(file_path)
            self.logger.debug(f"File '{file_name}' have been erased.")
            return True
        except OSError as error:
            self.logger.error(f"Error: '{file_name}' : {error.strerror}")
            return False

    def dir_files_check(
            self,
            dir_path: str | Path,
            files_names_list: List[str],
    ) -> bool:
        """
        Checks if the specified directory exists and all listed files are 
        present in it.

        Args:
            dir_path (str | Path): The directory path to check.
            files_names_list (List[str]): A list of file names to check for 
                existence within the directory.

        Returns:
            bool: True if the directory and all files exist, False otherwise.

        Raises:
            ModelFolderError: If the directory does not exist or any file is 
                missing.
        """

        msg = ''

        if not Path(dir_path).is_dir():
            msg = f"Directory '{dir_path}' does not exist."

        missing_files = [
            file_name for file_name in files_names_list
            if not (Path(dir_path) / file_name).is_file()]

        if missing_files:
            msg = f"Model setup files '{missing_files}' are missing."

        if msg:
            self.logger.error(msg)
            raise exc.ModelFolderError(msg)

        return True

    def copy_file_to_destination(
            self,
            path_destination: str | Path,
            path_source: str,
            file_name: str,
            file_new_name: Optional[str] = None,
            force_overwrite: bool = False,
    ) -> None:
        """
    Copies a file from the source path to the destination path, with an option 
    to rename and overwrite.

    Args:
        path_destination (str | Path): The destination path where the file will 
            be copied.
        path_source (str): The source path from which the file will be copied.
        file_name (str): The name of the file to be copied.
        file_new_name (Optional[str]): Optional new name for the file at the 
            destination.
        force_overwrite (bool): If True, existing file at the destination will 
            be overwritten without prompt.

    Raises:
        FileNotFoundError: If the source file does not exist.
    """
        source_path = Path(path_source) / file_name
        destination_file_name = file_new_name or source_path.name
        destination_file_path = Path(path_destination) / destination_file_name

        if destination_file_path.exists() and not force_overwrite:
            self.logger.warning(f"'{file_name}' already exists.")
            user_input = input(f"Overwrite '{file_name}'? (y/[n]): ")
            if user_input.lower() != 'y':
                self.logger.debug(f"'{file_name}' NOT overwritten.")
                return

        if source_path.exists() and source_path.is_file():
            shutil.copy2(source_path, destination_file_path)
            self.logger.debug(
                f"File '{file_name}' successfully copied as '{file_new_name}'.")
        else:
            msg = f"The source file '{source_path}' does not exist."
            self.logger.error(msg)
            raise FileNotFoundError(msg)

    def copy_all_files_to_destination(
            self,
            path_source: str | Path,
            path_destination: str | Path,
            force_overwrite: bool = False,
    ) -> None:
        """
        Copies all files and directories from the source path to the destination 
        path, with an option to overwrite.

        Args:
            path_source (str | Path): The path of the directory whose contents 
                are to be copied.
            path_destination (str | Path): The destination path where the 
                contents will be copied.
            force_overwrite (bool): If True, existing content at the 
                destination will be overwritten without prompt.

        Raises:
            ModelFolderError: If the source path does not exist or is not a directory.
        """

        path_source = Path(path_source)
        path_destination = Path(path_destination)

        if not path_source.exists():
            msg = "The passed source path does not exists."
            self.logger.error(msg)
            raise exc.ModelFolderError(msg)

        if not os.path.isdir(path_source):
            msg = "The passed source path is not a directory."
            self.logger.error(msg)
            raise exc.ModelFolderError(msg)

        if not path_destination.exists():
            self.create_dir(path_destination)

        if os.listdir(path_destination) and not force_overwrite:
            dir_destination = os.path.basename(path_destination)

            self.logger.warning(f"Directory '{dir_destination}' not empty.")

            user_input = input(
                f"Overwrite content of '{dir_destination}'? (y/[n]): ")
            if user_input.lower() != 'y':
                self.logger.debug(f"'{dir_destination}' NOT overwritten.")
                return

        try:
            shutil.copytree(
                src=path_source,
                dst=path_destination,
                dirs_exist_ok=True
            )
            self.logger.debug(
                f"Directory '{os.path.basename(path_source)}' and all its "
                "content successfully copied.")
        except shutil.Error as msg:
            self.logger.error(f"Error copying items: {msg}")

    def dict_to_excel_headers(
            self,
            dict_name: Dict[str, Any],
            excel_dir_path: Path,
            excel_file_name: str,
            writer_engine: Optional[Literal['openpyxl', 'xlsxwriter']] = None,
    ) -> None:
        """
        Generates an Excel file with sheets named according to dictionary keys 
        and headers as specified in the dictionary values.

        Args:
            dict_name (Dict[str, Any]): Dictionary with sheet names as keys and 
                a list of column headers as values.
            excel_dir_path (Path): The directory path where the Excel file will 
                be saved.
            excel_file_name (str): The filename for the Excel file to be created.
            writer_engine (Literal['openpyxl', 'xlsxwriter'], optional): 
                The Excel writing engine to use. If None, uses the engine 
                defined in __init__.

        Raises:
            TypeError: If dict_name is not a dictionary.
            SettingsError: If any sheet headers list is invalid.
        """
        if writer_engine is None:
            writer_engine = self.xls_engine

        if not isinstance(dict_name, Dict):
            error_msg = f"{dict_name} is not a dictionary."
            self.logger.error(error_msg)
            raise TypeError(error_msg)

        def write_excel(
                excel_file_path: str | Path,
                dict_name: Dict[str, Any]
        ) -> None:
            """Support function to generate excel"""
            with pd.ExcelWriter(
                excel_file_path,
                engine=writer_engine,
            ) as writer:
                for sheet_name, headers_list in dict_name.items():
                    if not isinstance(headers_list, List):
                        msg = f"Invalid headers list for table '{sheet_name}'."
                        self.logger.error(msg)
                        raise exc.SettingsError(msg)

                    dataframe = pd.DataFrame(columns=headers_list)
                    sheet = writer.book.create_sheet(sheet_name)
                    writer.sheets[sheet_name] = sheet
                    dataframe.to_excel(
                        writer,
                        sheet_name=sheet_name,
                        index=False
                    )
                    self.logger.debug(
                        f"Excel tab name '{sheet_name}' inserted "
                        f"into '{os.path.basename(excel_file_path)}'."
                    )

        excel_file_path = Path(excel_dir_path, excel_file_name)

        if os.path.exists(excel_file_path):
            self.logger.warning(
                f"Excel file '{excel_file_name}' already exists.")
            response = input(
                'Do you really want to overwrite the file '
                f"'{excel_file_name}'(y/[n]): "
            ).lower()

            if response == 'y':
                write_excel(excel_file_path, dict_name)
                self.logger.warning(
                    f"Excel file '{excel_file_name}' overwritten.")
            else:
                self.logger.debug(
                    f"Excel file '{excel_file_name}' not overwritten.")
        else:
            write_excel(excel_file_path, dict_name)
            self.logger.debug(
                f"Excel file '{excel_file_name}' generated.")

    def dataframe_to_excel(
            self,
            dataframe: pd.DataFrame,
            excel_filename: str,
            excel_dir_path: str,
            sheet_name: Optional[str] = None,
            writer_engine: Optional[Literal['openpyxl', 'xlsxwriter']] = None,
            force_overwrite: bool = False,
    ) -> None:
        """
        Exports a DataFrame to an Excel file, optionally allowing for 
        overwriting an existing file.

        Args:
            dataframe (pd.DataFrame): The DataFrame to export.
            excel_filename (str): The name of the Excel file to create.
            excel_dir_path (str): The directory path where the Excel file will 
                be saved.
            sheet_name (str, optional): The name of the sheet in which to save 
                the DataFrame. Defaults to DataFrame name if None.
            writer_engine (Literal['openpyxl', 'xlsxwriter'], optional): 
                The Excel writing engine to use. If None, uses the engine 
                defined in __init__.

        Raises:
            Warning: If the file already exists and the user opts not to overwrite.
        """
        if writer_engine is None:
            writer_engine = self.xls_engine

        excel_file_path = Path(excel_dir_path, excel_filename)

        if not force_overwrite:
            if excel_file_path.exists():
                confirm = input(
                    f"File {excel_filename} already exists. \
                        Do you want to overwrite it? (y/[n])"
                )
                if confirm.lower() != 'y':
                    self.logger.warning(
                        f"File '{excel_filename}' not overwritten.")
                    return

        mode = 'a' if excel_file_path.exists() else 'w'
        if_sheet_exists = 'replace' if mode == 'a' else None

        self.logger.debug(
            f"Exporting dataframe '{sheet_name}' to '{excel_filename}'.")

        if sheet_name is None:
            sheet_name = str(dataframe)

        with pd.ExcelWriter(
            excel_file_path,
            engine=writer_engine,
            mode=mode,
            if_sheet_exists=if_sheet_exists,
        ) as writer:
            dataframe.to_excel(writer, sheet_name=sheet_name, index=False)

    def excel_to_dataframes_dict(
            self,
            excel_file_name: str,
            excel_file_dir_path: Path | str,
            empty_data_fill: Optional[Any] = None,
            set_values_type: bool = True,
    ) -> Dict[str, pd.DataFrame]:
        """
        Reads an Excel file composed of multiple tabs and returns a dictionary 
        with keys representing each tab's name and values as Pandas DataFrames 
        containing the data from each tab.

        Args:
            excel_file_name (str): The name of the Excel file to read.
            excel_file_dir_path (Path | str): The directory path where the 
                Excel file is located.
            empty_data_fill (Optional[Any], optional): Value to fill empty 
                cells with in the DataFrames. Defaults to None.
            dtype_values (Optional[type[str]], optional): Data type to force 
                for the values DataFrame columns. Defaults to None.

        Returns:
            Dict[str, pd.DataFrame]: A dictionary containing DataFrames for 
                each sheet in the Excel file.

        Raises:
            FileNotFoundError: If the specified Excel file does not exist.
        """

        file_path = Path(excel_file_dir_path, excel_file_name)

        if set_values_type:
            values_dtype = Constants.NumericalSettings.STD_VALUES_TYPE
            values_name = Constants.Labels.VALUES_FIELD['values'][0]

        if not os.path.exists(file_path):
            self.logger.error(f'{excel_file_name} does not exist.')
            raise FileNotFoundError(f"{excel_file_name} does not exist.")

        df_dict = pd.read_excel(io=file_path, sheet_name=None)

        for dataframe in df_dict.values():
            for col in dataframe.columns:

                if col == values_name:
                    dataframe[col] = dataframe[col].astype(values_dtype)

                if empty_data_fill is not None:
                    dataframe.fillna(empty_data_fill)

        self.logger.debug(f"Excel file '{excel_file_name}' loaded.")
        return df_dict

    def excel_tab_to_dataframe(
            self,
            excel_file_name: str,
            excel_file_dir_path: Path | str,
            tab_name: str = None,
    ) -> pd.DataFrame:
        """
        Reads a specific tab from an Excel file and returns the data as a 
        Pandas DataFrame.

        Args:
            excel_file_name (str): The name of the Excel file to read.
            excel_file_dir_path (Path | str): The directory path where the 
                Excel file is located.
            tab_name (str, optional): The name of the tab to read. If None, 
                reads the first tab. Defaults to None.

        Returns:
            pd.DataFrame: DataFrame containing data from a specified tab.

        Raises:
            FileNotFoundError: If the specified Excel file does not exist.
        """

        file_path = Path(excel_file_dir_path, excel_file_name)

        if not os.path.exists(file_path):
            msg = f"{excel_file_name} does not exist."
            self.logger.error(msg)
            raise FileNotFoundError(msg)

        xlsx_file = pd.ExcelFile(file_path)
        sheet_names = xlsx_file.sheet_names

        if tab_name is None:
            if len(sheet_names) > 1:
                msg = f"Multiple tabs found in '{excel_file_name}'. Specify " \
                    f"one of the following tabs: '{sheet_names}'."
                self.logger.error(msg)
                raise ValueError(msg)
            tab_name = sheet_names[0]
        else:
            if tab_name not in sheet_names:
                msg = f"Tab '{tab_name}' not found in '{excel_file_name}'. " \
                    f"Available tabs: '{sheet_names}'."
                self.logger.error(msg)
                raise ValueError(msg)

        dataframe = xlsx_file.parse(tab_name)
        dataframe = dataframe.astype(object).where(pd.notna(dataframe), None)

        self.logger.debug(
            f"Excel tab '{tab_name}' loaded from '{excel_file_name}'.")

        return dataframe

    def load_data_structure(
            self,
            structure_key: str,
            source: str,
            dir_path: Path | str,
    ) -> Dict:

        available_sources = Constants.ConfigFiles.AVAILABLE_SOURCES
        util.validate_selection(
            selection=source,
            valid_selections=available_sources
        )

        if source == 'yml':
            file_name = structure_key + '.yml'
            data = self.load_file(file_name, dir_path)

            if not data:
                msg = f"File '{file_name}' is empty."
                self.logger.error(msg)
                raise exc.SettingsError(msg)

        elif source == 'xlsx':
            file_name = Constants.ConfigFiles.SETUP_XLSX_FILE
            raw_data = self.excel_tab_to_dataframe(
                file_name, dir_path, structure_key)

            if raw_data.empty:
                msg = f"Excel tab '{structure_key}' is empty."
                self.logger.error(msg)
                raise exc.SettingsError(msg)

            data_pivot_keys = Constants.DefaultStructures.XLSX_PIVOT_KEYS
            merge_dict = True if \
                structure_key == Constants.ConfigFiles.SETUP_INFO[2] else False

            data = util.pivot_dataframe_to_data_structure(
                data=raw_data,
                primary_key=data_pivot_keys[structure_key][0],
                secondary_key=data_pivot_keys[structure_key][1],
                merge_dict=merge_dict,
            )

        else:
            msg = "Model settings source not recognized. Available sources: " \
                f"{available_sources}."
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        return data

    def validate_data_structure(
            self,
            data: Dict,
            validation_structure: Dict,
            path: str = '',
    ) -> Dict[str, str]:

        problems = {}
        optional_label = Constants.DefaultStructures.OPTIONAL
        any_label = Constants.DefaultStructures.ANY
        all_optional_fields = False

        if all(
            isinstance(v_exp, tuple) and v_exp[0] == optional_label
            for v_exp in validation_structure.values()
        ):
            all_optional_fields = True

        for k_exp, v_exp in validation_structure.items():
            current_path = f"{path}.{k_exp}" if path else k_exp

            # if no data are passed, all keys must be optional
            if not data:
                if all_optional_fields:
                    continue
                else:
                    problems[current_path] = f"Data structure is empty, but " \
                        "there are mandatory key-value pairs."

            # check for keys and related values
            if isinstance(v_exp, tuple) and v_exp[0] == optional_label:
                optional = True
                expected_value = v_exp[1:]
            else:
                optional = False
                expected_value = v_exp

            # generic keys are checked in the other for loop
            if k_exp == any_label:
                continue

            # check if mandatory keys are missing
            elif k_exp not in data:
                if optional:
                    continue
                problems[current_path] = f"Missing key-value pair."

            # check values types and content for mandatory keys
            else:
                value = data[k_exp]

                if isinstance(expected_value, type):
                    if not isinstance(value, expected_value | NoneType):
                        problems[current_path] = \
                            f"Expected {expected_value}, got {type(value)}"
                    if not optional and not value:
                        problems[current_path] = "Empty value."

                elif isinstance(expected_value, tuple):
                    if all(isinstance(v, type) for v in expected_value):
                        if not any(isinstance(value, v | NoneType) for v in expected_value):
                            problems[current_path] = \
                                f"Expected {expected_value}, got {type(value)}"
                        if not optional and not value:
                            problems[current_path] = "Empty value."

                # check for nested dictionaries
                elif isinstance(expected_value, dict):
                    if isinstance(value, dict):
                        problems.update(
                            self.validate_data_structure(
                                value, expected_value, current_path)
                        )
                    else:
                        problems[current_path] = \
                            f"Expected dict, got {type(value).__name__}"

                else:
                    problems[current_path] = "Unexpected value."

        # in case data is empty, no further checks required
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key

                if key not in validation_structure:

                    # check for unexpected keys
                    if any_label not in validation_structure:
                        problems[current_path] = "Unexpected key-value pair."

                    # check for nested dictionaries
                    else:
                        if isinstance(validation_structure[any_label], tuple) \
                                and validation_structure[any_label][0] == optional_label:
                            expected_value = validation_structure[any_label][1]
                        else:
                            expected_value = validation_structure[any_label]

                        if isinstance(value, dict):
                            problems.update(
                                self.validate_data_structure(
                                    value, expected_value, current_path)
                            )

        problems = util.remove_empty_items_from_dict(
            problems, empty_values=[{}])

        return problems
