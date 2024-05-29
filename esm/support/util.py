"""
util.py 

@author: Matteo V. Rocco
@institution: Politecnico di Milano

This module contains a collection of utility functions designed to assist with 
managing and manipulating data within the context of model generation and 
operation in the package. These functions include file management, data 
validation, dataframe manipulation, dictionary operations, and specific support 
functions that enhance the interoperability of data structures used throughout 
the application.

These utilities are critical in handling the data integrity and consistency 
required for successful model operation, providing robust tools for data 
manipulation and validation.
"""

from collections.abc import Iterable
import pprint as pp
from pathlib import Path
from typing import Dict, List, Any, Literal, Optional, Tuple, Type

import itertools as it
import pandas as pd

from copy import deepcopy
from esm.constants import Constants
from esm.log_exc.logger import Logger
from esm.support.file_manager import FileManager


def create_model_dir(
    model_dir_name: str,
    main_dir_path: str,
    default_model: Optional[str] = None,
    force_overwrite: bool = False,
    export_tutorial: bool = False,
    default_files_prefix: str = 'template_'
):
    """
    Creates a directory structure for a new model instance, optionally using a 
    default model as a template, and can include a tutorial notebook if specified.

    Args:
        model_dir_name (str): The name for the new model directory.
        main_dir_path (str): The directory path where the new model directory 
            will be created.
        default_model (Optional[str]): The template model name from which to 
            copy files.
        force_overwrite (bool): If True, existing files or directories will be 
            overwritten without confirmation.
        export_tutorial (bool): If True, includes a Jupyter notebook tutorial 
            in the model directory.
        default_files_prefix (str): Prefix for files to be copied from the 
            template, defaults to 'template_'.

    Returns:
        None: The function creates directories and copies files but does not 
            return any value.
    """

    files = FileManager(Logger())
    model_dir_path = Path(main_dir_path) / model_dir_name

    if model_dir_path.exists():
        if not files.erase_dir(
                dir_path=model_dir_path,
                force_erase=force_overwrite):
            return

    files.create_dir(model_dir_path, force_overwrite)

    if export_tutorial:
        file_name = Constants.get('_TUTORIAL_FILE_NAME')
        files.copy_file_to_destination(
            path_source=Constants.get('_DEFAULT_MODELS_DIR_PATH'),
            path_destination=model_dir_path,
            file_name=default_files_prefix + file_name,
            file_new_name=file_name,
            force_overwrite=True,
        )

    if default_model is None:
        files.logger.info(f"Generating model '{model_dir_name}' directory.")

        for file_name in Constants.get('_SETUP_FILES').values():
            files.copy_file_to_destination(
                path_destination=model_dir_path,
                path_source=Constants.get('_DEFAULT_MODELS_DIR_PATH'),
                file_name=default_files_prefix+file_name,
                file_new_name=file_name,
                force_overwrite=force_overwrite,
            )

    else:
        files.logger.info(
            f"Directory of model '{model_dir_name}' "
            f"generated based on default model '{default_model}'.")

        validate_selection(
            valid_selections=list(Constants.get('_DEFAULT_MODELS_LIST')),
            selection=default_model)

        template_dir_path = \
            Path(Constants.get('_DEFAULT_MODELS_DIR_PATH')) / default_model

        files.copy_all_files_to_destination(
            path_source=template_dir_path,
            path_destination=model_dir_path,
            force_overwrite=force_overwrite,
        )


def prettify(item: dict) -> None:
    """
    Prints a dictionary in a human-readable format.

    Args:
        item (dict): The dictionary to be printed.

    Raises:
        TypeError: If 'item' is not a dictionary.

    Returns:
        None: This function only prints the dictionary to the console and 
            does not return any value.
    """
    if not isinstance(item, dict):
        raise TypeError('Function argument should be a dictionary.')
    print(pp.pformat(item))


def validate_selection(
        valid_selections: List[str],
        selection: str,
) -> None:
    """
    Validates if a provided selection is within a list of valid selections.

    Args:
        valid_selections (List[str]): A list containing all valid selections.
        selection (str): The selection to validate.

    Raises:
        ValueError: If the selection is not found within the list of valid selections.

    Returns:
        None: This function only performs validation and does not return any value.
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
    Validates the structure of a dictionary against a predefined schema.

    Args:
        dictionary (Dict[str, Any]): The dictionary to be validated.
        validation_structure (Dict[str, Any]): A schema dictionary where 
            each key corresponds to expected data types.

    Returns:
        bool: True if the dictionary matches the schema, False otherwise.
    """
    for key, value in dictionary.items():
        if key not in validation_structure:
            return False
        if not isinstance(value, validation_structure[key]):
            return False
    return True


def items_in_list(
        items: List,
        list_to_check: List,
) -> bool:
    """
    Checks if all items in a list are present in another list.

    Args:
        items (List): The list of items to check.
        list_to_check (List): The list to check against.

    Returns:
        bool: True if all items are present in the list to check, False otherwise.
    """
    return all(item in list_to_check for item in items)


