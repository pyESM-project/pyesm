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
        self.logger.info('Generation of new Model object...')
        self.files = files
        self.model_settings = model_settings

        self.model_dir_path = \
            Path(self.model_settings['model data folder path']) / \
            self.model_settings['model name']

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

        self.logger.info('Model object generated.')

    def model_cleanup(self):
        self.files.erase_folder(self.model_dir_path)