"""Module defining utility functions.

This module contains a collection of utility functions designed to assist with 
managing and manipulating data within the context of model generation and 
operation in the package. These functions include file management, data 
validation, dataframe manipulation, dictionary operations, and specific support 
functions that enhance the interoperability of data structures used throughout 
the application.
"""
import itertools as it
import numpy as np
import pandas as pd

from collections.abc import Iterable
from copy import deepcopy
from typing import Dict, List, Any, Optional, Tuple

from cvxlab.defaults import Defaults
from cvxlab.support import util_text


def get_user_confirmation(message: str) -> bool:
    """Prompt the user to confirm an action via command line input.

    Args:
        message (str): The message to display to the user.

    Returns:
        bool: True if the user confirms the action, False otherwise.
    """
    response = input(f"{message} (y/[n]): ").lower()
    return response == 'y'


def validate_selection(
        valid_selections: Iterable[str | int],
        selection: str | int,
        ignore_case: bool = False,
) -> None:
    """Validate a selected item against a list of valid selections.

    This function checks if the provided selection is present in the list of
    valid selections. It can optionally ignore case sensitivity during the
    comparison.

    Args:
        valid_selections (List[str | int]): A list containing all valid selections.
        selection (str | int): The selection to validate.
        ignore_case (bool): If True, ignores the case of the selection. 
            Works only with string selections. Default is False.

    Raises:
        TypeError: If the selection is not of type string or int.
        ValueError: 
            If no valid selections are available.
            If ignore_case is True but the selections are not strings.
            If the selection is not found within the list of valid selections.
    """
    if not valid_selections:
        raise ValueError("No valid selections are available.")

    if not isinstance(selection, str | int):
        raise TypeError(
            "Selection must be of type string or int. "
            f"Passed type: {type(selection).__name__}; "
        )

    if ignore_case:
        if all(isinstance(item, str) for item in valid_selections):
            valid_selections = [item.lower() for item in valid_selections]
            selection = selection.lower()
        else:
            raise ValueError(
                "Ignore case option is only available for string selections.")

    if selection not in valid_selections:
        raise ValueError(
            "Invalid selection. Please choose one "
            f"of: {', '.join(valid_selections)}.")


def items_in_list(
        items: Any,
        control_list: Any,
) -> bool:
    """Check if all items are present in a control collection.

    Supports list, tuple, dict (uses its keys) as items and control_list.
    Strings / bytes are not accepted (treated as atomic, raise TypeError).

    Args:
        items: Collection whose (elements | keys) to test.
        control_list: Collection providing membership domain.

    Returns:
        bool: True if every item is in control_list, False otherwise.

    Raises:
        TypeError: If inputs are of unsupported types.
        ValueError: If control_list is empty.
    """
    # Normalize items
    if isinstance(items, dict):
        normalized_items = list(items.keys())
    elif isinstance(items, Iterable) and \
            not isinstance(items, (str, bytes)):
        normalized_items = set(items)
    else:
        raise TypeError(
            "'items' must be a non-string Iterable or dict. "
            f"Passed type: {type(items).__name__}."
        )

    # Normalize control_list
    if isinstance(control_list, dict):
        normalized_control = set(control_list.keys())
    elif isinstance(control_list, Iterable) and \
            not isinstance(control_list, (str, bytes)):
        normalized_control = set(control_list)
    else:
        raise TypeError(
            "'control_list' must be a non-string Iterable or dict. "
            f"Passed type: {type(control_list).__name__}."
        )

    if not normalized_control:
        return False

    if not normalized_items:
        return False

    return all(item in normalized_control for item in normalized_items)


def find_dict_depth(item: dict) -> int:
    """Determine the depth of a nested dictionary.

    Args:
        item (dict): The dictionary for which the depth is calculated.

    Returns:
        int: The maximum depth of the dictionary.

    Raises:
        TypeError: If the passed argument is not a dictionary.
    """
    if not isinstance(item, dict):
        raise TypeError(
            "Passed argument must be a dictionary. "
            f"{type(item).__name__} was passed instead.")

    if not item:
        return 0

    return 1 + max(
        find_dict_depth(v) if isinstance(v, dict) else 0
        for v in item.values()
    )


def pivot_dict(
        data_dict: Dict,
        keys_order: Optional[List] = None,
) -> Dict:
    """Convert a dictionary of lists into a nested dictionary.

    This recursive function pivots a dictionary of lists into a nested dictionary,
    optionally ordering keys according to a specified list.

    Args:
        data_dict (Dict): The dictionary to be pivoted.
        order_list (Optional[List]): An optional list specifying the order of 
            keys for pivoting.

    Returns:
        Dict: A nested dictionary with keys from the original dictionary and 
            values as dictionaries.

    Raises:
        TypeError: If 'data_dict' is not a dictionary or 'keys_order' is not 
            a list.
        ValueError: If 'keys_order' does not correspond to the keys of 
            'data_dict'.
    """
    if not isinstance(data_dict, dict):
        raise TypeError(
            "Argument 'data_dict' must be a dictionary. "
            f"{type(data_dict).__name__} was passed instead."
        )

    if keys_order is not None and not isinstance(keys_order, list):
        raise TypeError(
            "Argument 'keys_order' must be a list or None. "
            f"{type(keys_order).__name__} was passed instead."
        )

    def pivot_recursive(keys, values):
        if not keys:
            return {value: None for value in values}
        else:
            key = keys[0]
            remaining_keys = keys[1:]
            return {item: pivot_recursive(remaining_keys, values)
                    for item in data_dict[key]}

    if keys_order:
        if not isinstance(keys_order, list):
            raise TypeError("Argument 'keys_order' must be a list.")
        if not set(keys_order) == set(data_dict.keys()):
            raise ValueError(
                "Items in keys_order do not correspond to keys of "
                "passed dictionary.")

        keys = keys_order
    else:
        keys = list(data_dict.keys())

    values = list(data_dict[keys[-1]])
    return pivot_recursive(keys[:-1], values)


