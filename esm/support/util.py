from os import path
import pprint as pp
from pathlib import Path
from typing import Dict, List, Any, Literal

import itertools as it
import pandas as pd

from esm import constants
from esm.support.file_manager import FileManager
from esm.log_exc.logger import Logger


default_dir_path = 'default'


def create_model_dir(
    model_dir_name: str,
    main_dir_path: str,
    default_model: str = None,
    force_overwrite: bool = False,
    export_tutorial: bool = False,
    default_files_prefix: str = 'template_'
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
                path_source=default_dir_path,
                file_name=default_files_prefix+file_name,
                file_new_name=file_name,
                force_overwrite=force_overwrite,
            )

        files.logger.info(f"Directory of model '{model_dir_name}' generated.")

    else:
        validate_selection(
            valid_selections=constants._TEMPLATE_MODELS,
            selection=default_model)

        template_dir_path = Path(default_dir_path) / default_model

        files.copy_all_files_to_destination(
            path_source=template_dir_path,
            path_destination=model_dir_path,
            force_overwrite=force_overwrite,
        )

        files.logger.info(
            f"Directory of model '{model_dir_name}' "
            f"generated based on default model '{default_model}'.")

    if export_tutorial:
        tutorial_file_name = default_files_prefix + constants._TUTORIAL_FILE_NAME
        files.copy_file_to_destination(
            path_source=default_dir_path,
            path_destination=model_dir_path,
            file_name=tutorial_file_name,
            file_new_name=constants._TUTORIAL_FILE_NAME,
        )


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
    ValueError: Invalid selection. Please choose one of: option1, option2, 
        option3.
    """
    if not valid_selections:
        raise ValueError("No valid selections are available.")

    if selection not in valid_selections:
        raise ValueError(
            "Invalid selection. Please choose one "
            f"of: {', '.join(valid_selections)}.")


def validate_dict_structure(
        dictionary: Dict[str, Any],
        validation_structure: Dict[str, Any],
) -> bool:
    """
    Validate the structure of a dictionary against a validation structure.
    Only the first level of the dictionary hierarchy is validated.

    Args:
        dictionary (Dict[str, Any]): The dictionary to be validated.
        validation_structure (Dict[str, Any]): The structure to validate against.

    Returns:
        bool: True if the dictionary matches the validation structure, 
            False otherwise.
    """
    for key, value in dictionary.items():
        if key not in validation_structure:
            return False
        if not isinstance(value, validation_structure[key]):
            return False
    return True


def confirm_action(message: str) -> bool:
    """Ask the user to confirm an action.

    Args:
        message (str): Confirmation message to display.

    Returns:
        bool: True if the user confirms, False otherwise.
    """
    response = input(f"{message} (y/[n]): ").lower()
    return response == 'y'


def find_dict_depth(item: dict) -> int:
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
    >>> data = {
    >>>     'key_1': ['item_1', 'item_2', 'item_3'], 
    >>>     'key_2': [10, 20, 30]
    >>> }
    >>> data_pivoted = pivot_dict(data)

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

    Args:
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


def check_dataframes_equality(
        df_list: List[pd.DataFrame],
        skip_columns: List[str] = None,
        rows_order_matters: bool = False,
) -> bool:
    """Check the equality of multiple DataFrames while optionally skipping 
    specified columns.

    Args:
        df_list (List[pd.DataFrame]): A list of Pandas DataFrames to compare.
        skip_columns (List[str], optional): A list of column names to skip 
            during comparison.
        rows_order_matters (bool, optional): If set to False, two dataframes
            with same rows in different orders are still identified as equal. 

    Returns:
        bool: True if all DataFrames are equal, False otherwise.

    Raises:
        None
    """

    if skip_columns is not None:
        df_list = [
            dataframe.drop(columns=skip_columns)
            for dataframe in df_list
        ]

    if not rows_order_matters:
        df_list = [
            df.sort_values(df.columns.tolist()).reset_index(drop=True)
            for df in df_list
        ]

    return all(df.equals(df_list[0]) for df in df_list[1:])


def check_dataframe_columns_equality(
    df_list: List[pd.DataFrame],
    skip_columns: List[str] = None,
) -> bool:
    """Check the equality of column headers in multiple DataFrames while 
    optionally skipping specified columns.

    Args:
        df_list (List[pd.DataFrame]): A list of Pandas DataFrames to compare.
        skip_columns (List[str], optional): A list of column names to skip 
            during comparison.

    Returns:
        bool: True if all DataFrames have the same set of columns, False otherwise.

    Raises:
        None
    """

    if skip_columns is not None:
        modified_df_list = [
            dataframe.drop(columns=skip_columns, errors='ignore')
            for dataframe in df_list
        ]
    else:
        modified_df_list = df_list

    columns_list = [set(df.columns) for df in modified_df_list]

    first_columns = columns_list[0]
    return all(columns == first_columns for columns in columns_list[1:])


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


def substitute_keys(
        source_dict: Dict[str, Any],
        key_mapping_dict: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Substitute the keys in source_dict with the values from key_mapping.
    Raises an error if a value in key_mapping does not exist as a key in 
    source_dict.

    Args:
        source_dict (dict): A dictionary whose keys need to be substituted.
        key_mapping (dict): A dictionary containing the mapping of original 
            keys to new keys.

    Returns:
        dict: A new dictionary with substituted keys.

    Raises:
        ValueError: If a value from key_mapping is not a key in source_dict.
    """
    substituted_dict = {}
    for key, new_key in key_mapping_dict.items():
        if key not in source_dict:
            raise ValueError(
                f"Key '{key}' from key_mapping is not found in source_dict.")
        substituted_dict[new_key] = source_dict[key]
    return substituted_dict