def confirm_action(message: str) -> bool:
    """
    Prompts the user to confirm an action via command line input.

    Args:
        message (str): The message to display to the user.

    Returns:
        bool: True if the user confirms the action, False otherwise.
    """
    response = input(f"{message} (y/[n]): ").lower()
    return response == 'y'


def find_dict_depth(item: dict) -> int:
    """
    Determines the depth of a nested dictionary.

    Args:
        item (dict): The dictionary for which the depth is calculated.

    Returns:
        int: The maximum depth of the dictionary.
    """
    if not isinstance(item, dict) or not item:
        return 0

    return 1 + max(find_dict_depth(v) for k, v in item.items())


def generate_dict_with_none_values(item: dict) -> dict:
    """
    Converts all values in a nested dictionary to None, maintaining the structure 
    of the dictionary.

    Args:
        item (dict): The dictionary to be converted.

    Returns:
        dict: A new dictionary with the same keys but all values set to None.
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
        keys_order: Optional[List] = None,
) -> Dict:
    """
    Converts a dictionary of lists into a nested dictionary, optionally 
    ordering keys.

    Args:
        data_dict (Dict): The dictionary to be pivoted.
        order_list (Optional[List]): An optional list specifying the order of 
            keys for pivoting.

    Returns:
        Dict: A nested dictionary with keys from the original dictionary and 
            values as dictionaries.
    """

    if not isinstance(data_dict, dict):
        raise TypeError("Argument 'data_dict' must be a dictionary.")

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


def unpivot_dict_to_dataframe(
        data_dict: Dict[str, List[str]],
        key_order: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Converts a nested dictionary into a DataFrame by performing a cartesian 
    product of dictionary values.

    Args:
        data_dict (Dict[str, List[str]]): The dictionary to be unpivoted.
        key_order (Optional[List[str]]): Order of keys for the resulting DataFrame.
            default is None, so the order of keys in the dictionary is used.

    Returns:
        pd.DataFrame: A DataFrame resulting from the cartesian product of 
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
    """
    Add a given item to a specific position in a dictionary.

    Args:
        dictionary (dict): The dictionary to be modified.
        item (dict): The dictionary item to be added.
        position (int, optional): The position in the original dictionary where 
        the item should be added. If not provided, the function adds the item 
        at the end of the original dictionary. Default is -1.

    Raises:
        TypeError: If either 'dictionary' or 'item' is not of 'dict' type.
        ValueError: If 'position' is not within the range of -len(dictionary) to 
            len(dictionary).

    Returns:
        dict: A new dictionary with the item inserted at the specified position. 
            The order of the items is preserved.

    Note:
        This function requires Python 3.7 or later, as it relies on the fact that 
        dictionaries preserve insertion order as of this version.
    """

    if not all(isinstance(arg, dict) for arg in [dictionary, item]):
        raise TypeError("Passed argument/s not of 'dict' type.")

    if not -len(dictionary) <= position <= len(dictionary):
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
    """
    Merge a given 'series' with a 'dataframe' at the specified position.
    It repeats each value of the series as a new column of the dataframe.
    Final dataframe has a number of column of initial dataframe plus the number
    of items of the series.

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
        skip_columns: Optional[List[str]] = None,
        cols_order_matters: bool = False,
        rows_order_matters: bool = False,
) -> bool:
    """Check the equality of multiple DataFrames while optionally skipping 
    specified columns.

    Args:
        df_list (List[pd.DataFrame]): A list of Pandas DataFrames to compare.
        skip_columns (List[str], optional): A list of column names to skip 
            during comparison.
        cols_order_matters (bool, optional): If set to False, two dataframes
            with same columns in different orders are still identified as equal.
        rows_order_matters (bool, optional): If set to False, two dataframes
            with same rows in different orders are still identified as equal. 

    Returns:
        bool: True if all DataFrames are equal, False otherwise.

    Raises:
        None
    """
    df_list_copy = deepcopy(df_list)

    if skip_columns is not None:
        for dataframe in df_list_copy:
            columns_to_drop = [
                column
                for column in skip_columns
                if column in dataframe.columns
            ]
            dataframe.drop(columns=columns_to_drop, inplace=True)

    if len(set(df.shape for df in df_list_copy)) > 1:
        raise ValueError(
            "Passed dataframes have different shapes and cannot be compared.")

    if len(set(tuple(sorted(df.columns)) for df in df_list_copy)) > 1:
        raise ValueError(
            "Passed dataframes have different headers and cannot be compared.")

    if not cols_order_matters:
        df_list_copy = [df.sort_index(axis=1) for df in df_list_copy]

    if not rows_order_matters:
        df_list_copy = [
            df.sort_values(df.columns.tolist()).reset_index(drop=True)
            for df in df_list_copy
        ]

    return all(df.equals(df_list_copy[0]) for df in df_list_copy[1:])


