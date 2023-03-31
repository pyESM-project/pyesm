from pathlib import Path
from pySM.src import constants
from pySM.log_exc.logger import Logger
from pySM.src.file_manager import FileManager
from pySM.src.database import Database
from pySM.src.problem import Problem


class Model:

    def __init__(
            self,
            logger: 'Logger',
            files: 'FileManager',
            model_settings: dict,
            generate_sets_file: bool) -> None:

        self.logger = logger.getChild(__name__)
        self.files = files
        self.model_settings = model_settings

        self.model_dir_path = \
            Path(self.model_settings['model data folder path']) / \
            self.model_settings['model name']

        # solo se non esiste già
        self.files.create_folder(self.model_dir_path)

        self.logger.info('Generation of new Model instance')

        self.database = Database(
            logger=self.logger,
            files=self.files,
            model_folder_path=self.model_dir_path,
            sets=constants._SETS,
            generate_sets_file=generate_sets_file,
        )

        self.problem = Problem(
            logger=self.logger
        )
