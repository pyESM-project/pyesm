from pathlib import Path
from pySM.log_exc.logger import Logger
from pySM.src.file_manager import FileManager
from pySM.src.model import Model


class Interface:

    file_settings_dir_path = Path(__file__).resolve().parent

    def __init__(
            self,
            log_level: str,
            log_format: str,
            file_settings_name: str = 'model_settings.json',
            file_settings_dir_path: str = file_settings_dir_path,
            log_file_name='log_model.log') -> None:

        self.logger = Logger(
            logger_name='interface',
            log_level=log_level.upper(),
            log_file_path=Path(file_settings_dir_path) / log_file_name,
            log_format=log_format
        )

        self.logger.info('Initializing new interface... ---------------------')

        self.files = FileManager(logger=self.logger)

        self.model_settings = self.files.load_file(
            file_name=file_settings_name,
            folder_path=file_settings_dir_path
        )

        self.logger.info('Interface correctly initialized.')

    def model_init(
            self,
            generate_sets_file: bool = True) -> None:

        self.model = Model(
            logger=self.logger,
            files=self.files,
            model_settings=self.model_settings,
            generate_sets_file=generate_sets_file)


if __name__ == '__main__':

    m1 = Interface(
        log_level='info',
        log_format='minimal')

    m1.model_init(generate_sets_file=True)
