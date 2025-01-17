from pathlib import Path

from esm.constants import Constants
from esm.log_exc.logger import Logger
from esm.support import util
from esm.support.file_manager import FileManager


def create_model_dir(
    model_dir_name: str,
    main_dir_path: str,
    force_overwrite: bool = False,
    export_tutorial: bool = True,
    template_file_type: str = 'yml',
) -> None:

    files = FileManager(Logger())
    model_dir_path = Path(main_dir_path) / model_dir_name

    files.logger.info(f"Generating model '{model_dir_name}' directory.")

    util.validate_selection(
        valid_selections=Constants.ConfigFiles.AVAILABLE_SOURCES,
        selection=template_file_type)

    if model_dir_path.exists():
        if not files.erase_dir(
                dir_path=model_dir_path,
                force_erase=force_overwrite):
            return

    files.create_dir(model_dir_path, force_overwrite)

    if template_file_type == 'yml':
        structure_name = Constants.ConfigFiles.SETUP_INFO
        structures = Constants.DefaultStructures

        structure_mapping = {
            structure_name[0]: structures.SET_STRUCTURE,
            structure_name[1]: structures.DATA_TABLE_STRUCTURE,
            structure_name[2]: structures.PROBLEM_STRUCTURE,
        }

        for file_name, structure_template in structure_mapping.items():
            generate_yaml_template(
                structure=structure_template[1],
                model_dir_path=model_dir_path,
                file_name=f"{file_name}.yml",
                header=structure_template[0],
            )

    elif template_file_type == 'xlsx':
        structure_mapping = Constants.DefaultStructures.XLSX_TEMPLATE_COLUMNS
        template_file_name = Constants.ConfigFiles.SETUP_XLSX_FILE

        files.dict_to_excel_headers(
            dict_name=structure_mapping,
            excel_dir_path=model_dir_path,
            excel_file_name=template_file_name,
        )

    else:
        msg = f"Unsupported template file type '{template_file_type}'."
        files.logger.error(msg)
        raise ValueError

    if export_tutorial:
        file_name = Constants.ConfigFiles.TUTORIAL_FILE_NAME
        files.copy_file_to_destination(
            path_source='',
            path_destination=model_dir_path,
            file_name=file_name,
            file_new_name=file_name,
            force_overwrite=True,
        )


def generate_yaml_template(
        structure: dict,
        model_dir_path: Path,
        file_name: str,
        header: str,
) -> None:

    file_path = model_dir_path / file_name

    if file_path.exists():
        user_input = input(
            f"File '{file_name}' already exists. Overwrite? (y/[n]): ")
        if user_input.lower() != 'y':
            return

    def _convert_to_yaml(
            structure: dict,
            indent: int,
    ) -> list[str]:

        optional_key = Constants.DefaultStructures.OPTIONAL
        any_key = Constants.DefaultStructures.ANY
        yaml_lines = []
        indent_str = '    ' * indent

        for key, value in structure.items():
            key = '_' if key == any_key else key

            if isinstance(value, type):
                value = value.__name__
                yaml_lines.append(f"{indent_str}{key}: {value}")

            elif isinstance(value, dict):
                yaml_lines.append(f"{indent_str}{key}: ")
                yaml_lines.extend(_convert_to_yaml(value, indent + 1))

            elif isinstance(value, tuple):
                if all(isinstance(item, type) for item in value):
                    value = ", ".join([item.__name__ for item in value])
                    yaml_lines.append(f"{indent_str}{key}: {value}")
                elif value[0] is optional_key:
                    if isinstance(value[1], dict):
                        yaml_lines.append(f"{indent_str}{key}: # optional ")
                        yaml_lines.extend(
                            _convert_to_yaml(value[1], indent + 1))
                    elif isinstance(value[1], type):
                        value = f"{value[1].__name__} # optional"
                        yaml_lines.append(f"{indent_str}{key}: {value}")

        return yaml_lines

    if header:
        indent = 1
        yaml_content = [header]
    else:
        indent = 0
        yaml_content = []

    yaml_content.extend(_convert_to_yaml(structure, indent))

    try:
        with open(file_path, 'w') as file:
            file.write('\n'.join(yaml_content))
    except IOError as e:
        raise IOError(f"Error writing to file '{file_name}': {e}") from e
