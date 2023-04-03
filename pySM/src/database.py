from pathlib import Path
from pySM.log_exc.logger import Logger
from pySM.src.file_manager import FileManager


class Database:
    """Generation and handling of the model database."""

    def __init__(
            self,
            logger: 'Logger',
            files: 'FileManager',
            model_folder_path: str,
            sets: dict,
            generate_sets_file: bool = False) -> None:
        """Initializes the Database of the model.

        Args:
            sets (dict): sets dictionary (constant)
            model_folder_path (str): path of the model database folder
            generate_sets_file (bool, optional): if the sets.xlsx file must
                be generated. Defaults to False.
        """
        self.logger = logger.getChild(__name__)
        self.logger.info('Generation of Database object...')
        self.files = files
        self.model_folder_path = model_folder_path
        self.sets = sets

        if generate_sets_file:
            self.generate_blank_sets(
                dict_to_export=self.sets,
                excel_file_name='sets.xlsx'
            )

        self.logger.info('Database generated.')

    def generate_blank_sets(
            self,
            dict_to_export: dict,
            excel_file_name: str) -> None:
        """Generates excel file with headers defined by a dictionary.

        Args:
            dict_to_export (dict): dictionary with sets headers to be exported.
            excel_file_name (str): file name for the set file.
        """

        self.files.erase_folder(self.model_folder_path)
        self.files.create_folder(self.model_folder_path)
        self.files.generate_excel_headers(
            dict_name=dict_to_export,
            excel_file_path=Path(self.model_folder_path) / excel_file_name
        )

    def load_sets(self) -> dict:
        self.logger.info('Sets loaded.')
        pass