def dict_cartesian_product(
        data_dict: Dict[Any, List[Any]],
        include_dict_keys: bool = True,
) -> List[Dict[Any, Any] | List[Any]]:
    """Cartesian product of dictionary values.

    This function generates a list of dictionaries or lists representing the 
    cartesian product of dictionary values.

    Args:
        data_dict (Dict[Any, List[Any]]): The dictionary to be used for the 
            cartesian product. The keys are any hashable type, and the values 
            are lists of elements to be combined.
        include_dict_keys (bool): If True, includes dictionary keys in the 
            resulting dictionaries. If False, returns lists of values only. 
            Default is True.

    Returns:
        List[Dict[Any, Any] | List[Any]]: A list of dictionaries or lists 
            representing the cartesian product of dictionary values. Each 
            dictionary contains one combination of the input values with the 
            corresponding keys, or each list contains one combination 
            of the input values without keys.

    Raises:
        TypeError: If 'data_dict' is not a dictionary or 'include_dict_keys' 
            is not a boolean.
    """
    if not isinstance(data_dict, dict):
        raise TypeError(
            "Argument 'data_dict' must be a dictionary. "
            f"{type(data_dict).__name__} was passed instead."
        )
    if not isinstance(include_dict_keys, bool):
        raise TypeError(
            "Argument 'include_dict_keys' must be a boolean. "
            f"{type(include_dict_keys).__name__} was passed instead."
        )

    if not data_dict:
        return []

    combinations = it.product(*data_dict.values())

    if not include_dict_keys:
        return [list(combination) for combination in combinations]

    return [
        dict(zip(data_dict.keys(), combination))
        for combination in combinations
    ]


def dict_values_cartesian_product(
        data_dict: Dict[Any, List[Any]],
) -> int:
    """Return Cartesian product of dictionary values.

    This function returns an integer representing the number of combination of 
    items included in all values of a dictionary.

    Args:
        data_dict (Dict[Any, List[Any]]): The dictionary to be used for the 
            cartesian product. The keys are any hashable type, and the values 
            are lists of elements to be combined.

    Returns:
        int: An integer representing the number of combinations of the input values.

    Raises:
        TypeError: If 'data_dict' is not a dictionary.
    """
    if not isinstance(data_dict, dict):
        raise TypeError(
            "Argument 'data_dict' must be a dictionary. "
            f"{type(data_dict).__name__} was passed instead."
        )

    if not data_dict:
        return 0

    combinations = it.product(*data_dict.values())
    return len(list(combinations))


def flattening_list(nested_list: List[Any]) -> List[Any]:
    """Flatten a (possibly nested) list into a flat list.

    Treats only list/tuple as flattenable. Strings, bytes, other iterables kept atomic.
    Args:
        nested_list (List[Any]): List containing elements and/or nested lists.
    Returns:
        List[Any]: Flat list of all atomic elements.
    """
    if not isinstance(nested_list, list):
        raise TypeError("Argument must be a list.")

    flat: List[Any] = []
    stack = list(reversed(nested_list))

    while stack:
        item = stack.pop()
        if isinstance(item, (list, tuple)):
            stack.extend(reversed(item))
        else:
            flat.append(item)

    return flat


