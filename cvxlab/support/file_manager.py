"""Module defining the FileManager class.

The FileManager class provides methods for handling file and directory operations
such as creating and erasing directories, copying files, and managing data files
like JSON, YAML, and Excel. It is designed to facilitate robust management of
file operations required in model setups, ensuring data integrity and ease of
data manipulation across various components of the application.
"""
from types import NoneType
from typing import List, Dict, Any, Literal, Optional
from pathlib import Path

import importlib.util
import os
import shutil
import json
import yaml

import pandas as pd

from cvxlab.defaults import Defaults
from cvxlab.log_exc import exceptions as exc
from cvxlab.log_exc.logger import Logger
from cvxlab.support import util


class FileManager:
    """FileManager class for managing file and directory operations.

    The FileManager class provides methods to handle directories and file interactions,
    including creating, deleting, loading, and copying files across directories.
    It simplifies file operations required in various parts of a modeling application,
    ensuring that file manipulations are handled efficiently and reliably.

    Attributes:

    - logger (Logger): Logger object for logging information and errors.
    - xls_engine (str): Default Excel engine to use ('openpyxl' or 'xlsxwriter').

    """

    def __init__(
        self,
        logger: Logger,
        xls_engine: Literal['openpyxl', 'xlsxwriter', None] = None,
    ) -> None:
        """Initialize FileManager with logger and optional Excel engine.

        Args:
            logger (Logger): Logger object for logging messages.
            xls_engine (Literal['openpyxl', 'xlsxwriter', None], optional): Excel 
                engine for reading/writing files.
        """
        self.logger = logger.get_child(__name__)

        if xls_engine is None:
            self.xls_engine = 'openpyxl'
        else:
            self.xls_engine = xls_engine

    def create_dir(
            self,
            dir_path: Path,
            force_overwrite: bool = False,
    ) -> None:
        """Create a directory at the specified path.

        Args:
            dir_path (Path): Path where the directory will be created.
            force_overwrite (bool): If True, overwrite existing directory.
        """
        dir_name = dir_path.name

        if os.path.exists(dir_path) and not force_overwrite:
            self.logger.warning(f"Directory '{dir_name}' already exists.")
            if not util.get_user_confirmation(f"Overwrite directory '{dir_name}'?"):
                self.logger.debug(f"Directory '{dir_name}' not overwritten.")
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
        """Erase the directory at the specified path.

        Args:
            dir_path (Path): Path of the directory to erase.
            force_erase (bool): If True, erase without confirmation.

        Returns:
            bool: True if erased, False otherwise.
        """
        dir_name = str(dir_path).rsplit('/', maxsplit=1)[-1]

        if os.path.exists(dir_path):
            if not force_erase:
                if not util.get_user_confirmation(
                    f"Do you really want to erase the directory '{dir_name}'?"
                ):
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

    def load_structured_file(
            self,
            file_name: str,
            dir_path: Path,
            file_type: str = 'yml',
    ) -> Dict[str, Any]:
        """Load a JSON or YAML file from the specified directory.

        Args:
            file_name (str): Name of the file to load.
            dir_path (Path): Directory containing the file.
            file_type (str): Format of the file ('json' or 'yml').

        Returns:
            Dict[str, Any]: Contents of the file as a dictionary.
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

    def load_functions_from_module(
            self,
            file_name: str,
            dir_path: Path | str,
    ) -> list[callable]:
        """Load functions from a Python module.

        Returns:
            list[callable]: List of functions defined in the file.
        """
        file_path = Path(dir_path) / file_name

        if not os.path.exists(file_path):
            return []

        spec = importlib.util.spec_from_file_location(
            "module.name", file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        functions_list = [
            getattr(module, attr) for attr in dir(module)
            if callable(getattr(module, attr))
        ]

        return functions_list

    def erase_file(
            self,
            dir_path: Path | str,
            file_name: str,
            force_erase: bool = False,
            confirm: bool = True,
    ) -> bool:
        """Erase a specified file from a directory.

        Args:
            dir_path (Path | str): Directory containing the file.
            file_name (str): Name of the file to erase.
            force_erase (bool): If True, erase without confirmation.
            confirm (bool): If True, prompt for confirmation.

        Returns:
            bool: True if erased, False otherwise.
        """
        file_path = Path(dir_path) / file_name

        if not os.path.exists(file_path):
            self.logger.warning(
                f"File '{file_name}' does not exist. The file cannot be erased.")
            return False

        if confirm and not force_erase:
            if not util.get_user_confirmation(
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
        """Check if directory exists and all listed files are present.

        Args:
            dir_path (str | Path): Directory path to check.
            files_names_list (List[str]): List of file names to check.

        Returns:
            bool: True if directory and all files exist.

        Raises:
            ModelFolderError: If directory or any file is missing.
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
        """Copy a file from source to destination.

        Args:
            path_destination (str | Path): Destination path.
            path_source (str): Source path.
            file_name (str): Name of the file to copy.
            file_new_name (Optional[str]): New name for the file at destination.
            force_overwrite (bool): If True, overwrite existing file.

        Raises:
            FileNotFoundError: If source file does not exist.
        """
        root_path = Path(__file__).parents[2]
        source_path = Path(root_path) / path_source / file_name
        destination_file_name = file_new_name or source_path.name
        destination_file_path = Path(path_destination) / destination_file_name

        if destination_file_path.exists() and not force_overwrite:
            self.logger.warning(f"'{file_name}' already exists.")
            if not util.get_user_confirmation(f"Overwrite '{file_name}'?"):
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
        """Copy all files and directories from source to destination.

        Args:
            path_source (str | Path): Source directory.
            path_destination (str | Path): Destination directory.
            force_overwrite (bool): If True, overwrite existing content.

        Raises:
            ModelFolderError: If source path does not exist or is not a directory.
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
            if not util.get_user_confirmation(
                f"Overwrite content of '{dir_destination}'?"
            ):
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

    def rename_file(
            self,
            dir_path: str | Path,
            name_old: str,
            name_new: str,
            file_extension: Optional[str] = None,
            force_overwrite: bool = False,
    ) -> None:
        """Rename a file in the specified directory.

        Args:
            dir_path (str | Path): Directory containing the file.
            name_old (str): Current name of the file.
            name_new (str): New name for the file.
            file_extension (Optional[str]): File extension if not included.
            force_overwrite (bool): If True, replace destination if it exists.

        Raises:
            FileNotFoundError: If file does not exist.
            FileExistsError: If new file name already exists.
        """
        dir_path = Path(dir_path)

        if file_extension:
            name_old = f"{name_old}.{file_extension.lstrip('.')}"
            name_new = f"{name_new}.{file_extension.lstrip('.')}"
        else:
            if '.' not in name_old or '.' not in name_new:
                raise ValueError(
                    "File extension must be specified when not included "
                    "in the file name.")

        file_path = dir_path / name_old
        new_file_path = dir_path / name_new

        if not file_path.exists():
            raise FileNotFoundError(f"File '{file_path}' does not exist.")

        if new_file_path.exists() and not force_overwrite:
            raise FileExistsError(
                f"A file named '{name_new}' already exists. Operation aborted.")

        if force_overwrite:
            os.replace(file_path, new_file_path)
        else:
            file_path.rename(new_file_path)

        self.logger.debug(f"File '{name_old}' renamed to '{name_new}'.")

    def dict_to_excel_headers(
            self,
            dict_name: Dict[str, Any],
            excel_dir_path: Path,
            excel_file_name: str,
            writer_engine: Optional[Literal['openpyxl', 'xlsxwriter']] = None,
    ) -> None:
        """Generate an Excel file with sheets named by dictionary keys and headers.

        Args:
            dict_name (Dict[str, Any]): Dictionary with sheet names and column headers.
            excel_dir_path (Path): Directory to save the Excel file.
            excel_file_name (str): Filename for the Excel file.
            writer_engine (Optional[Literal['openpyxl', 'xlsxwriter']]): Excel writing engine.

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
            """Support function to generate excel."""
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
            if not util.get_user_confirmation(
                f"Do you really want to overwrite the file '{excel_file_name}'?"
            ):
                write_excel(excel_file_path, dict_name)
            else:
                self.logger.debug(
                    f"Excel file '{excel_file_name}' not overwritten.")
        else:
            write_excel(excel_file_path, dict_name)

    def dataframe_to_excel(
            self,
            dataframe: pd.DataFrame,
            excel_filename: str,
            excel_dir_path: str,
            sheet_name: Optional[str] = None,
            writer_engine: Optional[Literal['openpyxl', 'xlsxwriter']] = None,
            force_overwrite: bool = False,
    ) -> None:
        """Export a DataFrame to an Excel file.

        Optionally allows overwriting an existing file.

        Args:
            dataframe (pd.DataFrame): DataFrame to export.
            excel_filename (str): Name of the Excel file.
            excel_dir_path (str): Directory to save the Excel file.
            sheet_name (Optional[str]): Name of the sheet.
            writer_engine (Optional[Literal['openpyxl', 'xlsxwriter']]): Excel 
                writing engine.
            force_overwrite (bool): If True, overwrite existing file.

        Raises:
            Warning: If file exists and not overwritten.
        """
        if writer_engine is None:
            writer_engine = self.xls_engine

        excel_file_path = Path(excel_dir_path, excel_filename)

        if not force_overwrite:
            if excel_file_path.exists():
                self.logger.warning(
                    f"Excel file '{excel_filename}' already exists.")
                if not util.get_user_confirmation(
                    f"Do you want to overwrite '{excel_filename}'?"
                ):
                    self.logger.warning(
                        f"File '{excel_filename}' not overwritten.")
                    return

        mode = 'a' if excel_file_path.exists() else 'w'
        if_sheet_exists = 'replace' if mode == 'a' else None

        self.logger.debug(
            f"Exporting dataframe '{sheet_name}' to '{excel_filename}'.")

        if sheet_name is None:
            sheet_name = str(dataframe)

        try:
            with pd.ExcelWriter(
                excel_file_path,
                engine=writer_engine,
                mode=mode,
                if_sheet_exists=if_sheet_exists,
            ) as writer:
                dataframe.to_excel(writer, sheet_name=sheet_name, index=False)
        except Exception as error:
            msg = f"Error exporting DataFrame to excel: {str(error)}"
            self.logger.error(msg)
            raise exc.OperationalError(msg)

    def dataframe_to_csv(
        self,
        dataframe: pd.DataFrame,
        csv_filename: str,
        csv_dir_path: str,
        force_overwrite: bool = False,
    ) -> None:
        """Export a DataFrame to a CSV file.

        Optionally allows overwriting an existing file.

        Args:
            dataframe (pd.DataFrame): DataFrame to export.
            csv_filename (str): Name of the CSV file.
            csv_dir_path (str): Directory to save the CSV file.
            force_overwrite (bool): If True, overwrite existing file.

        Raises:
            Warning: If file exists and not overwritten.
        """
        csv_file_path = Path(csv_dir_path, csv_filename)

        if not force_overwrite:
            if csv_file_path.exists():
                self.logger.warning(
                    f"csv file '{csv_filename}' already exists.")
                if not util.get_user_confirmation(
                    f"Do you want to overwrite '{csv_filename}'?"
                ):
                    self.logger.warning(
                        f"File '{csv_filename}' not overwritten.")
                    return

        self.logger.debug(
            f"Exporting dataframe to '{csv_filename}'.")

        try:
            dataframe.to_csv(csv_file_path, index=False)
        except Exception as error:
            msg = f"Error exporting DataFrame to csv: {str(error)}"
            self.logger.error(msg)
            raise exc.OperationalError(msg)

    def _open_excel_file(
            self,
            excel_file_name: str,
            excel_file_dir_path: Path | str,
    ) -> pd.ExcelFile:
        """Open and return an Excel file object.

        Args:
            excel_file_name (str): Name of the Excel file.
            excel_file_dir_path (Path | str): Directory containing the Excel file.

        Returns:
            pd.ExcelFile: Opened Excel file object.

        Raises:
            FileNotFoundError: If Excel file does not exist.
            OperationalError: If file cannot be opened.
        """
        file_path = Path(excel_file_dir_path, excel_file_name)

        if not os.path.exists(file_path):
            msg = f'{excel_file_name} does not exist.'
            self.logger.error(msg)
            raise FileNotFoundError(msg)

        try:
            return pd.ExcelFile(file_path, engine=self.xls_engine)
        except Exception as error:
            msg = f"Error opening Excel file: {str(error)}"
            self.logger.error(msg)
            raise exc.OperationalError(msg)

    def _parse_excel_sheet(
            self,
            xlsx: pd.ExcelFile,
            sheet_name: str,
    ) -> pd.DataFrame:
        """Parse a single Excel sheet and optionally normalize.

        Args:
            xlsx (pd.ExcelFile): Excel file object.
            sheet_name (str): Name of the sheet to parse.

        Returns:
            pd.DataFrame: Parsed DataFrame.

        Raises:
            OperationalError: If parsing fails.
        """
        try:
            df = xlsx.parse(
                sheet_name=sheet_name,
                keep_default_na=True,
                dtype_backend="python" if hasattr(pd, "options") else None,
            )

        except Exception as e:
            msg = f"Excel parsing error | sheet '{sheet_name}' | {str(e)}"
            self.logger.error(msg)
            raise exc.OperationalError(msg)

        return df

    def _parse_csv_to_dataframe(self, file_path: Path | str,) -> pd.DataFrame:
        """Parse a CSV file and return as a DataFrame.

        Args:
            file_path (Path | str): Path to the CSV file.

        Returns:
            pd.DataFrame: Parsed CSV data as a DataFrame.

        Raises:
            OperationalError: If parsing fails.
        """
        file_path = Path(file_path)

        try:
            dataframe = pd.read_csv(file_path, keep_default_na=True)
        except Exception as error:
            msg = f"CSV parsing error | file '{file_path.name}' | {str(error)}"
            self.logger.error(msg)
            raise exc.OperationalError(msg)

        return dataframe

    def excel_to_dataframes_dict(
            self,
            excel_file_name: str,
            excel_file_dir_path: Path | str,
            sheet_names: Optional[List[str | int]] = None,
    ) -> Dict[str, pd.DataFrame]:
        """Read an Excel file with multiple sheets into a dictionary of DataFrames.

        Args:
            excel_file_name (str): Name of the Excel file.
            excel_file_dir_path (Path | str): Directory containing the Excel file.
            sheet_names (Optional[List[str | int]]): List of sheet names to parse. 
                If None, parses all sheets.
            empty_data_fill (Optional[Any]): Value to fill empty cells.
            set_values_type (bool): If True, set values column type.
            values_normalization (bool): If True, normalize values.

        Returns:
            Dict[str, pd.DataFrame]: Dictionary of DataFrames for each sheet.

        Raises:
            FileNotFoundError: If Excel file does not exist.
            ValueError: If specified sheet names are not found in the file.
        """
        xlsx = self._open_excel_file(excel_file_name, excel_file_dir_path)
        available_sheets = xlsx.sheet_names

        if sheet_names is None:
            sheets_to_parse = available_sheets
        else:
            invalid_sheets = [
                s for s in sheet_names
                if s not in available_sheets
            ]
            if invalid_sheets:
                msg = (
                    f"Sheet(s) {invalid_sheets} not found in '{excel_file_name}' | "
                    f"Available sheets: {available_sheets}"
                )
                self.logger.error(msg)
                raise ValueError(msg)

            sheets_to_parse = sheet_names

        df_dict: Dict[str, pd.DataFrame] = {}

        for sheet in sheets_to_parse:
            df_dict[sheet] = self._parse_excel_sheet(
                xlsx=xlsx, sheet_name=sheet)

        return df_dict

    def file_to_dataframe(
            self,
            file_name: str,
            file_dir_path: Path | str,
    ) -> pd.DataFrame:
        """Load data from a file into a DataFrame.

        Args:
            file_name (str): Name of the file to load.
            file_dir_path (Path | str): Directory containing the file.

        Returns:
            pd.DataFrame: Loaded DataFrame.
        """
        file_path = Path(file_dir_path) / file_name

        if not file_path.exists():
            msg = f"File '{file_name}' does not exist."
            self.logger.error(msg)
            raise FileNotFoundError(msg)

        file_extension = file_path.suffix.lower().lstrip('.')
        file_base_name = file_path.stem

        if file_extension == 'xlsx':
            df_dict = self.excel_to_dataframes_dict(
                excel_file_name=file_name,
                excel_file_dir_path=file_dir_path,
                sheet_names=[file_base_name],
            )
            dataframe = df_dict[file_base_name]

        elif file_extension == 'csv':
            dataframe = self._parse_csv_to_dataframe(file_path)

        else:
            msg = f"Unsupported file extension '{file_extension}'."
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        return dataframe

    def load_data_structure(
            self,
            structure_key: str,
            source: str,
            dir_path: Path | str,
    ) -> Dict:
        """Load a data structure from YAML or Excel source.

        Args:
            structure_key (str): Key for the structure to load.
            source (str): Source type ('yml' or 'xlsx').
            dir_path (Path | str): Directory containing the source file.

        Returns:
            Dict: Loaded data structure.

        Raises:
            SettingsError: If file or tab is empty or source not recognized.
        """
        available_sources = Defaults.ConfigFiles.AVAILABLE_SETUP_SOURCES

        util.validate_selection(
            selection=source,
            valid_selections=available_sources
        )

        if source == 'yml':
            file_name = structure_key + '.yml'
            data = self.load_structured_file(file_name, dir_path)

            if not data:
                msg = f"File '{file_name}' is empty."
                self.logger.error(msg)
                raise exc.SettingsError(msg)

        elif source == 'xlsx':
            file_name = Defaults.ConfigFiles.SETUP_XLSX_FILE
            raw_data_dict = self.excel_to_dataframes_dict(
                excel_file_name=file_name,
                excel_file_dir_path=dir_path,
                sheet_names=[structure_key],
            )

            raw_data = raw_data_dict[structure_key]
            raw_data = util.normalize_dataframe(
                df=raw_data,
                replace_nans=True,
            )

            if raw_data.empty:
                msg = f"Excel tab '{structure_key}' is empty."
                self.logger.error(msg)
                raise exc.SettingsError(msg)

            data_pivot_keys = Defaults.DefaultStructures.XLSX_PIVOT_KEYS
            merge_dict = True if \
                structure_key == Defaults.ConfigFiles.SETUP_INFO[2] else False

            skip_process_str = True if structure_key == 'problem' else False

            data = util.pivot_dataframe_to_data_structure(
                data=raw_data,
                primary_key=data_pivot_keys[structure_key][0],
                secondary_key=data_pivot_keys[structure_key][1],
                merge_dict=merge_dict,
                skip_process_str=skip_process_str,
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
        """Validate a data structure against a validation schema.

        Args:
            data (Dict): Data structure to validate.
            validation_structure (Dict): Validation schema.
            path (str, optional): Path for nested validation.

        Returns:
            Dict[str, str]: Dictionary of problems found.
        """
        errors = {}
        optional_label = Defaults.DefaultStructures.OPTIONAL
        any_label = Defaults.DefaultStructures.ANY

        all_optional_fields = all(
            isinstance(v_exp, tuple) and v_exp[0] == optional_label
            for v_exp in validation_structure.values()
        )

        for k_exp, v_exp in validation_structure.items():
            current_path = f"{path}.{k_exp}" if path else k_exp

            # if no data are passed, all keys must be optional
            if not data:
                if not all_optional_fields:
                    errors[current_path] = f"Data structure is empty, but " \
                        "there are mandatory key-value pairs."
                continue

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
                if not optional:
                    errors[current_path] = f"Missing key-value pair."
                continue

            # check values types and content for mandatory keys
            else:
                value = data[k_exp]

                if isinstance(expected_value, type):
                    if not isinstance(value, expected_value | NoneType):
                        errors[current_path] = \
                            f"Expected {expected_value}, got {type(value)}"
                    if not optional and not value:
                        errors[current_path] = "Empty value."

                elif isinstance(expected_value, tuple):
                    if all(isinstance(v, type) for v in expected_value):
                        if not any(isinstance(value, v | NoneType) for v in expected_value):
                            errors[current_path] = \
                                f"Expected {expected_value}, got {type(value)}"
                        if not optional and not value:
                            errors[current_path] = "Empty value."

                # check for nested dictionaries
                elif isinstance(expected_value, dict):
                    if isinstance(value, dict):
                        errors.update(
                            self.validate_data_structure(
                                value, expected_value, current_path)
                        )
                    else:
                        errors[current_path] = \
                            f"Expected dict, got {type(value).__name__}"

                else:
                    errors[current_path] = "Unexpected value."

        # in case data is empty, no further checks required
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key

                if key not in validation_structure:

                    # check for unexpected keys
                    if any_label not in validation_structure:
                        errors[current_path] = f"Unexpected key '{key}'. Valid keys: " \
                            f"{list(validation_structure)}."

                    # check for nested dictionaries
                    else:
                        if isinstance(validation_structure[any_label], tuple) \
                                and validation_structure[any_label][0] == optional_label:
                            expected_value = validation_structure[any_label][1]
                        else:
                            expected_value = validation_structure[any_label]

                        if isinstance(value, dict):
                            errors.update(
                                self.validate_data_structure(
                                    value, expected_value, current_path)
                            )

        errors = util.remove_empty_items_from_dict(
            errors, empty_values=[{}])

        return errors

    def save_dataframe(
        self,
        dataframe: pd.DataFrame,
        output_path: Path | str,
        file_format: str,
        index: bool = False,
    ) -> Path:
        """Save a dataframe to the specified file path.

        Args:
            dataframe: DataFrame to save.
            output_path: Destination path, including the file name.
            file_format: Output format, such as ``xlsx``, ``csv``, or
                ``parquet``.
            index: Whether to save the dataframe index. Defaults to False.

        Returns:
            Path: Path of the saved file.

        Raises:
            ValueError: If the selected file format is unsupported.
        """
        output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        file_format = file_format.lower().strip()

        supported_formats = (
            Defaults.UncertaintySettings.AVAILABLE_EXPORT_FORMATS
        )

        if file_format not in supported_formats:
            raise ValueError(
                f"Unsupported dataframe format '{file_format}'. "
                f"Available formats: {supported_formats}."
            )

        if file_format == "xlsx":
            dataframe.to_excel(
                output_path,
                index=index,
                engine=self.xls_engine,
            )
        elif file_format == "csv":
            dataframe.to_csv(
                output_path,
                index=index,
            )
        elif file_format == "parquet":
            dataframe.to_parquet(
                output_path,
                index=index,
            )

    def __repr__(self):
        """Return string representation of FileManager instance."""
        class_name = type(self).__name__
        return f'{class_name}'
