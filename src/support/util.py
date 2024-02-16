import itertools as it
import pprint as pp

from pathlib import Path
from typing import Dict, List, Any, Literal
import numpy as np

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

    def __iter__(self):
        return iter(self.items())


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


def validate_selection(
        valid_selections: List[str],
        selection: str,
) -> None:
    """Validates if the given selection is in the list of valid selections.

    Args:
        valid_selections (List[str]): A list of valid selections.
        selection (str): The user's selection to be validated.

    Raises:
        ValueError: If the provided selection is not a valid selection.

    Example:
    >>> valid_selections = ['option1', 'option2', 'option3']
    >>> validate_selection(valid_selections, 'option2')  # No exception raised
    >>> validate_selection(valid_selections, 'invalid_option')
    ValueError: Invalid selection. Please choose one of: option1, option2, option3.
    """
    if selection not in valid_selections:
        raise ValueError(
            "Invalid selection. Please choose one "
            f"of: {', '.join(valid_selections)}.")


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
        data_dict: Dict[str, List[str]],
        key_order: List[str] = None,
) -> pd.DataFrame:
    """Generates a Pandas DataFrame by unpivoting content of a dictionary of 
    lists with generic number of items. User can unpivot just a subset of 
    entries of the dictionary with the desired order of keys.

    Args:
        data_dict (Dict[str, List[str]]): dictionary to be unpivoted. 
        key_order (List, optional): final index of the dictionary. Defaults: None.

    Returns:
        pd.DataFrame: Pandas DataFrame resulting from the cartesian product of 
        dictionary values.
    """

    if key_order and all([isinstance(item, List) for item in key_order]):
        key_order = [item[0] for item in key_order]

    if key_order:
        common_keys = set(key_order).intersection(set(data_dict.keys()))

        if not common_keys:
            raise ValueError(
                "No common keys between 'key_order' and 'data_dict'.")

        data_dict_to_unpivot = {key: data_dict[key] for key in key_order}

    else:
        data_dict_to_unpivot = data_dict
        key_order = list(data_dict_to_unpivot.keys())

    cartesian_product = list(it.product(*data_dict_to_unpivot.values()))

    unpivoted_data_dict = pd.DataFrame(
        data=cartesian_product,
        columns=key_order,
    )

    return unpivoted_data_dict


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


def merge_series_to_dataframe(
        series: pd.Series,
        dataframe: pd.DataFrame,
        position: Literal[0, -1] = 0,
) -> pd.DataFrame:
    """Merge a given 'series' with a 'dataframe' at the specified position.
    It repeats all values of series for all rows of the dataframe.

    Parameters:
    - series (pd.Series): The series to be merged.
    - dataframe (pd.DataFrame): The dataframe to merge with.
    - position (Literal[0, -1], optional): The position at which to merge the series.
        0 indicates merging at the beginning, and -1 indicates merging at the end.
        Defaults to 0.

    Returns:
    pd.DataFrame: The merged dataframe.
    """
    if series.empty or dataframe.empty:
        raise ValueError("Both series and dataframe must be non-empty.")

    series_to_df = pd.concat(
        objs=[series]*len(dataframe),
        axis=1,
    ).transpose().reset_index(drop=True)

    objs = [series_to_df, dataframe]

    if position == -1:
        objs = objs[::-1]

    return pd.concat(objs=objs, axis=1)


def update_dataframes_on_condition(
        existing_df: pd.DataFrame,
        new_df: pd.DataFrame,
        col_to_update: str,
        cols_common: List[str],
        case: List[str],
) -> pd.DataFrame:
    """Compares values in existing and new DataFrames and returns a new DataFrame
    based on different 'case' options:
        - merge: data of existing_df and new_df (commond data updated with new_df).
        - existing_updated: only common data for existing_df and new_df 
        (commond data updated with new_df).
        - new_only: new data included in new_df not available in existing_df

    Args:
        existing_df (pd.DataFrame): DataFrame to be updated.
        new_df (pd.DataFrame): DataFrame containing the values to update from.
        col_to_update (str): name of the column to be considered for the comparison.
        cols_common (List[str]): List of column names representing the common 
        columns for the comparison.
        case: The type of comparison to be performed. Options: 
        'merge', 'existing_updated', 'new_only'.

    Returns:
        pd.DataFrame: updated DataFrame.

    Raises:
        ValueError: if an invalid 'case' is provided.
    """
    valid_cases = ['merge', 'existing_updated', 'new_only']
    validate_selection(valid_cases, case)

    merged_df = pd.merge(
        left=existing_df,
        right=new_df,
        on=cols_common,
        how='outer' if case == 'merge' else 'inner',
        suffixes=('_existing', '_new')
    )

    merged_df[col_to_update] = np.where(
        merged_df[col_to_update + '_new'].notna(),
        merged_df[col_to_update + '_new'],
        merged_df[col_to_update + '_existing']
    )

    merged_df.drop(
        columns=[col_to_update + '_existing', col_to_update + '_new'],
        inplace=True)

    if case == 'new_only':
        existing_dict = existing_df[cols_common].to_dict(orient='list')
        condition = ~new_df[cols_common].isin(existing_dict).all(axis=1)
        return new_df[condition]

    return merged_df


def add_column_to_dataframe(
        dataframe: pd.DataFrame,
        column_header: str,
        column_values: Any = None,
        column_position: int = None,
) -> None:
    """Inserts a new column into the provided DataFrame at the specified 
    position or at the end if no position is specified.

    Args:
        dataframe (pd.DataFrame): The pandas DataFrame to which the column 
            will be added.
        column_header (str): The name/header of the new column.
        column_values (Any, optional): The values to be assigned to the new 
            column. If not provided, the column will be populated with 
            NaN values.
        column_position (int, optional): The index position where the new 
            column will be inserted. If not provided, the column will be 
            inserted at the end.

    Returns:
        None

    Raises:
        None
    """
    if column_position is None:
        column_position = len(dataframe.columns)

    dataframe.insert(
        loc=column_position,
        column=column_header,
        value=column_values,
    )