def filter_dict_by_matching_value_content(
        input_dict: Dict[str, Dict[str, List[str] | None]]
) -> Dict[str, Dict[str, List[str] | None]]:
    """
    Filters a dictionary by keeping only the key-value pairs where the values
    (which are dictionaries themselves) contain the same items, disregarding
    the order of items within the lists that are values of the inner 
    dictionaries.

    Args:
        input_dict (dict): A dictionary where each value is another dictionary 
            with strings as keys and lists of strings as values.

    Returns:
        dict: A filtered dictionary containing only the entries where at least 
            one other entry exists with the same content in its value, 
            disregarding the order of items within the lists.

    Example:
    >>> example_dict = {
    ...     "item1": {"key1": ["a", "b"], "key2": ["c"]},
    ...     "item2": {"key2": ["c"], "key1": ["b", "a"]},  # Same as item1 but different order
    ...     "item3": {"key1": ["a"], "key2": ["b", "c"]},  # Different
    ... }
    >>> filtered_dict = filter_dict_by_matching_value_content(example_dict)
    >>> print(filtered_dict)
    {'item1': {'key1': ['a', 'b'], 'key2': ['c']},
     'item2': {'key2': ['c'], 'key1': ['b', 'a']}}  # Only item1 and item2 are included

    Note:
        This function assumes that the lists within the inner dictionaries 
            do not contain duplicate items, as it converts these lists to 
            sets for comparison purposes.
    """
    if not isinstance(input_dict, dict):
        raise TypeError("input_dict must be a dictionary.")

    def dict_to_comparable_form(d):
        return frozenset((k, tuple(sorted(v))) for k, v in d.items())

    comparable_form_to_keys = {}

    for key, value in input_dict.items():
        comparable_form = dict_to_comparable_form(value)

        if comparable_form not in comparable_form_to_keys:
            comparable_form_to_keys[comparable_form] = []

        comparable_form_to_keys[comparable_form].append(key)

    result_dict = {}

    for keys in comparable_form_to_keys.values():
        if len(keys) > 1:
            for key in keys:
                result_dict[key] = input_dict[key]

    return result_dict


def filter_dataframe(
        df_to_filter: pd.DataFrame,
        filter_dict: Dict[str, List[str]],
) -> pd.DataFrame:
    """
    Filters a DataFrame based on a dictionary identifying dataframe columns 
    and the related items to be filtered.

    Args:
        df_to_filter (pd.DataFrame): The DataFrame to filter.
        filter_dict (dict): A dictionary where keys are dataframe column names 
            and values are lists of strings that the filtered dictionary 
            columns will include.

    Returns:
        pd.DataFrame: A DataFrame filtered based on the specified column 
            criteria.
    """
    combined_mask = pd.Series([True] * len(df_to_filter))

    for column, values in filter_dict.items():

        if column in df_to_filter.columns:
            current_mask = df_to_filter[column].isin(values)
            combined_mask &= current_mask

    return df_to_filter[combined_mask]


def compare_dicts_ignoring_order(
        dict1: Dict[str, List[Any]],
        dict2: Dict[str, List[Any]],
) -> bool:

    if set(dict1.keys()) != set(dict2.keys()):
        return False
    for key in dict1:
        if sorted(dict1[key]) != sorted(dict2[key]):
            return False
    return True
