import os
import json
import yaml
import warnings
import pandas as pd

from pathlib import Path


class FileManager:

    package_folder_path = Path(__file__).resolve().parent.parent / 'interface'

    def load_file(
            file_name: str,
            file_type: str = 'json',
            folder_path: str = package_folder_path
            ) -> dict:
        """Load file in json format and returns a dictionary

        Args:
            file_name (str): file name to be loaded.
            file_type (str): file type (only .json or .yaml allowed)
            folder_path (str, optional): package folder set as default.

        Returns:
            dict: a dictionary containing the data from the file.
        """

        if file_type == 'json':
            loader = json.load
        elif file_type == 'yaml':
            loader = yaml.safe_load
        else:
            raise ValueError('Invalid file type. Only .json and .yaml are allowed.')

        path_file = folder_path / file_name

        with path_file.open() as file:
            try:
                return loader(file)
            except ValueError as error:
                raise ValueError(
                    f'Error loading {file_type} file: wrong file format'
                    ) from error


            

    def generate_excel_empty_sets(
            self,
            sets_dict,
            sets_dir_path,
            sets_file_name):
        """Generate input data file with sets structure."""
        file_path = os.path.join(sets_dir_path, sets_file_name)

        if os.path.exists(file_path):
            warnings.warn(f"Excel file '{sets_file_name}' already exists.")
            return

        with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
            for sheet_name, value in sets_dict.items():
                pd.DataFrame(columns=value['Headers']).to_excel(
                    writer, sheet_name=sheet_name, index=False)

    def read_excel_sets_data(
            self,
            sets_dict,
            sets_dir_path,
            sets_file_name):
        """Read input data from an Excel file."""
        file_path = os.path.join(sets_dir_path, sets_file_name)

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"{sets_file_name} does not exist.")

        sets_dict_data = sets_dict.copy()
        for sheet_name in sets_dict.keys():
            sets_dict_data[sheet_name] = pd.read_excel(file_path, sheet_name)
        return sets_dict_data


if __name__ == '__main__':

    from pySM.src.file_manager import FileManager as fm

    fm.load_file('case_config.json')
    