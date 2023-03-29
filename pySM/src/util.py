import json
import yaml

import pprint as pp

from pathlib import Path


def prettify(item: dict) -> None:
    """Print a dictionary in a human-readable format in the terminal

    Args:
        item (dict): a generic dictionary

    Raises:
        TypeError: If the argument is not a dictionary.
    """
    if not isinstance(item, dict):
        raise TypeError('Function argument should be a dictionary.')
    print(pp.pformat(item))


def find_dict_depth(item) -> int:
    """Find and return the depth of a generic dictionary

    Args:
        item (dict): a generic dictionary

    Returns:
        int: depth of the dictionary
    """
    if not isinstance(item, dict) or not item:
        return 0
    return 1 + max(find_dict_depth(v) for k, v in item.items())


def load_file(
        file_name: str,
        folder_path: str,
        file_type: str = 'json') -> dict:
    """Loads JSON or YAML file and returns a dictionary with its content.

    Args:
        file_name (str): file name to be loaded.
        file_type (str): file type (only .json or .yaml allowed)
        folder_path (str, optional): The path to the folder where the file 
            is located. If None, the default path of the FileManager 
            instance is used.

    Raises:
        ValueError: If the file_type argument is not 'json' or 'yaml'.
        ValueError: If the file format is incorrect or the file cannot be loaded.

    Returns:
        dict: a dictionary containing the data from the file.
    """
    if file_type == 'json':
        loader = json.load
    elif file_type == 'yaml':
        loader = yaml.safe_load
    else:
        raise ValueError(
            'Invalid file type. Only JSON and YAML are allowed.')

    file_path = Path(folder_path) / file_name

    with file_path.open() as file:
        try:
            return loader(file)
        except ValueError as error:
            raise ValueError(
                f'Error loading {file_type} file: wrong file format'
            ) from error


if __name__ == '__main__':
    pass
