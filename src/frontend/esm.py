from pathlib import Path

from src import constants
from src.support.file_manager import FileManager
from src.log_exc.logger import Logger
from src.support import util


default_data_path = 'default'


def create_model_dir(
    model_dir_name: str,
    main_dir_path: str,
    default_model: str = None,
    force_overwrite: bool = False,
):
    """
    Create a directory structure for the generation of Model instances. 
    If no default_model is indicated, only basic setup files are generated.

    Args:
        model_dir_name (str): Name of the model directory.
        main_dir_path (str): Path to the main directory where the model 
            directory will be created.
        default_model (str, optional): Name of the default modle to use as a
            template. List of available templates in /src/constants.py.
            Defaults to None.
        force_overwrite (bool, optional): if True, avoid asking permission to 
            overwrite existing files/directories. Defaults to False.
    """

    files = FileManager(Logger())
    model_dir_path = Path(main_dir_path) / model_dir_name

    if model_dir_path.exists():
        if not files.erase_dir(
                dir_path=model_dir_path,
                force_erase=force_overwrite):
            return

    files.create_dir(model_dir_path, force_overwrite)

    if default_model is None:
        for file_name in constants._SETUP_FILES.values():
            files.copy_file_to_destination(
                path_destination=model_dir_path,
                path_source=default_data_path,
                file_name='dft_'+file_name,
                file_new_name=file_name,
                force_overwrite=force_overwrite,
            )

        files.logger.info(f"Directory of model '{model_dir_name}' generated.")

    else:
        util.validate_selection(
            valid_selections=constants._TEMPLATE_MODELS,
            selection=default_model)

        template_dir_path = Path(default_data_path) / default_model

        files.copy_all_files_to_destination(
            path_source=template_dir_path,
            path_destination=model_dir_path,
            force_overwrite=force_overwrite,
        )

        files.logger.info(
            f"Directory of model '{model_dir_name}' "
            f"generated based on default model '{default_model}'.")
