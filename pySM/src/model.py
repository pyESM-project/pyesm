from pathlib import Path
from pySM.src import constants
from pySM.src import util
from pySM.src.database import Database
from pySM.src.problem import Problem
from pySM.log_exc.logger import Logger


class Model:
    """Initialization and management of the model."""

    file_settings_dir_path = \
        Path(__file__).resolve().parent.parent / 'interface'

    def __init__(
            self,
            file_settings_name: str,
            generate_sets_file: bool,
            file_settings_dir_path: str = file_settings_dir_path) -> None:

        self.model_settings = util.load_file(
            file_name=file_settings_name,
            folder_path=file_settings_dir_path
        )

        self.model_dir_path = \
            Path(self.model_settings['model data folder path']) / \
            self.model_settings['model name']

        self.logger = Logger(
            logger_name=__name__,
            log_level=self.model_settings['logging']['log level'].upper(),
            log_file_path=self.model_dir_path /
            self.model_settings['logging']['file name']
        )

        self.logger.info('Settings loaded.')

        self.database = Database(
            model_folder_path=self.model_dir_path,
            sets=constants._SETS,
            generate_sets_file=generate_sets_file,
            logger=self.logger
        )

        self.logger.info('Database generated.')

        self.problem = Problem(
            logger=self.logger
        )

        self.logger.info('Numerical problem defined.')


if __name__ == '__main__':
    pass
