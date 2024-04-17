from typing import List, Dict, Any, Optional
from pathlib import Path

import os
import shutil
import json
import yaml

import pandas as pd

from esm.log_exc import exceptions as exc
from esm.log_exc.logger import Logger
from esm.support import util


class FileManager:

    def __init__(
        self,
        logger: Logger,
        xls_engine: Optional[str] = None,
    ) -> None:

        self.logger = logger.getChild(__name__)

        if not xls_engine:
            self.xls_engine: str = 'openpyxl'
        else:
            self.xls_engine: str = xls_engine

        self.logger.debug(f"'{self}' object generated.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def create_dir(
            self,
            dir_path: Path,
            force_overwrite: bool = False,
    ) -> None:
        """This method receives a folder path and generates the folder in case
        it does not exist.

        Args:
            dir_path (str): path of the folder to be generated.

        Returns:
            bool: True if the directory was erased, False otherwise.
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
        """This method erases a directory and its content in a given path.

        Args:
            dir_path (str): path of the directory to be deleted.
            force_erase (bool, optional): Forcefully erase the file without
                asking. Defaults to False.
        """
        if os.path.exists(dir_path):
            dir_name = str(dir_path).rsplit('\\', maxsplit=1)[-1]

            if not force_erase:
                response = input(
                    'Do you really want to erase the directory '
                    f"'{dir_name}'(y/[n]): "
                ).lower()

                if response != 'y':
                    self.logger.info(
                        f"Directory '{dir_name}' and its content not erased.")
                    return False

            try:
                shutil.rmtree(dir_path)
            except OSError as error:
                self.logger.error(f"Error: '{dir_name}' : {error.strerror}")
                return False
            else:
                self.logger.info(f"Directory '{dir_name}' have been erased.")
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
        """Loads JSON or YAML file and returns a dictionary with its content.

        Args:
            file_name (str): file name to be loaded.
            file_type (str): file type (only .json or .yaml allowed)
            dir_path (str, optional): The path to the folder where the file
                is located. If None, the default path of the FileManager
                instance is used.

        Raises:
            ValueError: If the file_type argument is not 'json' or 'yaml'.
            ValueError: If the file format is incorrect or the file cannot be loaded.

        Returns:
            dict: a dictionary containing the data from the file.
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
        """Erase a file in a given path with an option to confirm before erasing.

        Args:
            dir_path (Path or str): Path of the directory of the file.
            file_name (str): Name of the file to be erased.
            force_erase (bool, optional): Forcefully erase the file without
                asking. Defaults to False.
            confirm (bool, optional): Ask for user confirmation before erasing.
                Defaults to True.

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
        Copy a file from the specified package folder to a specified 
        destination path, with an optional new file name.

        Args:
            destination_path (str or Path): The path where the file will 
                be copied.
            file_position (str): The package folder position.
            file_name (str): The name of the file to be copied.
            new_file_name (str, optional): The new name for the file. 
                Defaults to None.

        Raises:
            FileNotFoundError: If the source file is not found.
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
            self.logger.debug(f"File '{file_name}' successfully generated.")
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
        except Exception as msg:
            self.logger.error(f"Error copying items: {msg}")

    def dict_to_excel_headers(
            self,
            dict_name: Dict[str, Any],
            excel_dir_path: Path,
            excel_file_name: str,
            writer_engine: str = 'openpyxl',
    ) -> None:
        """Generates an excel file with headers provided by a dictionary in a 
        specified dictionary depth. In case the headers key item is a list, 
        select the list_item to be used.
        """

        if not isinstance(dict_name, Dict):
            error_msg = f"{dict_name} is not a dictionary."
            self.logger.error(error_msg)
            raise TypeError(error_msg)

        def write_excel(
                excel_file_path: str | Path,
                dict_name: Dict[str, Any]
        ) -> None:
            """Support function to generate excel"""
            with pd.ExcelWriter(excel_file_path, engine=writer_engine) as writer:
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
            sheet_name: str = None,
    ) -> None:

        excel_file_path = Path(excel_dir_path, excel_filename)

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
            f"Exporting dataframe {sheet_name} to {excel_filename}.")

        if sheet_name is None:
            sheet_name = str(dataframe)

        with pd.ExcelWriter(
            excel_file_path,
            engine=self.xls_engine,
            mode=mode,
            if_sheet_exists=if_sheet_exists,
        ) as writer:
            dataframe.to_excel(writer, sheet_name=sheet_name, index=False)

    def excel_to_dataframes_dict(
            self,
            excel_file_name: str,
            excel_file_dir_path: Path | str,
            empty_data_fill: str = '',
            dtype: Optional[type[str]] = None,
    ) -> Dict[str, pd.DataFrame]:
        """Reading an excel file composed by multiple tabs and returning
        a dictionary with keys as tabs and tables in each tab as Pandas 
        DataFrames.
        """

        file_path = Path(excel_file_dir_path, excel_file_name)

        if not os.path.exists(file_path):
            self.logger.error(f'{excel_file_name} does not exist.')
            raise FileNotFoundError(f"{excel_file_name} does not exist.")

        df_dict = pd.read_excel(io=file_path, sheet_name=None, dtype=dtype)
        df_dict = {sheet_name: df.fillna(empty_data_fill)
                   for sheet_name, df in df_dict.items()}

        self.logger.debug(f"Excel file '{excel_file_name}' loaded.")
        return df_dict
