import os
import shutil
import warnings
import pandas as pd
from pySM.log_exc.logger import Logger


class FileManager:

    def __init__(self, logger: Logger) -> None:
        self.logger = logger.getChild(__name__)

    def erase_folder(self, folder_path: str) -> None:
        """This method erases a folder and its content in a given path.

        Args:
            folder_path (str): path of the folder to be deleted.
        """

        if os.path.exists(folder_path):
            response = input(
                'Do you really want to erase the directory'
                f"'{folder_path}'(y/[n]): "
            ).lower()

            if response != 'y':
                self.logger.info(f'{folder_path} erased.')
                return

            try:
                shutil.rmtree(folder_path)
            except OSError as e:
                self.logger.info(f'Error: {folder_path} : {e.strerror}')
            else:
                self.logger.info(f'{folder_path} have been erased.')

        else:
            warnings.warn(
                f"{folder_path} does not exist. The folder could not be erased.")

    def generate_excel_headers(
            self,
            dict_name: dict,
            excel_file_path: str,
            dict_headers_category_name: str = 'Headers',
            writer_engine: str = 'openpyxl') -> None:
        """This method generates an excel file with headers provided by a dictionary.

        Args:
            dict_name (dict): dictionary of dictionaries with headers to be 
                exported in Excel.
            excel_file_path (str): complete Excel file path.
            dict_headers_category_name (str, optional): name of the header keys. 
                Defaults to 'Headers'.
            writer_engine (str, optional): Pandas writer engine. 
                Defaults to 'openpyxl'.
        """

        with pd.ExcelWriter(excel_file_path, engine=writer_engine) as writer:
            for sheet_name, value in dict_name.items():
                df = pd.DataFrame(columns=value[dict_headers_category_name])
                sheet = writer.book.create_sheet(sheet_name)
                writer.sheets[sheet_name] = sheet
                df.to_excel(
                    writer,
                    sheet_name=sheet_name,
                    index=False
                )

    def load_excel(
            self,
            sets_dict,
            sets_dir_path,
            sets_file_name):

        file_path = os.path.join(sets_dir_path, sets_file_name)

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"{sets_file_name} does not exist.")

        sets_dict_data = sets_dict.copy()
        for sheet_name in sets_dict.keys():
            sets_dict_data[sheet_name] = pd.read_excel(file_path, sheet_name)
        return sets_dict_data
