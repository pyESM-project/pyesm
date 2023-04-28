import sqlite3
import datetime

from pySM.util import constants
from pathlib import Path
from pySM.log_exc.logger import Logger
from pySM.util.file_manager import FileManager


class Database:

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            database_dir_path: str,
            database_name: str,
            database_settings: dict,
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info(f"Generation of '{str(self)}' object.")

        self.files = files

        database_path = Path(database_dir_path, database_name)
        self.connection = sqlite3.connect(f'{database_path}')
        self.cursor = self.connection.cursor()

        self.sets_structure = constants._SETS

        for table in self.sets_structure:
            self.create_table(
                table_name='_set_' + table,
                table_fields=self.sets_structure[table]['Headers']
            )

        self.close_connection()

        if database_settings['generate_excel_blank_sets'] == True:
            self.files.dict_to_excel(
                dict_name=self.sets_structure,
                excel_dir_path=database_dir_path,
                excel_file_name='sets.xlsx',
                table_key='Headers',
            )

        self.logger.info(f"'{str(self)}' object initialized.")

    def __str__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def create_table(
            self,
            table_name: str,
            table_fields: dict,
    ):
        fields_str = ", ".join(
            [f'{field_name} {field_type}'
             for field_name, field_type in table_fields.items()]
        )

        query = f'CREATE TABLE IF NOT EXISTS {table_name}({fields_str})'

        try:
            self.cursor.execute(query)
            self.connection.commit()
            self.logger.debug(f'Table {table_name} created.')
        except sqlite3.OperationalError as error_msg:
            self.logger.error(error_msg)
            raise sqlite3.OperationalError(error_msg)

    def close_connection(self):
        self.connection.close()
        self.logger.debug(f"'{str(self)}' connection closed.")

    # def load_sets(self) -> dict:
    #     """Loading sets file data previously filled by the user."""
    #     if self.sets is None:
    #         self.sets = self.files.excel_to_dataframes_dict(
    #             excel_file_name=self.sets_file_name,
    #             excel_file_dir_path=self.model_folder_path)

    # def generate_blank_rps(self) -> None:
    #     """Generating blank rps files to be filled by the user."""
    #     self.files.dataframes_dict_to_excel()
