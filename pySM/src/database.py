import os
import warnings
import shutil
import pandas as pd

from pathlib import Path


class Database:

    def __init__(
            self,
            model_folder_path: str,
            sets: dict,
            clean_database: bool,
            generate_sets_file: bool) -> None:
        """Initializes the Database of the model.

        Args:
            model_folder_path (str): path of the model database folder.
            sets (dict): dictionary of the model sets.
            clean_database (bool): True for erasing the existing database.
            generate_sets_file (bool): True for generating a new database
        """

        self.model_folder_path = model_folder_path
        self.sets = sets

        if clean_database:
            self.erase_database()

        if generate_sets_file:
            self.generate_blank_sets(
                dict_to_export=self.sets,
                excel_file_name='sets.xlsx'
            )

    def erase_database(self):
        """Erases the database in the model folder.
        """
        response = input(f"Do you really want to erase the directory \
                        '{self.model_folder_path}' and all its contents? (y/[n]): ")
        if response.lower() != 'y':
            print("Operation cancelled.")
            return
        try:
            shutil.rmtree(self.model_folder_path)
        except OSError as e:
            print(f"Error: {self.model_folder_path} : {e.strerror}")
        else:
            print(f"All files and folders in {self.model_folder_path} \
                have been erased successfully.")

    def generate_blank_sets(
            self,
            dict_to_export: dict,
            excel_file_name: str,
            excel_data_validation: bool = True,
            dict_headers_name: str = 'Headers',
            writer_engine: str = 'openpyxl') -> None:
        """Generates excel file with headers defined by a dictionary.
        Excel columns can be implemented with data validation.

        Args:
            dict_to_export (dict): dictionary to be exported.
            excel_file_name (str): file name of the sets Excel file.
            excel_data_validation (bool, optional): add data validation to 
                Excel file. Defaults to True.
            dict_headers_name (str, optional): name of headers in the dictionary. 
                Defaults to 'Headers'.
            writer_engine (str, optional): defines writer engines for Pandas. 
                Defaults to 'openpyxl'.
        """

        file_path = Path(self.model_folder_path) / excel_file_name
        if os.path.exists(file_path):
            warning_msg = f'File {excel_file_name} already exists and not overwritten.'
            warnings.warn(warning_msg, UserWarning)
            return

        os.makedirs(self.model_folder_path, exist_ok=True)

        with pd.ExcelWriter(file_path, engine=writer_engine) as writer:
            for sheet_name, value in dict_to_export.items():
                pd.DataFrame(columns=value[dict_headers_name]).to_excel(
                    writer, sheet_name=sheet_name, index=False)

    # def load_excel(
    #         self,
    #         sets_dict,
    #         sets_dir_path,
    #         sets_file_name):

    #     file_path = os.path.join(sets_dir_path, sets_file_name)

    #     if not os.path.exists(file_path):
    #         raise FileNotFoundError(f"{sets_file_name} does not exist.")

    #     sets_dict_data = sets_dict.copy()
    #     for sheet_name in sets_dict.keys():
    #         sets_dict_data[sheet_name] = pd.read_excel(file_path, sheet_name)
    #     return sets_dict_data


if __name__ == '__main__':
    pass
