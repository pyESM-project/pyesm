from typing import Dict
from pathlib import Path
from util import constants
from util.database_sql import DatabaseSQL
from log.logger import Logger
from util.file_manager import FileManager


class Database:

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            database_dir_path: Path,
            database_settings: Dict[str, str],
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info(f"Generation of '{self}' object.")

        self.files = files

        self.database_dir_path = database_dir_path
        self.database_settings = database_settings

        self.sets_structure = constants._SETS
        self.sets = None

        if self.database_settings['generate_blank_sets']:
            self.files.dict_to_excel(
                dict_name=self.sets_structure,
                excel_dir_path=database_dir_path,
                excel_file_name=self.database_settings['sets_file_name'],
                table_key='table_headers',
            )
        
        if self.database_settings['generate_database_sql']:
            self.generate_database_sql(
                database_sql_name=self.database_settings['database_sql_name'],
            )

        self.logger.info(f"'{self}' object initialized.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def generate_database_sql(
            self,
            database_sql_name: str ='database.db',
    ) -> None:

        self.database_sql_name = database_sql_name
        self.database_sql_path = Path(self.database_dir_path, database_sql_name)
        
        self.database_sql = DatabaseSQL(
            logger=self.logger,
            database_sql_path=self.database_sql_path,
        )

        for table in self.sets_structure:
            self.database_sql.create_table(
                table_name=self.sets_structure[table]['table_name'],
                table_fields=self.sets_structure[table]['table_headers']
            )