from pathlib import Path
from pySM.src import constants
from pySM.src import util
from pySM.src.database import Database
from pySM.src.problem import Problem
from pySM.log_exc.logger import Logger
from pySM.src.file_manager import FileManager


class Model:

    def __init__(
            self,
            logger: Logger,
            model_settings: dict,
            generate_sets_file: bool = True) -> None:

        self.logger = logger.getChild(__name__)
        self.model_settings = model_settings

        self.model_dir_path = \
            Path(self.model_settings['model data folder path']) / \
            self.model_settings['model name']

        self.files = FileManager(logger=self.logger)
        self.files.create_folder(self.model_dir_path)

        self.logger.info('Generation of new Model instance')
        self.logger.info('Model settings loaded.')

        self.database = Database(
            model_folder_path=self.model_dir_path,
            sets=constants._SETS,
            generate_sets_file=generate_sets_file,
            logger=self.logger
        )

        self.problem = Problem(
            logger=self.logger
        )


if __name__ == '__main__':
    pass
