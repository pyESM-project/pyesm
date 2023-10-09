from pathlib import Path
from pySM.log_exc.logger import Logger
from pySM.util.file_manager import FileManager
from pySM.core.model import Model


class Interface:

    default_file_settings_dir_path = Path(__file__).resolve().parent
    default_file_settings_name = 'model_settings.json'

    def __init__(
            self,
            log_level: str = 'info',
            log_format: str = 'standard',
            log_file_name: str = 'log_model.log',
            file_settings_name: str = default_file_settings_name,
            file_settings_dir_path: str = default_file_settings_dir_path,
    ) -> None:

        self.logger = Logger(
            logger_name=str(self),
            log_level=log_level.upper(),
            log_file_path=Path(file_settings_dir_path) / log_file_name,
            log_format=log_format
        )

        self.logger.info(f"Initializing '{self}' object.")

        self.files = FileManager(logger=self.logger)

        self.file_settings_name = file_settings_name
        self.file_settings_dir_path = file_settings_dir_path

        self.model = Model(
            logger=self.logger,
            files=self.files,
            file_settings_name=self.file_settings_name,
            file_settings_dir_path=self.file_settings_dir_path,
        )

        self.logger.info(f"'{self}' object initialized.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'


    # def generate_rps(self):
    #     self.model.database.load_sets()
        # add validation of Category
        # self.model.database.generate_blank_rps()
if __name__ == '__main__':
    pass
