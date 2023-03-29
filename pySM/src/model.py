from pathlib import Path

from pySM.src import constants
from pySM.src import util
from pySM.src.database import Database
from pySM.src.problem import Problem


class Model:

    file_settings_dir_path = \
        Path(__file__).resolve().parent.parent / 'interface'

    def __init__(
            self,
            file_settings_name: str,
            file_settings_dir_path: str = file_settings_dir_path,
            clean_database: bool = False,
            generate_sets_file: bool = False) -> None:

        self.model_settings = util.load_file(
            file_name=file_settings_name,
            folder_path=file_settings_dir_path
        )

        self.model_dir_path = \
            Path(self.model_settings['model data folder path']) / \
            self.model_settings['model name']

        self.database = Database(
            model_folder_path=self.model_dir_path,
            sets=constants._SETS,
            clean_database=clean_database,
            generate_sets_file=generate_sets_file
        )

        self.problem = Problem()

    def load_sets_data(self):
        pass


if __name__ == '__main__':
    pass
