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
            sets_structure: dict,
            generate_sets_file: bool = False) -> None:
        """Initializes the Database of the model.

        Args:
            sets (dict): sets dictionary (constant)
            model_folder_path (str): path of the model database folder
            generate_sets_file (bool, optional): if the sets.xlsx file must
                be generated. Defaults to False.
        """
        self.logger = logger.getChild(__name__)
        self.logger.info(f"Generation of '{str(self)}' object...")
        self.files = files
        self.model_folder_path = model_folder_path
        self.sets_file_name = 'sets.xlsx'
        self.sets_structure = sets_structure
        self.sets = None

        if generate_sets_file:
            self.generate_blank_sets(dict_to_export=self.sets_structure)

        self.logger.info(f"'{str(self)}' object generated.")

    def __str__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def generate_blank_sets(
            self,
            dict_to_export: dict) -> None:
        """Generates excel file with headers defined by a dictionary.

        Args:
            dict_to_export (dict): dictionary with sets headers to be exported.
            excel_file_name (str): file name for the set file.
        """

        self.files.create_folder(self.model_folder_path)
        self.files.generate_excel_headers(
            dict_name=dict_to_export,
            excel_file_path=Path(self.model_folder_path) / self.sets_file_name
        )

    def load_sets(self) -> dict:
        """Loading sets file data previously filled by the user."""
        if self.sets is None:
            self.sets = self.files.excel_to_dataframes_dict(
                excel_file_name=self.sets_file_name,
                excel_file_dir_path=self.model_folder_path)

    def generate_blank_rps(self) -> None:
        """Generating blank rps files to be filled by the user."""
        self.files.dataframes_dict_to_excel()
