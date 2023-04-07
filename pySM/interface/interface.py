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
        """Interface initialization: generating logger and file manager, 
        loading model settings."""

        self.logger = Logger(
            logger_name='interface',
            log_level=log_level.upper(),
            log_file_path=Path(file_settings_dir_path) / log_file_name,
            log_format=log_format
        )

        self.logger.info(f"Initializing '{str(self)}' object.")

        self.files = FileManager(logger=self.logger)
        self.model = None
        self.model_settings = self.files.load_file(
            file_name=file_settings_name,
            folder_path=file_settings_dir_path
        )

        self.logger.info(f"'{str(self)}' object correctly initialized.")

    def __str__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def model_init(self, generate_sets_file: bool) -> None:
        """Initialization of the model and generation of blank sets file."""
        if self.model is None:
            self.model = Model(
                logger=self.logger,
                files=self.files,
                model_settings=self.model_settings,
                generate_sets_file=generate_sets_file)

    def model_cleanup(self):
        """Deleting model data folder."""
        self.model.model_cleanup()

    def generate_rps(self):
        """Loading sets file and generating blank rps."""
        self.model.database.load_sets()
        # add validation of Category 
        # eventually adding method for automatic ID completion in sets.
        self.model.database.generate_blank_rps()


if __name__ == '__main__':
    pass
