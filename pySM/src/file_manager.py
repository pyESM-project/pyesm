import os
import json
import yaml
import warnings
import pandas as pd

from pathlib import Path
from pySM.src import util


class FileManager:

    def __init__(
            self,
            folder_path: str = Path(
                __file__).resolve().parent.parent / 'interface'):
        """Initialize an instance of FileManager object with a path to
           interface folder.

        Args:
            folder_path (str, optional): default interface folder.
        """
        self.folder_path = folder_path

    def load_file(
            self,
            file_name: str,
            file_type: str = 'json',
            folder_path: str = None) -> dict:
        """Loads JSON or YAML file and returns a dictionary with its content.

        Args:
            file_name (str): file name to be loaded.
            file_type (str): file type (only .json or .yaml allowed)
            folder_path (str, optional): The path to the folder where the file 
                is located. If None, the default path of the FileManager 
                instance is used.

        Raises:
            ValueError: If the file_type argument is not 'json' or 'yaml'.
            ValueError: If the file format is incorrect or the file cannot be loaded.

        Returns:
            dict: a dictionary containing the data from the file.
        """
        if folder_path is None:
            folder_path = self.folder_path

        if file_type == 'json':
            loader = json.load
        elif file_type == 'yaml':
            loader = yaml.safe_load
        else:
            raise ValueError(
                'Invalid file type. Only JSON and YAML are allowed.')

        file_path = Path(folder_path) / file_name

        with file_path.open() as file:
            try:
                return loader(file)
            except ValueError as error:
                raise ValueError(
                    f'Error loading {file_type} file: wrong file format'
                ) from error

    def load_excel(
            self,
            sets_dict,
            sets_dir_path,
            sets_file_name):
        """Load EXCEL files and returns a dictionary with their content.

        Args:
            sets_dict (_type_): _description_
            sets_dir_path (_type_): _description_
            sets_file_name (_type_): _description_

        Raises:
            FileNotFoundError: _description_

        Returns:
            _type_: _description_
        """
        file_path = os.path.join(sets_dir_path, sets_file_name)

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"{sets_file_name} does not exist.")

        sets_dict_data = sets_dict.copy()
        for sheet_name in sets_dict.keys():
            sets_dict_data[sheet_name] = pd.read_excel(file_path, sheet_name)
        return sets_dict_data

    def dict_to_excel(
            self,
            sets_dict,
            sets_dir_path,
            sets_file_name):
        """Generates excel files from a dictionary"""

        file_path = os.path.join(sets_dir_path, sets_file_name)

        if os.path.exists(file_path):
            warnings.warn(f"Excel file '{sets_file_name}' already exists.")
            return

        with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
            for sheet_name, value in sets_dict.items():
                pd.DataFrame(columns=value['Headers']).to_excel(
                    writer, sheet_name=sheet_name, index=False)


if __name__ == '__main__':

    from pySM.src.file_manager import FileManager

    fm = FileManager()
    file_content = fm.load_file(
        file_name='case_config.json', file_type='json')

    util.find_dict_depth
