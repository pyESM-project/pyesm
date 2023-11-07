import os
import itertools as it
import pprint as pp


from pathlib import Path
from typing import Dict, List, Any


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


def generate_dict_with_none_values(item: dict) -> dict:
    """Recursively converts a nested dictionary to a dictionary where each key 
    has a corresponding value of None.

    Args:
        item (dict): The input dictionary to be converted.

    Returns:
        dict: The resulting dictionary with the same keys as the input, and 
        each key having a value of None.
    """
    dict_keys = {}

    for key, value in item.items():
        if isinstance(value, dict):
            dict_keys[key] = generate_dict_with_none_values(value)
        else:
            dict_keys[key] = None

    return dict_keys


def generate_nested_directories_paths(
        base_path: Path,
        directories: Dict[int, List[str]],
) -> List[Path]:
    """Generate nested directories based on the provided base_path and 
    directory structure.

    Args:
        base_path (Path): The base path where the nested directories will be created.
        directories (Dict[str, List[str]]): A dictionary with the directory structure,
            where keys are folder levels, and values are lists of folder names.

    Returns:
        List (Path): List of full paths of the nested directories.
    """
    if directories and all(v is not None for v in directories.values()):
        full_dir_paths = []
        dir_paths = list(it.product(*directories.values()))

        for dir_path in dir_paths:
            full_dir_paths.append(Path(base_path, *map(str, dir_path)))

        return full_dir_paths
    else:
        return [base_path]
