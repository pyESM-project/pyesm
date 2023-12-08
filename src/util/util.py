import itertools as it
import pprint as pp

from pathlib import Path
from typing import Dict, List, Any, OrderedDict

import pandas as pd


class DotDict(dict):
    """This class generates a dictionary where values can be accessed either
    by key (example: dict_instance['key']) and by dot notation (example:
    dict_instance.key). The class inherits all methods of standard dict.
    """

    def __getattr__(self, name: str) -> Any:
        if name in self:
            return self[name]
        else:
            error = f"No such attribute: {name}"
            raise AttributeError(error)

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value


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
    """Generates nested directories based on the provided base_path and 
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


def pivot_dict(
        data_dict: Dict,
        order_list: List = None,
) -> Dict:
    """Pivot a dictionary of lists (arbitrary number of keys and items in each 
    list), transforming it into a nested dictionary with keys equal to items of 
    the lists. Order of parsing keys can be changed.

    Args:
        data_dict (Dict): dictionary to be converted
        order_list (List, optional): order of parsing keys. Defaults to None.

    Returns:
        Dict: dictionary of nested dictionaries with last level = None

    Example:
        data = {
            'key_1': ['item_1', 'item_2', 'item_3'], 
            'key_2': [10, 20, 30]
        }

        data_pivoted = pivot_dict(data)

        data_pivoted = {
            item_1: {10: None, 20: None, 30: None},
            item_2: {10: None, 20: None, 30: None},
        }
    """
    def pivot_recursive(keys, values):
        if not keys:
            return {value: None for value in values}
        else:
            key = keys[0]
            remaining_keys = keys[1:]
            return {item: pivot_recursive(remaining_keys, values)
                    for item in data_dict[key]}

    if order_list:
        keys = order_list
    else:
        keys = list(data_dict.keys())

    values = list(data_dict[keys[-1]])
    return pivot_recursive(keys[:-1], values)


def unpivot_dict_to_dataframe(
        dict: Dict[str, List[str]],
        headers: List[str] = None,
) -> pd.DataFrame:
    """Generates a Pandas DataFrame by unpivoting content of a dictionary of 
    lists with generic number of items.

    Args:
        dict (Dict[str, List[str]]): dictionary to be unpivoted. 
        headers (List, optional): final index of the dictionary. Defaults to None.

    Returns:
        pd.DataFrame: Pandas DataFrame resulting from the cartesian product of 
        dictionary values.
    """

    cartesian_product = list(it.product(*dict.values()))

    if not headers:
        columns_headers = dict.keys()

    elif len(headers) == len(dict):
        columns_headers = headers

    else:
        raise ValueError(
            "Passed headers do not match number of columns in DataFrame.")

    df = pd.DataFrame(
        cartesian_product,
        columns=columns_headers,
    )
    return df


def add_item_to_dict(
        dictionary: dict,
        item: dict,
        position: int = -1,
) -> dict:
    """Add an given item to a defined position in a dictionary. 

    Args:
        dictionary (dict): dictionary to be modified.
        item (dict): dictionary item to be added.
        position (int, default: -1): position in the original dictionary where 
        add the item. If not indicated, the function add the item at the end of
        the original dictionary.

    Raises:
        ValueError: this function works with Python >= 3.7

    Returns:
        OrderedDict: _description_
    """

    if not (-len(dictionary) <= position <= len(dictionary)):
        raise ValueError(
            "Invalid position. Position must be "
            f"within {-len(dictionary)} and {len(dictionary)}")

    items = list(dictionary.items())
    item_list = list(item.items())
    items.insert(position, *item_list)
    return dict(items)