def unpivot_dict_to_dataframe(
        data_dict: Dict[str, List[str]],
        key_order: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Unpivot a dictionary to a DataFrame.

    This function converts a nested dictionary into a DataFrame by performing a 
    cartesian product of dictionary values.

    Args:
        data_dict (Dict[str, List[str]]): The dictionary to be unpivoted.
        key_order (Optional[List[str]]): Order of keys for the resulting DataFrame.
            default is None, so the order of keys in the dictionary is used.

    Returns:
        pd.DataFrame: A DataFrame resulting from the cartesian product of 
            dictionary values.

    Raises:
        TypeError: If 'data_dict' is not a dictionary or 'key_order' is not 
            a list.
        ValueError: If 'key_order' does not correspond to the keys of 
            'data_dict'.
    """
    if not isinstance(data_dict, dict):
        raise TypeError(
            "Argument 'data_dict' must be a dictionary. "
            f"{type(data_dict).__name__} was passed instead."
        )

    if not data_dict:
        return pd.DataFrame()

    if key_order is not None and not isinstance(key_order, list):
        raise TypeError(
            "Argument 'key_order' must be a list or None. "
            f"{type(key_order).__name__} was passed instead."
        )

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
    """Add a given item to a specific position in a dictionary.

    Args:
        dictionary (dict): The dictionary to be modified.
        item (dict): The dictionary item to be added.
        position (int, optional): The position in the original dictionary where 
            the item should be added. If not provided, the function adds the item 
            at the end of the original dictionary. Default is -1.

    Returns:
        dict: A new dictionary with the item inserted at the specified position. 
            The order of the items is preserved.

    Raises:
        TypeError: If either 'dictionary' or 'item' is not of 'dict' type.
        ValueError: If 'position' is not within the range of -len(dictionary) to 
            len(dictionary).

    Note:
        This function requires Python 3.7 or later, as it relies on the fact that 
        dictionaries preserve insertion order as of this version.
    """
    if not all(isinstance(arg, dict) for arg in [dictionary, item]):
        raise TypeError("Passed argument/s not of 'dict' type.")

    if not isinstance(position, int):
        raise TypeError("Passed position argument must be of 'int' type.")

    if not -len(dictionary) <= position <= len(dictionary):
        raise ValueError(
            "Invalid position. Position must be "
            f"within {-len(dictionary)} and {len(dictionary)}")

    items = list(dictionary.items())
    item_list = list(item.items())

    for i in item_list:
        items.insert(position, i)

    return dict(items)


def check_dataframes_equality(
        df_list: List[pd.DataFrame],
        skip_columns: Optional[List[str]] = None,
        check_columns: Optional[List[str]] = None,
        cols_order_matters: bool = False,
        rows_order_matters: bool = False,
        homogeneous_num_types: bool = False,
) -> bool:
    """Check dataframes equality.

    This function checks the equality of multiple DataFrames while optionally 
    skipping specified columns or checking only specified columns. The function 
    can also ignore the order of columns and rows in the DataFrames.

    Args:
        df_list (List[pd.DataFrame]): A list of Pandas DataFrames to compare.
        skip_columns (List[str], optional): A list of column names to skip 
            during comparison.
        check_columns (List[str], optional): A list of column names to specifically
            include during comparison. If provided, only these columns are compared.
        cols_order_matters (bool, optional): If set to False, two dataframes
            with same columns in different orders are still identified as equal.
        rows_order_matters (bool, optional): If set to False, two dataframes
            with same rows in different orders are still identified as equal. 
        homogeneous_num_types (bool, optional): If set to True, all numeric
            values are converted to float64 for consistent comparisons.

    Returns:
        bool: True if all DataFrames are equal, False otherwise.

    Raises:
        ValueError: If any column in skip_columns is not present in all DataFrames.
        ValueError: If both skip_columns and check_columns are provided.
    """
    df_list_copy = deepcopy(df_list)

    if skip_columns and check_columns:
        raise ValueError(
            "Cannot use both 'skip_columns' and 'check_columns' arguments "
            "simultaneously.")

    if skip_columns:
        all_columns_set = set().union(*(df.columns for df in df_list_copy))
        if not set(skip_columns).issubset(all_columns_set):
            raise ValueError(
                "One or more items in 'skip_columns' argument are never "
                "present in any dataframe.")

        for dataframe in df_list_copy:
            dataframe.drop(columns=skip_columns, errors='ignore', inplace=True)

    if check_columns:
        all_columns_set = set().union(*(df.columns for df in df_list_copy))
        if not set(check_columns).issubset(all_columns_set):
            raise ValueError(
                "One or more items in 'check_columns' argument are never "
                "present in any dataframe.")

        for dataframe in df_list_copy:
            columns_to_drop = [
                col for col in dataframe.columns
                if col not in check_columns
            ]
            dataframe.drop(
                columns=columns_to_drop,
                errors='ignore',
                inplace=True,
            )

    # Convert all numeric values to float64 for consistent comparisons
    if homogeneous_num_types:
        df_list_copy = [
            df.apply(lambda col: pd.to_numeric(col, errors='coerce'))
            for df in df_list_copy
        ]

    shapes = set(df.shape for df in df_list_copy)
    if len(shapes) > 1:
        return False

    columns = set(tuple(sorted(df.columns)) for df in df_list_copy)
    if len(columns) > 1:
        return False

    if not cols_order_matters:
        df_list_copy = [df.sort_index(axis=1) for df in df_list_copy]

    if not rows_order_matters:
        df_list_copy = [
            df.sort_values(df.columns.tolist()).reset_index(drop=True)
            for df in df_list_copy
        ]

    first_df = df_list_copy[0]
    return all(first_df.equals(df) for df in df_list_copy[1:])


def check_dataframe_columns_equality(
    df_list: List[pd.DataFrame],
    skip_columns: Optional[List[str]] = None,
) -> bool:
    """Check the equality of column headers in multiple DataFrames.

    This function checks if multiple DataFrames have the same set of column headers,
    while optionally skipping specified columns.

    Args:
        df_list (List[pd.DataFrame]): A list of Pandas DataFrames to compare.
        skip_columns (List[str], optional): A list of column names to skip 
            during comparison.

    Returns:
        bool: True if all DataFrames have the same set of columns, False otherwise.

    Raises:
        ValueError: If df_list is empty or any DataFrame in df_list has no columns.
        TypeError: If any item in df_list is not a Pandas DataFrame.
    """
    if not df_list:
        raise ValueError("Passed list must not be empty.")

    if any(not isinstance(df, pd.DataFrame) for df in df_list):
        raise TypeError("Passed list must include only Pandas DataFrames.")

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
        column_position: Optional[int] = None,
) -> pd.DataFrame:
    """Add a column to a DataFrame at a specified position.

    Creates a copy of the input DataFrame and adds a new column at the specified
    position. If the column already exists, returns the original DataFrame unchanged.

    Args:
        dataframe (pd.DataFrame): The DataFrame to which the column will be added.
        column_header (str): The name of the column to add.
        column_values (Any, optional): Values for the new column. Defaults to None.
        column_position (int | None, optional): Position (0-indexed) where the column
            should be inserted. If None, appends to the end. Defaults to None.

    Returns:
        pd.DataFrame: A new DataFrame with the added column.

    Raises:
        TypeError: If dataframe is not a pandas DataFrame or column_header is not a string.
        ValueError: If column_position is out of valid range.
    """
    if not isinstance(column_header, str):
        raise TypeError("Passed column header must be of type string.")

    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError(
            "Passed dataframe argument must be a Pandas DataFrame.")

    if column_header in dataframe.columns:
        return dataframe

    dataframe = dataframe.copy()

    # in case of empty dataframe, add a dummy row to allow column insertion
    if dataframe.empty and len(dataframe) == 0:
        dataframe = pd.DataFrame(index=[0])

    if column_position is None:
        column_position = len(dataframe.columns)

    if not (0 <= column_position <= len(dataframe.columns)):
        raise ValueError(
            "Passed column_position is greater than the number of columns "
            "of the dataframe.")

    if column_values is not None:
        if not isinstance(column_values, (list, np.ndarray, pd.Series)):
            column_values = [column_values] * len(dataframe)

        if len(column_values) != len(dataframe):
            raise ValueError(
                f"Length of 'column_values' ({len(column_values)}) does not match "
                f"DataFrame length ({len(dataframe)})."
            )

    dataframe.insert(
        loc=column_position,
        column=column_header,
        value=column_values,
    )

    return dataframe


def substitute_dict_keys(
        source_dict: Dict[str, Any],
        key_mapping_dict: Dict[str, Any],
) -> Dict[str, Any]:
    """Substitute dictionary keys.

    This function substitute the keys in source_dict with the values from key_mapping.
    Raises an error if a value in key_mapping does not exist as a key in source_dict.

    Args:
        source_dict (dict): A dictionary whose keys need to be substituted.
        key_mapping (dict): A dictionary containing the mapping of original 
            keys to new keys.

    Returns:
        dict: A new dictionary with substituted keys.

    Raises:
        TypeError: If passed arguments are not dictionaries.
        ValueError: If a value from key_mapping is not a key in source_dict.
    """
    if not isinstance(source_dict, dict) or \
            not isinstance(key_mapping_dict, dict):
        raise TypeError("Passed arguments must be of dictionaries.")

    substituted_dict = {}
    for key, new_key in key_mapping_dict.items():
        if key not in source_dict:
            raise ValueError(
                f"Key '{key}' from key_mapping is not found in source_dict.")
        substituted_dict[new_key] = source_dict[key]
    return substituted_dict


def fetch_dict_primary_key(
        dictionary: Dict[str, Any],
        second_level_key: str | int,
        second_level_value: Any,
) -> List[str | int]:
    """Fetch dictionary primary keys by second-level key-value pair.

    This function fetches all primary keys from a dictionary based on a second-level 
    key-value pair. If the second-level key-value pair is not found, returns an 
    empty list.

    Args:
        dictionary (Dict[str, Any]): The dictionary to search.
        second_level_key (str | int): The key to search for in the second level.
        second_level_value (Any): The value to search for in the second level.

    Returns:
        List[str | int]: A list of primary keys where the second-level key-value 
            pair is found. Returns an empty list if not found.

    Raises: 
        TypeError: If dictionary is not a dictionary.
    """
    if not isinstance(dictionary, dict):
        raise TypeError("Passed dictionary must be a dictionary.")

    matching_keys = []
    for primary_key, value in dictionary.items():
        if isinstance(value, dict) and \
                value.get(second_level_key) == second_level_value:
            matching_keys.append(primary_key)

    return matching_keys


def filter_dataframe(
        df_to_filter: pd.DataFrame,
        filter_dict: Dict[str, List[str]],
        reset_index: bool = True,
        reorder_cols_based_on_filter: bool = False,
        reorder_rows_based_on_filter: bool = False,
) -> pd.DataFrame:
    """Filter a DataFrame based on a dictionary of column criteria.

    Filters a DataFrame based on a dictionary identifying dataframe columns 
    and the related items to be filtered. The function can also reorder
    columns and rows based on the order of keys and values in the filter_dict.

    Args:
        df_to_filter (pd.DataFrame): The DataFrame to filter.
        filter_dict (dict): A dictionary where keys are dataframe column names 
            and values are lists of strings that the filtered dictionary 
            columns will include.
        reset_index (bool, Optional): If True, resets the index of the filtered 
            DataFrame. Default to True.
        reorder_cols_based_on_filter (bool, Optional): If True, reorder the filtered
            dataframe columns according to the order of parsed dictionary
            keys. Default to False.
        reorder_rows_based_on_filter (bool, Optional): If True, reorder the filtered
            dataframe rows according to the order of parsed dictionary
            values. Default to False.

    Returns:
        pd.DataFrame: A DataFrame filtered based on the specified column 
            criteria.

    Raises:
        ValueError: If df_to_filter is not a DataFrame, if filter_dict is not 
            a dictionary, or if any key in filter_dict is not a column in 
            df_to_filter.
    """
    if not isinstance(df_to_filter, pd.DataFrame):
        raise ValueError("Passed df_to_filter must be a Pandas DataFrame.")

    if not isinstance(filter_dict, dict):
        raise ValueError("Passed filter_dict must be a dictionary.")

    for key in filter_dict.keys():
        if key not in df_to_filter.columns:
            raise ValueError(
                f"Key '{key}' in filter_dict is not a DataFrame column.")

    # filter dataframe based on filter_dict
    mask = pd.Series([True] * len(df_to_filter))

    for column, values in filter_dict.items():
        mask = mask & df_to_filter[column].isin(values)

    filtered_df = df_to_filter[mask].copy()

    # optionally reorder columns based on filter_dict keys
    if reorder_cols_based_on_filter:
        filter_keys = list(filter_dict.keys())
        other_keys = [
            col
            for col in df_to_filter.columns
            if col not in filter_keys
        ]
        new_columns_order = filter_keys + other_keys
        filtered_df = filtered_df[new_columns_order]

    # optionally reorder rows based on filter_dict values
    if reorder_rows_based_on_filter:
        df_order = unpivot_dict_to_dataframe(filter_dict)
        sort_key = pd.Series(
            range(len(df_order)),
            index=pd.MultiIndex.from_frame(df_order)
        )
        filtered_df['sort_key'] = filtered_df.set_index(
            list(filter_dict.keys())
        ).index.map(sort_key.get)
        filtered_df.sort_values('sort_key', inplace=True)
        filtered_df.drop(columns='sort_key', inplace=True)

    if reset_index:
        filtered_df.reset_index(drop=True, inplace=True)

    return filtered_df


def find_non_allowed_types(
        dataframe: pd.DataFrame,
        allowed_types: Tuple,
        target_col_header: str,
        return_col_header: Optional[str] = None,
        allow_none: bool = False,
) -> List:
    """Find non-allowed types in a DataFrame column.

    This function finds rows in a DataFrame where the value in a specified column 
    is not of an allowed type. It can return either the values in the target column
    or the values in another specified column for those rows. 

    Args:
        dataframe (pd.DataFrame): The DataFrame to check.
        allowed_types (Tuple[type]): The types that are allowed for the target 
            column values.
        target_col_header (str): The name of the column to check.
        return_col_header (Optional[str]): The name of the column to return. 
            If None, return list of items in the target_col_header with non-allowed
            types.
        allow_none (bool): Whether to allow None values. Default is False.

    Returns:
        List: The list of values in the return column for rows where the target 
            column is not of an allowed type, or items in the target column 
            with non-allowed types.

    Raises:
        ValueError: If dataframe is not a DataFrame, if target_col_header or 
            return_col_header is not a column in dataframe, or if allowed_types 
            is not a tuple.
    """
    if not isinstance(dataframe, pd.DataFrame):
        raise ValueError("Passed 'dataframe' argument must be a DataFrame.")
    if not isinstance(allowed_types, tuple):
        raise ValueError("Passed 'allowed_types' argument must be a tuple.")
    if target_col_header not in dataframe.columns:
        raise ValueError(
            f"'{target_col_header}' is not a column in dataframe.")
    if return_col_header and return_col_header not in dataframe.columns:
        raise ValueError(
            f"'{return_col_header}' is not a column in dataframe.")

    def is_non_allowed(row):
        value = row[target_col_header]
        if pd.isna(value):
            return not allow_none
        return not isinstance(value, allowed_types)

    non_allowed_rows = dataframe.apply(is_non_allowed, axis=1)

    if return_col_header:
        return dataframe.loc[non_allowed_rows, return_col_header].tolist()

    return dataframe.loc[non_allowed_rows, target_col_header].tolist()


def find_dict_keys_corresponding_to_value(
        dictionary: Dict[Any, Any],
        target_value: Any,
) -> Optional[Any]:
    """Find all keys in a dictionary that correspond to a given value.

    Args:
        dictionary (Dict[Any, Any]): The dictionary to search.
        target_value (Any): The value to find.

    Returns:
        List[Any]: The keys corresponding to the target value. If the value 
            is not found, returns an empty list.

    Raises:
        TypeError: If the passed argument is not a dictionary.
    """
    if not isinstance(dictionary, dict):
        raise TypeError(
            "Passed 'dictionary' argument must be a dictionary."
            f"{type(dictionary).__name__} was passed instead.")

    return [
        key for key, value in dictionary.items()
        if value == target_value
    ]


def calculate_change_norm(
        seq1: List[float] | Tuple[float, ...] | pd.Series | np.ndarray | float | int,
        seq2: List[float] | Tuple[float, ...] | pd.Series | np.ndarray | float | int | None,
        metric: Defaults.NumericalSettings.NormType,
        ignore_nan: bool,
) -> float:
    """Compute change metric between two numeric sequences (or scalars).

    This function computes a specified change metric between two numeric sequences
    (or scalars). It supports various metrics including maximum relative change,
    maximum absolute change, and L1, L2, and L-infinity norms. It can also ignore
    NaN or non-numeric values during the computation.
    If seq2 is None, the norm of seq1 is calculated, calculating the norm of the
    vector with respect to zero.

    Supported metrics (let x := seq1, y := seq2, d := x - y). 
        "max_relative": maximum relative change. Implemented as:
            max_i |d_i| / |y_i|   (∞ if |y_i| == 0 and |d_i| > 0)
        "max_absolute": maximum absolute change. Implemented as:
            max_i |d_i|
        "linf": L-infinity norm (Maximum norm). Implemented as:
            ||d||_∞  (max_i |d_i|)
        "l1": L1 norm (Manhattan norm). Implemented as:
            ||d||_1  (sum_i |d_i|)
        "l2": L2 norm (Euclidean norm, commonly adopted). Implemented as:
            ||d||_2  (sqrt(sum_i d_i^2))

    Args:
        seq1, seq2: Numeric sequences (or scalars). Must have same length. If None, 
            norm of seq1 is calculated.
        metric: Metric name as above.
        ignore_nan: If True, drop positions where either x or y is NaN/non-numeric.
            If False, raises on non-numeric or NaN.

    Returns:
        float: The computed metric. If all positions are dropped, returns 0.0.

    Raises:
        ValueError: On length mismatch, invalid metric, or non-numeric values when 
            ignore_nan=False.
    """
    # Convert inputs to 1D numpy arrays
    x = np.asarray(seq1, dtype=float).ravel()
    y = np.asarray(seq2, dtype=float).ravel() if seq2 is not None else None

    if y is not None and x.shape != y.shape:
        raise ValueError("Sequences must have the same shape.")

    # Build mask for valid numeric entries
    valid_mask = np.isfinite(x) & (np.isfinite(y) if y is not None else True)

    if not ignore_nan:
        if not np.all(valid_mask):
            raise ValueError(
                "NaN/Inf values encountered and ignore_nan=False.")
    else:
        x = x[valid_mask]
        y = y[valid_mask] if y is not None else None

    if x.size == 0:
        return 0.0

    d = x - y if y is not None else x
    abs_d = np.abs(d)

    if metric == "max_relative":
        if y is None:
            # When computing norm only, use absolute values
            return float(np.max(abs_d))
        # Relative change: max_i |d_i| / |y_i|
        denom = np.abs(y)
        # relative element-wise; denom==0 and abs_d>0 -> inf
        with np.errstate(divide='ignore', invalid='ignore'):
            rel = np.where(
                abs_d == 0, 0.0, np.where(denom == 0, np.inf, abs_d / denom))
        return float(np.max(rel))

    if metric == "max_absolute":
        return float(np.max(abs_d))

    if metric == "l1":
        return float(np.linalg.norm(d, ord=1))

    if metric == "l2":
        return float(np.linalg.norm(d, ord=2))

    if metric == "linf":
        return float(np.linalg.norm(d, ord=np.inf))

    raise ValueError(f"Unsupported metric '{metric}'.")


def root_mean_square(
        values: Iterable | np.ndarray | pd.Series,
        ignore_nan: bool = True,
) -> float:
    """Compute the root-mean-square (RMS) of numeric values.

    RMS is defined as: rms = sqrt( (1/n) * sum_i v_i^2 )

    Args:
        values: Any iterable/array/Series of numeric values (list, set, tuple, 
            ndarray, Series).
        ignore_nan: If True, drops NaN/Inf entries before computing RMS; if all 
            are dropped, returns 0.0. If False, raises on NaN/Inf.

    Returns:
        float: The RMS of the provided values.

    Raises:
        ValueError: If non-numeric, NaN/Inf values are present and ignore_nan=False.
    """
    arr = np.asarray(
        list(values) if not isinstance(values, (np.ndarray, pd.Series))
        else values, dtype=float
    ).ravel()

    valid_mask = np.isfinite(arr)
    if not ignore_nan:
        if not np.all(valid_mask):
            raise ValueError(
                "NaN/Inf values encountered and ignore_nan=False.")
    else:
        arr = arr[valid_mask]

    if arr.size == 0:
        return 0.0

    return float(np.sqrt(np.mean(arr**2)))


def calculate_values_difference(
        value_1: float,
        value_2: float,
        relative_difference: bool = True,
        modules_difference: bool = False,
        ignore_nan: bool = False,
) -> float:
    """Calculate the difference between two values.

    This function calculates the difference between two numeric values. It can
    compute either the absolute or relative difference, and can also return the
    module of the difference. If either value is non-numeric and ignore_nan is
    True, the function returns None.

    Args:
        value_1 (float): The first value.
        value_2 (float): The second value.
        relative_difference (bool): If True, calculate the relative difference. 
            Default is True.
        modules_difference (bool): If True, calculate the module of difference 
            (either absolute or relative). Default is False.
        ignore_nan (bool): If True, ignore non-numeric values. 
            Default is False.

    Returns:
        float: The calculated difference. If both values are non-numeric 
            and ignore_nan_values is True, nothing is returned.

    Raises:
        ValueError: If either value is non-numeric and ignore_nan is False.
    """
    if not isinstance(value_1, float | int) or \
            not isinstance(value_2, float | int):
        if not ignore_nan:
            raise ValueError("Passed values must be of numeric type.")
        else:
            return

    if modules_difference:
        difference = abs(value_1 - value_2)
        reference = abs(value_2)
    else:
        difference = value_1 - value_2
        reference = value_2

    if relative_difference:

        if difference == 0:
            return 0

        if reference == 0:
            return float('inf')

        return difference / reference

    else:
        return difference


def remove_empty_items_from_dict(
        dictionary: Dict,
        empty_values: List = [None, 'nan', 'None', 'null', '', 'NaN', [], {}],
) -> Dict:
    """Remove keys with empty values from a dictionary.

    Args:
        dictionary (Dict): The dictionary to clean.

    Returns:
        Dict: A new dictionary with all keys that had empty values removed.

    Raises:
        TypeError: If the passed argument is not a dictionary.
        ValueError: If the passed empty_values list does not include at least
            one type of the default empty values.
    """
    empty_values_list = [None, 'nan', 'None', 'null', '', 'NaN', [], {}]

    if not isinstance(dictionary, dict):
        raise TypeError(
            "Passed argument must be a dictionary. "
            f"{type(dictionary).__name__} was passed instead")

    if not [value for value in empty_values if value in empty_values_list]:
        raise ValueError(
            "Passed empty_values tuple must include at least one type of the "
            f"default empty values {empty_values_list}.")

    def _remove_items(d: Dict) -> Dict:
        cleaned_dict = {}

        for key, value in d.items():
            if isinstance(value, dict):
                nested = _remove_items(value)
                if nested:
                    cleaned_dict[key] = nested
            elif value not in empty_values:
                cleaned_dict[key] = value

        return cleaned_dict

    return _remove_items(dictionary)


def merge_dicts(
        dicts_list: List[Dict],
        unique_values: bool = False,
) -> Dict[str, List[Any]]:
    """Merge a list of dictionaries into a single dictionary.

    This function merges a list of dictionaries into a single dictionary.
    If a key appears in multiple dictionaries, its values are combined into a list.
    If `unique_values` is True, ensures values are unique per key.
    This function is a helper for the pivot_dataframe_to_data_structure function.

    Args:
        dicts_list (List[Dict[str, Any]]): A list of dictionaries to merge.
        unique_values (bool): If True, ensures unique values per key. Default is False.

    Returns:
        Dict[str, List[Any]]: A merged dictionary with keys combined and values in lists.
    """
    merged = {}

    for dictionary in dicts_list:
        if dictionary is None:
            dictionary = {}

        for key, value in dictionary.items():

            if value is None:
                continue

            if not isinstance(value, Iterable) or \
                    isinstance(value, (str, bytes)):
                value = [value]

            if key not in merged:
                merged[key] = list(value) if not unique_values else set(value)

            else:
                if unique_values:
                    merged[key].update(value)  # Use set to avoid duplicates
                else:
                    merged[key].extend(value)  # Allow duplicates

    return {key: list(values) for key, values in merged.items()}


def pivot_dataframe_to_data_structure(
    data: pd.DataFrame,
    primary_key: Optional[str | int] = None,
    secondary_key: Optional[str | int] = None,
    merge_dict: bool = False,
    skip_process_str: bool = False,
) -> dict:
    """Pivot a DataFrame into a nested dictionary structure.

    This function pivots a DataFrame into a nested dictionary structure based on
    specified primary and secondary keys. It can also merge dictionaries for
    rows with the same primary key and process string values.

    Args:
        data (pd.DataFrame): The DataFrame to be pivoted.
        primary_key (Optional[str  |  int], optional): The column name or index 
            to be used as the primary key. Defaults to the first column.
        secondary_key (Optional[str  |  int], optional): The column name or index
            to be used as the secondary key. Defaults to None.
        merge_dict (bool, optional): If True, merges dictionaries for rows with
            the same primary key. Defaults to False.
        skip_process_str (bool, optional): If True, skips processing string
            values. Defaults to False.

    Raises:
        ValueError: If primary or secondary key is not found in DataFrame columns.

    Returns:
        dict: A nested dictionary representing the pivoted DataFrame.
    """
    data_structure = {}
    primary_key = primary_key or data.columns[0]

    if primary_key not in data.columns:
        raise ValueError(
            f"Primary key '{primary_key}' not found in DataFrame columns.")

    for _, row in data.iterrows():
        key = row[primary_key]

        if key not in data_structure:
            data_structure[key] = {}

        inner_dict = {}
        for column in data.columns:
            if column == primary_key:
                continue

            if column == secondary_key:
                break

            value = row[column]
            if value is not None:
                if not skip_process_str:
                    # string is processed except for metadata column
                    if column != Defaults.DefaultStructures.METADATA:
                        inner_dict[column] = util_text.process_str(value)
                    else:
                        inner_dict[column] = value
                else:
                    inner_dict[column] = value

        if merge_dict:
            data_structure[key] = merge_dicts(
                [data_structure[key], inner_dict])
        else:
            data_structure[key] = inner_dict

    if secondary_key:
        if secondary_key not in data.columns:
            raise ValueError(
                f"Secondary key '{secondary_key}' not found in DataFrame columns.")

        secondary_key_index = data.columns.get_loc(secondary_key)
        secondary_keys_list = data.columns[secondary_key_index:]

        for _, row in data.iterrows():
            outern_key = row[primary_key]
            inner_key = row[secondary_key]

            data_structure[outern_key].setdefault(secondary_key, {})

            inner_dict = {}

            for column in secondary_keys_list:
                if column == secondary_key:
                    continue

                value = row[column]
                if value is not None:
                    if column != Defaults.DefaultStructures.METADATA:
                        inner_dict[column] = util_text.process_str(value)
                    else:
                        inner_dict[column] = value

            data_structure[outern_key][secondary_key][inner_key] = inner_dict

    if None in data_structure:
        return data_structure[None]

    return data_structure


def transform_dict_none_to_values(dictionary: Dict, none_to: Any) -> Dict:
    """Transform None values in a dictionary to a specified value.

    This function iterates through a dictionary and replaces any None values
    with a specified value.

    Args:
        dictionary (Dict): The dictionary to be transformed.
        none_to (Any): The value to replace None values with.

    Returns:
        Dict: A new dictionary with None values replaced by the specified value.

    Raises:
        TypeError: If the passed argument is not a dictionary.    
    """
    if not isinstance(dictionary, Dict):
        raise TypeError(f"Dict type expected, '{type(dictionary)}' passed.")

    result = {}

    for key, value in dictionary.items():
        if value is None:
            result[key] = none_to
        else:
            result[key] = value

    return result


def is_sparse(array: np.ndarray, threshold: float) -> bool:
    """Check if a numpy ndarray can be considered sparse based on a given threshold.

    Args:
        array (np.ndarray): The numpy array to check.
        threshold (float): The proportion of zero elements required to consider
            the array as sparse.

    Returns:
        bool: True if the array is sparse, False otherwise.
    """
    if not isinstance(array, np.ndarray):
        raise TypeError(
            "Argument 'array' must be a numpy ndarray. "
            f"{type(array).__name__} was passed instead."
        )

    if not (0 <= threshold <= 1):
        raise ValueError("Argument 'threshold' must be between 0 and 1.")

    total_elements = array.size
    zero_elements = np.count_nonzero(array == 0)
    proportion_zero = zero_elements / total_elements

    if proportion_zero == 1:
        return False
    elif proportion_zero >= threshold:
        return True
    else:
        return False


def normalize_dataframe(
        df: pd.DataFrame,
        exclude_columns: Optional[List[str]] = None,
        numeric_columns: Optional[List[str]] = None,
        numeric_dtype: Optional[type] = None,
        replace_nans: bool = True,
        nan_fill_value: Optional[Any] = None,
) -> pd.DataFrame:
    """Normalize a DataFrame with optional casting and missing-value handling.

    Processing steps (in order):
      1. Copy the input DataFrame to avoid mutating the original.
      2. Validate exclude_columns; build target_cols = all columns except exclusions.
      3. If numeric_columns is provided, cast those columns (except excluded ones) to numeric_dtype.
      4. If replace_nans is True, replace a set of Na-like sentinels in target_cols with Python None.
      5. If nan_fill_value is not None, fill remaining None/NaN entries globally with that value.

    Na-like sentinels replaced when replace_nans is True:
      pd.NA, np.nan, float('nan'), 'nan', 'NaN', 'NA', 'na', 'N/A', 'null'

    Args:
        df (pd.DataFrame): Input DataFrame to normalize.
        exclude_columns (List[str] | None): Columns to skip for Na-like replacement
            and numeric casting. Default None.
        numeric_columns (str | List[str] | None): Column name(s) to cast to numeric_dtype.
            (Current signature accepts str; pass a list if multiple needed.)
        numeric_dtype (type | None): Target dtype for columns in numeric_columns.
            Required if numeric_columns is provided.
        replace_nans (bool): If True, perform Na-like sentinel replacement in non-excluded columns.
        nan_fill_value (Any | None): Value used with DataFrame.fillna after replacement.
            If None, no fill is performed.

    Returns:
        pd.DataFrame: A new normalized DataFrame.

    Raises:
        TypeError: If df is not a pandas DataFrame.
        ValueError: If exclude_columns or numeric_columns contain invalid names,
            if numeric_columns is provided without numeric_dtype,
            or if casting fails for any specified column.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(
            "Argument 'df' must be a pandas DataFrame. "
            f"{type(df).__name__} was passed instead."
        )

    df = df.copy()

    # Validate exclude_columns
    if exclude_columns is None:
        exclude_columns = []
    else:
        if not items_in_list(exclude_columns, df.columns):
            raise ValueError(
                f"One or more columns in '{exclude_columns}' not found "
                "in DataFrame.")

    target_cols = [col for col in df.columns if col not in exclude_columns]

    # Step 1: Convert numeric columns to specified dtype
    if numeric_columns is not None:
        if not items_in_list(numeric_columns, df.columns):
            raise ValueError(
                f"One or more columns in '{numeric_columns}' not found "
                "in DataFrame.")

        if not numeric_dtype:
            raise ValueError(
                "When 'numeric_columns' is specified, "
                "'numeric_dtype' must also be provided.")

        try:
            df.update({
                col: df[col].astype(numeric_dtype)
                for col in numeric_columns
                if col not in exclude_columns
            })
        except Exception as e:
            raise ValueError(
                "Error converting specified numeric columns to "
                f"'{numeric_dtype}': {e}"
            ) from e

    # Step 2: Replace all NaN/Na variants with None
    if replace_nans:
        nan_variants = {
            key: None for key in
            [
                pd.NA, np.nan, float('nan'),
                'nan', 'NaN', 'NA', 'na', 'N/A', 'null'
            ]
        }
        df[target_cols] = df[target_cols].replace(nan_variants)

    # Step 3: Fill None/NaN with specific value
    if nan_fill_value is not None:
        df.fillna(nan_fill_value, inplace=True)

    return df


def filter_non_allowed_negatives(
        dataframe: pd.DataFrame,
        column_header: str,
) -> pd.DataFrame:
    """Set DataFrame column values to zero based on sign condition.

    This function creates a copy of the input DataFrame and modifies the negative 
    values in the specified column to zero. 

    Args:
        dataframe (pd.DataFrame): The DataFrame to modify.
        column_header (str): The name of the column to modify.

    Returns:
        pd.DataFrame: A modified copy of the DataFrame with updated column values.

    Raises:
        TypeError: If dataframe is not a pandas DataFrame or column_header is not a string.
        ValueError: If column_header does not exist in the DataFrame or if
            condition_values is not one of the specified literals.
    """
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("Passed 'dataframe' must be a pandas DataFrame.")

    if not isinstance(column_header, str):
        raise TypeError("Passed 'column_header' must be a string.")

    if column_header not in dataframe.columns:
        raise ValueError(f"Column '{column_header}' not found in DataFrame.")

    df = dataframe.copy()
    series = df[column_header]
    numeric_series = pd.to_numeric(series, errors='coerce')

    if numeric_series.isna().any():
        invalid_mask = numeric_series.isna() & series.notna()
        invalid_examples = series[invalid_mask].unique().tolist()
        raise ValueError(
            f"Column '{column_header}' contains non-numeric values: {invalid_examples}"
        )

    # set negative values to zero
    numeric_series = numeric_series.mask(numeric_series < 0, 0)
    df[column_header] = numeric_series

    return df
