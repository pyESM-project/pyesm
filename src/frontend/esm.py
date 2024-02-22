from pathlib import Path

from src.support import constants
from src.support.file_manager import FileManager
from src.log_exc.logger import Logger
from src.backend.model import Model


default_data_path = 'default'


def create_model_dir(
    model_dir_name: str,
    main_dir_path: str,
    force_overwrite: bool = False,
):

    files = FileManager(Logger())
    model_dir_path = Path(main_dir_path) / model_dir_name

    if model_dir_path.exists():
        if not files.erase_dir(model_dir_path):
            return

    files.create_dir(
        dir_path=model_dir_path,
        force_overwrite=force_overwrite
    )

    for file_name in constants._SETUP_FILES.values():
        files.copy_file_to_destination(
            path_destination=model_dir_path,
            path_source=default_data_path,
            file_name=file_name,
            force_overwrite=force_overwrite,
        )

    files.logger.info(
        f"Folder and template setup files for model '{model_dir_name}' ready.")
