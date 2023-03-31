from pathlib import Path
from pySM.log_exc.logger import Logger
from pySM.src.file_manager import FileManager
from pySM.src.model import Model


class Interface:

    file_settings_dir_path = Path(__file__).resolve().parent

    def __init__(
            self,
            file_settings_name: str = 'model_settings.json',
            file_settings_dir_path: str = file_settings_dir_path,
            log_file_name='log_model.log',
            log_level: str = 'info') -> None:

        self.logger = Logger(
            logger_name=__name__,
            log_level=log_level.upper(),
            log_file_path=Path(file_settings_dir_path) / log_file_name
        )

        self.files = FileManager(logger=self.logger)

        self.logger.info('Interface init: file manager and logger active.')

        self.model_settings = self.files.load_file(
            file_name=file_settings_name,
            folder_path=file_settings_dir_path
        )

    def model_init(
            self,
    ) -> None:
        pass


if __name__ == '__main__':

    test_model = Interface()
    test_model.model_init()
