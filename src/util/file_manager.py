import os
import shutil
import json
import yaml
import pandas as pd

from typing import List, Dict
from pathlib import Path
from log.logger import Logger


class FileManager:

    def __init__(self, logger: Logger) -> None:
        self.logger = logger.getChild(__name__)
        self.logger.debug(f"'{self}' object generated.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def create_dir(self, dir_path: Path) -> None:
        """This method receives a folder path and generates the folder in case
        it not exists.

        Args:
            dir_path (str): path of the folder to be generated.
        """

        dir_name = str(dir_path).rsplit('\\', maxsplit=1)[-1]

        if os.path.exists(dir_path):
            self.logger.warning(f"Folder '{dir_name}' already exists.")
            return {}
        else:
            os.makedirs(dir_path, exist_ok=True)
            self.logger.debug(f"Folder '{dir_name}' has created.")

    def erase_dir(self, dir_path: Path) -> None:
        """This method erases a folder and its content in a given path.

        Args:
            folder_path (str): path of the folder to be deleted.
        """
        if os.path.exists(dir_path):
            dir_name = str(dir_path).rsplit('\\', maxsplit=1)[-1]
            response = input(
                'Do you really want to erase the directory '
                f"'{dir_name}'(y/[n]): "
            ).lower()

            if response != 'y':
                self.logger.warning(
                    f"Folder '{dir_name}' and its content not erased.")
                return {}

            try:
                shutil.rmtree(dir_path)
            except OSError as error:
                self.logger.error(f"Error: '{dir_name}' : {error.strerror}")
            else:
                self.logger.warning(f"Folder '{dir_name}' have been erased.")

        else:
            self.logger.warning(
                f"Folder '{dir_name}' does not exist. The folder cannot be erased.")

    def load_file(
            self,
            file_name: str,
            dir_path: Path,
            file_type: str = 'yaml') -> Dict[str, any]:
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
        elif file_type == 'yaml':
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

    def dict_to_excel(
            self,
            dict_name: Dict[str, any],
            excel_dir_path: Path,
            excel_file_name: str = "",
            table_key: str = "",
            table_key_dict_depth: int = 0,
            writer_engine: str = 'openpyxl',
    ) -> None:
        """Generates an excel file with information provided by a dictionary.
        """

        if not isinstance(dict_name, Dict):
            self.logger.error(f'{dict_name} is not a dictionary.')

        def write_excel(excel_file_path, dict_name):
            """Support function to generate excel"""
            with pd.ExcelWriter(excel_file_path, engine=writer_engine) as writer:
                for sheet_name, value in dict_name.items():
                    if table_key is None:
                        columns_data = value
                    else:
                        if isinstance(value[table_key], List):
                            columns_data = value[table_key]
                        elif isinstance(value[table_key], Dict):
                            columns_data = [
                                value[table_key][key][table_key_dict_depth]
                                for key in value[table_key]
                            ]
                        else:
                            self.logger.error(
                                f"Invalid table_key '{table_key}'.")

                    dataframe = pd.DataFrame(columns=columns_data)
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

    def excel_to_dataframes_dict(
            self,
            excel_file_name: str,
            excel_file_dir_path: Path,
            empty_data_fill: str,
    ) -> Dict[str, pd.DataFrame]:
        """Reading an excel file composed by multiple tabs and returning
        a dictionary with keys as tabs and tables in each tab as Pandas 
        DataFrames.
        """

        file_path = Path(excel_file_dir_path, excel_file_name)

        if not os.path.exists(file_path):
            self.logger.error(f'{excel_file_name} does not exist.')
            raise FileNotFoundError(f"{excel_file_name} does not exist.")

        df_dict = pd.read_excel(io=file_path, sheet_name=None)
        df_dict = {sheet_name: df.fillna(empty_data_fill)
                   for sheet_name, df in df_dict.items()}

        self.logger.debug(f"Excel file '{excel_file_name}' loaded.")
        return df_dict

    # def dataframes_dict_to_excel(self):
    #     # self.logger.debug(f"Excel file '{}' loaded.")
    #     pass