def check_dataframe_columns_equality(
    df_list: List[pd.DataFrame],
    skip_columns: Optional[List[str]] = None,
) -> bool:
    """
    Check the equality of column headers in multiple DataFrames while 
    optionally skipping specified columns.

    Args:
        df_list (List[pd.DataFrame]): A list of Pandas DataFrames to compare.
        skip_columns (List[str], optional): A list of column names to skip 
            during comparison.

    Returns:
        bool: True if all DataFrames have the same set of columns, False otherwise.

    Raises:
        ValueError: If df_list is empty or any DataFrame in df_list has no columns.
    """
    if not df_list:
        raise ValueError("Passed list must not be empty.")

    if any(not isinstance(df, pd.DataFrame) for df in df_list):
        raise TypeError("Passed list must include only Pandas DataFrames.")

    if any(df.empty for df in df_list):
        raise ValueError("DataFrames in passed list must not be empty.")

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
) -> bool:
    """
    Inserts a new column into the provided DataFrame at the specified 
    position or at the end if no position is specified, only if the column
    does not already exist.

    Args:
        dataframe (pd.DataFrame): The pandas DataFrame to which the column 
            will be added.
        column_header (str): The name/header of the new column.
        column_values (Any, optional): The values to be assigned to the new 
            column. If not provided, the column will be populated with 
            NaN values.
        column_position (int, optional): The index position where the new 
            column will be inserted. If not provided, the column will be 
            inserted at the end. Default to None.

    Returns:
        bool: True if the column was added, False if the column already exists.

    Raises:
        TypeError: If column_header is not string or dataframe is not a Pandas
            DataFrame.
        ValueError: If the column_position is greater than the current number 
            of columns or if the column_header is empty, or if the legth of the
            passed column does not match the number of rows of the DataFrame.
    """
    if not isinstance(column_header, str):
        raise TypeError("Passed column header must be of type string.")

    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError(
            "Passed dataframe argument must be a Pandas DataFrame.")

    if column_header in dataframe.columns:
        return False

    if column_position is not None and column_position > len(dataframe):
        raise ValueError(
            "Passed column_position is greater than the number of columns "
            "of the dataframe.")

    if column_position is None:
        column_position = len(dataframe.columns)

    if column_values and \
            len(column_values) != dataframe.shape[0]:
        raise ValueError(
            "Passed column_values length must match the number or rows"
            "of the DataFrame.")

    dataframe.insert(
        loc=column_position,
        column=column_header,
        value=column_values,
    )

    return True


def substitute_dict_keys(
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


def filter_dataframe(
        df_to_filter: pd.DataFrame,
        filter_dict: Dict[str, List[str]],
        reset_index: bool = True,
        reorder_cols_based_on_filter: bool = False,
        reorder_rows_based_on_filter: bool = False,
) -> pd.DataFrame:
    """
    Filters a DataFrame based on a dictionary identifying dataframe columns 
    and the related items to be filtered.

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


def compare_dicts_ignoring_order(
        iterable: Iterable[Dict[str, List[Any]]]
) -> bool:
    """
    Compares any number of dictionaries to see if they are the same, ignoring 
    the order of items in the lists which are the values of the dictionaries.

    Args:
        iterable (Iterable[Dict[str, List[Any]]]): An iterable of dictionaries 
            to compare.

    Returns:
        bool: True if all dictionaries are the same (ignoring order of list 
            items), False otherwise.

    Raises:
        ValueError: If dicts is not an iterable, or if any value in dicts is 
            not a dictionary.
    """
    try:
        iter(iterable)
    except TypeError:
        raise ValueError("'iterable' argument must be an iterable.")

    for value in iterable:
        if not isinstance(value, dict):
            raise ValueError(
                "Each item in 'iterable' must be a dictionary.")

    iterable = list(iterable)
    if len(iterable) < 2:
        return True

    reference = iterable[0]
    ref_keys = set(reference.keys())

    for d in iterable[1:]:
        if set(d.keys()) != ref_keys:
            return False
        for key in ref_keys:
            if sorted(d[key]) != sorted(reference[key]):
                return False

    return True


def find_non_allowed_types(
        dataframe: pd.DataFrame,
        allowed_types: Tuple,
        target_col_header: str,
        return_col_header: Optional[str] = None,
) -> List:
    """
    Find rows in a DataFrame where the value in a specified column is not of 
    an allowed type.

    Args:
        dataframe (pd.DataFrame): The DataFrame to check.
        allowed_types (Tuple[type]): The types that are allowed for the target 
            column values.
        target_col_header (str): The name of the column to check.
        return_col_header (Optional[str]): The name of the column to return. 
            If None, return list of items in the target_col_header with non-allowed
            types.

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

    non_allowed_rows = dataframe.apply(
        lambda row: not isinstance(
            row[target_col_header], allowed_types),
        axis=1)

    if return_col_header:
        return dataframe.loc[non_allowed_rows, return_col_header].tolist()

    return dataframe.loc[non_allowed_rows, target_col_header].tolist()
