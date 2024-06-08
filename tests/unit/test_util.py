"""
test_util.py 

@author: Matteo V. Rocco
@institution: Politecnico di Milano

This module contains tests for the functions in the 'esm.support.util' module.
"""


import pytest
import pprint

from esm.support.util import *


def test_prettify(capfd):
    """
    Test the function 'prettify'.

    This test function uses pytest's capfd fixture to capture stdout and stderr.
    It tests 'prettify' with a set of test cases, each containing an input item,
    an expected output, and an expected exception (if any).

    Parameters
    ----------
    capfd : _pytest.capture.CaptureFixture
        Pytest fixture that can capture stdout and stderr.

    Raises
    ------
    AssertionError
        If the output of 'prettify' doesn't match the expected output.
    """
    test_cases = [
        ({'key1': 'value1', 'key2': 'value2'},
         pprint.pformat({'key1': 'value1', 'key2': 'value2'}) + '\n', None),
        ('not a dictionary', None, TypeError)
    ]

    for input_item, expected_output, expected_exception in test_cases:
        if expected_exception:
            with pytest.raises(expected_exception):
                prettify(input_item)
        else:
            prettify(input_item)
            out, err = capfd.readouterr()
            assert out == expected_output


def test_validate_selection():
    """
    Test the 'validate_selection' method.

    This test method checks the behavior of the validate_selection function
    under various scenarios, including valid and invalid selections, as well
    as empty valid selections and non-string selections.
    """
    test_cases = [
        (['option1', 'option2'], 'option2', None),  # valid selection
        (['option1', 'option2'], 'invalid_option', ValueError),  # invalid selection
        ([], 'option1', ValueError),  # no valid selections
        (['option1', 'option2'], 1, ValueError),  # integer selection
    ]

    for valid_selections, selection, expected_exception in test_cases:
        if expected_exception:
            with pytest.raises(expected_exception):
                validate_selection(valid_selections, selection)
        else:
            validate_selection(valid_selections, selection)


def test_validate_dict_structure():
    """
    Test the 'validate_dict_structure' method.

    This test function checks the behavior of the validate_dict_structure
    function against various dictionaries and validation structures. It asserts
    that the function returns the expected output based on the provided input.

    Test cases:
    - A dictionary with valid structure should return True.
    - A dictionary with an invalid structure should return False.
    - A dictionary with extra keys not present in the validation structure 
        should return False.
    """
    test_items = {
        1: {"key1": 1, "key2": "value"},
        2: {"key1": True, "key2": 2},
        3: {"key1": 1, "key2": {"subkey1": 1, "subkey2": 2}},
    }

    validation_structures = {
        1: {"key1": int, "key2": str},
        2: {"key1": bool, "key2": int},
        3: {"key1": int, "key2": dict},
    }

    expected_outputs = {
        1: True,
        2: True,
        3: True,
    }

    for key in test_items:
        assert validate_dict_structure(
            dictionary=test_items[key],
            validation_structure=validation_structures[key]
        ) == expected_outputs[key]


def test_confirm_action(monkeypatch):
    """
    Test the function 'confirm_action'.
    This test function checks the following scenarios:
    1. A valid case where the user confirms the action by entering 'y'.
    2. A valid case where the user denies the action by entering 'n'.

    The 'monkeypatch' fixture is used to simulate user input.

    Raises
    ------
    AssertionError
        If the output of 'confirm_action' doesn't match the expected output.
    """
    monkeypatch.setattr('builtins.input', lambda _: 'y')
    assert confirm_action("Confirm?") == True

    monkeypatch.setattr('builtins.input', lambda _: 'n')
    assert confirm_action("Confirm?") == False


def test_find_dict_depth():
    """
    Test for 'find_dict_depth' method.

    Test cases:
     - tests a dictionary with only 1 depth
     - tests a dictionary with 3 depth
     - tests an empty dictionary
     - tests a dictionary with other data types inside of it
     - tests a non-dictionary input
     - tests a non-dictionary input
    """

    test_items = {
        1: {1: 1, 2: 2},
        2: {1: {2: 2, 3: {4: 4, 5: 5}}, 6: 6},
        3: {},
        4: {1: {2: 'two', 3: (4, 5)}, 6: [7, 8]},
        5: [],
        6: 'dictionary',
    }

    expected_outputs = {
        1: 1,
        2: 3,
        3: 0,
        4: 2,
        5: 0,
        6: 0,
    }

    for item in test_items:
        assert find_dict_depth(test_items[item]) == expected_outputs[item]


def test_generate_dict_with_none_values():
    """
    Test the 'generate_dict_with_none_values' method.

    This test function checks the behavior of the generate_dict_with_none_values
    function against various input dictionaries. It asserts that the function
    returns the expected output dictionary where each key has a corresponding
    value of None.

    Test cases:
    - A nested dictionary with values should be converted to a dictionary with
        the same structure, where each key has a value of None.
    - An empty dictionary should return an empty dictionary.
    - A dictionary with non-nested values should return a dictionary with the
        same keys, each having a value of None.
    """

    test_items = [
        ({1: {2: {3: 'a', 4: 'b'}}}, {1: {2: {3: None, 4: None}}}),  # nested dict
        # non-nested dict
        ({'x': 1, 'y': 2, 'z': 3}, {'x': None, 'y': None, 'z': None}),
        ({}, {}),  # empty dict
    ]

    for item in test_items:
        assert generate_dict_with_none_values(item[0]) == item[1]


def test_pivot_dict():
    """
    Test the function 'pivot_dict'.

    This test function checks the following scenarios:
    1. A valid case where a dictionary is pivoted without specifying a keys order.
    2. A valid case where a dictionary is pivoted with a specified keys order.
    3. An invalid case where a non-existent key is included in the keys order.

    Raises
    ------
    AssertionError
        If the output of 'pivot_dict' doesn't match the expected output.
    ValueError
        If a non-existent key is included in the keys order.
    """
    data = {
        'key_1': ['item_1', 'item_2', 'item_3'],
        'key_2': [10, 20, 30]
    }

    # valid data input
    result = pivot_dict(data)
    expected_result = {
        'item_1': {10: None, 20: None, 30: None},
        'item_2': {10: None, 20: None, 30: None},
        'item_3': {10: None, 20: None, 30: None},
    }
    assert result == expected_result

    # valid data input with different keys_order
    result = pivot_dict(data, ['key_2', 'key_1'])
    expected_result = {
        10: {'item_1': None, 'item_2': None, 'item_3': None},
        20: {'item_1': None, 'item_2': None, 'item_3': None},
        30: {'item_1': None, 'item_2': None, 'item_3': None},
    }
    assert result == expected_result

    # invalid keys_order
    with pytest.raises(ValueError):
        pivot_dict(data, ['key3', 'key2'])


def test_unpivot_dict_to_dataframe():
    """
    Test cases:
    - Unpivot dict with unspecified key order.
    - Unpivot dict with key order as the same order of passed dict keys.
    - Unpivot dict with key order different compared to passed dict keys.
    - Unpivot dict with key order as subset of passed dict keys.
    - 
    """

    std_dict = {'A': [1, 2], 'B': [3, 4]}

    key_orders = {
        1: None,
        2: ['A', 'B'],
        3: ['B', 'A'],
        4: ['B'],
        5: ['Z'],
    }

    expected_outputs = {
        1: pd.DataFrame({'A': [1, 1, 2, 2], 'B': [3, 4, 3, 4]}),
        2: pd.DataFrame({'A': [1, 1, 2, 2], 'B': [3, 4, 3, 4]}),
        3: pd.DataFrame({'B': [3, 3, 4, 4], 'A': [1, 2, 1, 2]}),
        4: pd.DataFrame({'B': [3, 4]}),
        5: ValueError
    }

    for item, key_order in key_orders.items():

        if expected_outputs[item] is ValueError:
            with pytest.raises(ValueError):
                unpivot_dict_to_dataframe(
                    data_dict=std_dict,
                    key_order=key_order,
                )
        else:
            assert unpivot_dict_to_dataframe(
                data_dict=std_dict,
                key_order=key_order,
            ).equals(expected_outputs[item]), f"Failed on test case '{item}'"


def test_add_item_to_dict():
    """
    Test the function 'add_item_to_dict'.

    This test function checks the following scenarios:
    1. A valid case where a dictionary item is added at a specific position.
    2. A case where the position index is out of bounds.
    3. A case where the item to be added is not a dictionary.
    """
    dictionary = {'key1': 'value1', 'key2': 'value2'}

    # working case
    item = {'key3': 'value3'}
    position = 0
    result = add_item_to_dict(dictionary, item, position)
    expected_result = {**item, **dictionary}
    assert result == expected_result

    # position index out of bound
    with pytest.raises(ValueError):
        add_item_to_dict(dictionary, item, 10)

    # passing wrong item type
    with pytest.raises(TypeError):
        add_item_to_dict(dictionary, 'not_a_dictionary')
    with pytest.raises(TypeError):
        add_item_to_dict('not_a_dictionary', item)


def test_merge_series_to_dataframe():

    # valid inputs, default position
    series = pd.Series([1, 2, 3], index=['A', 'A1', 'A2'], name='A')
    dataframe = pd.DataFrame({'B': [4, 5, 6], 'C': [7, 8, 9]})
    result = merge_series_to_dataframe(series, dataframe)
    expected_result = pd.DataFrame(
        {'A': [1, 1, 1], 'A1': [2, 2, 2], 'A2': [3, 3, 3], 'B': [4, 5, 6], 'C': [7, 8, 9]})
    pd.testing.assert_frame_equal(result, expected_result)

    # valid inputs, position -1
    result = merge_series_to_dataframe(series, dataframe, -1)
    expected_result = pd.DataFrame(
        {'B': [4, 5, 6], 'C': [7, 8, 9], 'A': [1, 1, 1], 'A1': [2, 2, 2], 'A2': [3, 3, 3]})
    pd.testing.assert_frame_equal(result, expected_result)

    # empty series
    with pytest.raises(ValueError):
        merge_series_to_dataframe(pd.Series(), dataframe)

    # empty dataframe
    with pytest.raises(ValueError):
        merge_series_to_dataframe(series, pd.DataFrame())


def test_check_dataframes_equality():
    """
    Test the check_dataframes_equality function.
    This function creates several pairs of pandas DataFrames with different 
    characteristics (identical, same shape and headers but different values, 
    different column order, different row order, different headers, different 
    shapes) and checks if the check_dataframes_equality function correctly 
    identifies whether they are equal considering the specified conditions.
    """
    # identical dataframes
    df1 = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
    df2 = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
    assert check_dataframes_equality([df1, df2]) == True

    # dataframes with same shape and headers but different values
    df3 = pd.DataFrame({'A': [1, 2, 3], 'B': [7, 8, 9]})
    assert check_dataframes_equality([df1, df3]) == False

    # identical dataframes but different column order
    df4 = pd.DataFrame({'B': [4, 5, 6], 'A': [1, 2, 3]})
    assert check_dataframes_equality(
        [df1, df4], cols_order_matters=False) == True
    assert check_dataframes_equality(
        [df1, df4], cols_order_matters=True) == False

    # identical dataframes but different row order
    df5 = pd.DataFrame({'A': [3, 2, 1], 'B': [6, 5, 4]})
    assert check_dataframes_equality(
        [df1, df5], rows_order_matters=False) == True
    assert check_dataframes_equality(
        [df1, df5], rows_order_matters=True) == False

    # identical dataframe except for one column (skipped)
    df6 = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6], 'C': [7, 8, 9]})
    assert check_dataframes_equality([df1, df6], skip_columns=['C']) == True

    # dataframes with different headers
    df7 = pd.DataFrame({'D': [1, 2, 3], 'E': [4, 5, 6]})
    with pytest.raises(ValueError):
        check_dataframes_equality([df1, df7])

    # dataframes with different shapes
    with pytest.raises(ValueError):
        check_dataframes_equality([df1, df6], skip_columns=['A'])


def test_check_dataframe_columns_equality():
    """
    Test the check_dataframe_columns_equality function.
    This function creates several pairs of pandas DataFrames with different 
    column headers and checks if the check_dataframe_columns_equality function 
    correctly identifies whether they have the same set of columns. It also 
    tests the function's ability to ignore specified columns.
    """
    df1 = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    df2 = pd.DataFrame({'A': [5, 6], 'B': [7, 8]})
    df3 = pd.DataFrame({'A': [9, 10], 'C': [11, 12]})
    df4 = 'not_a_dataframe'
    df5 = pd.DataFrame()

    assert check_dataframe_columns_equality([df1, df2]) == True
    assert check_dataframe_columns_equality([df1, df3]) == False
    assert check_dataframe_columns_equality([df1, df2, df3]) == False
    assert check_dataframe_columns_equality(
        [df1, df2], skip_columns=['B']) == True
    assert check_dataframe_columns_equality(
        [df1, df3], skip_columns=['B', 'C']) == True

    with pytest.raises(TypeError):
        check_dataframe_columns_equality(
            [df1, df4], skip_columns=['B', 'C'])

    with pytest.raises(ValueError):
        check_dataframe_columns_equality([])

    with pytest.raises(ValueError):
        check_dataframe_columns_equality([df1, df5])


def test_add_column_to_dataframe():
    """
    Test the add_column_to_dataframe function.
    This function creates a pandas DataFrame and tests the add_column_to_dataframe 
    function by adding a new column to the DataFrame. It checks if the function 
    correctly adds the column, handles invalid input, and correctly returns 
    whether the column was added.
    """
    df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})

    # adding a new column with values
    assert add_column_to_dataframe(df, 'C', [7, 8, 9]) == True
    pd.testing.assert_frame_equal(
        df, pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6], 'C': [7, 8, 9]}))

    # adding a column header that already exists
    df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
    assert add_column_to_dataframe(df, 'A') == False

    # adding a new column with no values
    df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
    assert add_column_to_dataframe(df, 'C', None) == True
    pd.testing.assert_frame_equal(
        df, pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6], 'C': None}))

    # Test adding a column with invalid column_header
    with pytest.raises(TypeError):
        add_column_to_dataframe(df, 123)

    # Test adding a column with invalid dataframe
    with pytest.raises(TypeError):
        add_column_to_dataframe("not a dataframe", 'D')

    # Test adding a column with invalid column_position
    with pytest.raises(ValueError):
        add_column_to_dataframe(df, 'D', column_position=10)

    # Test adding a column with invalid number of values
    with pytest.raises(ValueError):
        add_column_to_dataframe(df, 'E', [1, 4])


def test_substitute_dict_keys():
    """
    Test the substitute_dict_keys function.
    This function tests the substitute_keys function with valid and invalid 
    input, and checks if the function correctly substitutes the keys, handles 
    invalid input, and raises the correct errors.
    """
    # valid input
    source_dict = {'A': 1, 'B': 2, 'C': 3}
    key_mapping_dict = {'A': 'X', 'B': 'Y', 'C': 'Z'}
    expected_dict = {'X': 1, 'Y': 2, 'Z': 3}
    assert substitute_dict_keys(source_dict, key_mapping_dict) == expected_dict

    # key that does not exist in source_dict
    source_dict = {'A': 1, 'B': 2, 'C': 3}
    with pytest.raises(ValueError):
        substitute_dict_keys(source_dict, {'D': 'W'})

    # not all keys exist in source_dict
    source_dict = {'A': 1, 'B': 2, 'C': 3}
    with pytest.raises(ValueError):
        substitute_dict_keys(source_dict, {'A': 'X', 'D': 'W'})

    # keys with invalid source_dict
    with pytest.raises(TypeError):
        substitute_dict_keys("not a dictionary", key_mapping_dict)

    # keys with invalid key_mapping_dict
    with pytest.raises(TypeError):
        substitute_dict_keys(source_dict, "not a dictionary")


def test_filter_dataframe():
    """
    Test the filter_dataframe function.
    This function tests the filter_dataframe function with valid and invalid 
    input, and checks if the function correctly filters the DataFrame, handles 
    invalid input, and raises the correct errors.
    """
    df = pd.DataFrame({
        'items': ['item_1', 'item_2', 'item_3', 'item_1', 'item_2', 'item_3'],
        'techs': ['tech_1', 'tech_1', 'tech_1', 'tech_2', 'tech_2', 'tech_2'],
        'values': [1, 2, 3, 4, 5, 6]
    })

    # filtering DataFrame with valid input
    filter_dict = {'items': ['item_1', 'item_2']}
    filtered_df = filter_dataframe(df, filter_dict)
    expected_df = pd.DataFrame({
        'items': ['item_1', 'item_2', 'item_1', 'item_2'],
        'techs': ['tech_1', 'tech_1', 'tech_2', 'tech_2'],
        'values': [1, 2, 4, 5]
    })
    pd.testing.assert_frame_equal(filtered_df, expected_df)

    # filtering DataFrame with different column order not preserving cols order
    filter_dict = {'techs': ['tech_1'], 'items': ['item_1', 'item_2']}
    filtered_df = filter_dataframe(df, filter_dict)
    expected_df = pd.DataFrame({
        'items': ['item_1', 'item_2'],
        'techs': ['tech_1', 'tech_1'],
        'values': [1, 2]
    })
    pd.testing.assert_frame_equal(filtered_df, expected_df)

    # filtering DataFrame with different column order cols preserving order
    filter_dict = {'techs': ['tech_2'], 'items': ['item_1', 'item_2']}
    filtered_df = filter_dataframe(
        df,
        filter_dict,
        reorder_cols_based_on_filter=True,
    )
    expected_df = pd.DataFrame({
        'techs': ['tech_2', 'tech_2'],
        'items': ['item_1', 'item_2'],
        'values': [4, 5]
    })
    pd.testing.assert_frame_equal(filtered_df, expected_df)

    # filtering DataFrame with different column order cols preserving order
    # and keeping the original dataframe index
    filter_dict = {'techs': ['tech_2'], 'items': ['item_1', 'item_2']}
    filtered_df = filter_dataframe(
        df,
        filter_dict,
        reset_index=False,
        reorder_cols_based_on_filter=True,
    )
    expected_df = pd.DataFrame({
        'techs': ['tech_2', 'tech_2'],
        'items': ['item_1', 'item_2'],
        'values': [4, 5]
    })
    expected_df.index = [3, 4]
    pd.testing.assert_frame_equal(filtered_df, expected_df)

    # filtering DataFrame with different rows order NOT preserving rows order
    filter_dict = {'items': ['item_2', 'item_1']}
    filtered_df = filter_dataframe(df, filter_dict)
    expected_df = pd.DataFrame({
        'items': ['item_1', 'item_2', 'item_1', 'item_2'],
        'techs': ['tech_1', 'tech_1', 'tech_2', 'tech_2'],
        'values': [1, 2, 4, 5]
    })
    pd.testing.assert_frame_equal(filtered_df, expected_df)

    # filtering DataFrame with different rows order preserving rows order
    filter_dict = {
        'items': ['item_2', 'item_1'],
        'techs': ['tech_2', 'tech_1']
    }
    filtered_df = filter_dataframe(
        df,
        filter_dict,
        reorder_rows_based_on_filter=True,
    )
    expected_df = pd.DataFrame({
        'items': ['item_2', 'item_2', 'item_1', 'item_1'],
        'techs': ['tech_2', 'tech_1', 'tech_2', 'tech_1'],
        'values': [5, 2, 4, 1]
    })
    pd.testing.assert_frame_equal(filtered_df, expected_df)

    # filtering DataFrame with different cols/rows order preserving filter
    # order and index
    filter_dict = {
        'techs': ['tech_2', 'tech_1'],
        'items': ['item_3', 'item_1'],
    }
    filtered_df = filter_dataframe(
        df,
        filter_dict,
        reset_index=False,
        reorder_rows_based_on_filter=True,
        reorder_cols_based_on_filter=True,
    )
    expected_df = pd.DataFrame({
        'techs': ['tech_2', 'tech_2', 'tech_1', 'tech_1'],
        'items': ['item_3', 'item_1', 'item_3', 'item_1'],
        'values': [6, 4, 3, 1]
    })
    expected_df.index = [5, 3, 2, 0]
    pd.testing.assert_frame_equal(filtered_df, expected_df)

    # filtering DataFrame with invalid filter_dict
    with pytest.raises(ValueError):
        filter_dataframe(df, {'D': ['apple', 'banana', 'cherry']})

    # filtering DataFrame with invalid df_to_filter
    with pytest.raises(ValueError):
        filter_dataframe("not a dataframe", filter_dict)


def test_compare_dicts_ignoring_order():
    """
    Test the compare_dicts_ignoring_order function.
    This function tests the compare_dicts_ignoring_order function with valid and 
    invalid input, and checks if the function correctly compares dictionaries, 
    handles invalid input, and raises the correct errors.
    """
    # comparing dictionaries with the same keys and values, but different order
    iterable = [
        {'A': [1, 2, 3], 'B': ['a', 'b', 'c']},
        {'A': [3, 2, 1], 'B': ['c', 'b', 'a']},
    ]
    assert compare_dicts_ignoring_order(iterable) == True

    # comparing dictionaries with different keys
    iterable = [
        {'A': [1, 2, 3], 'B': ['a', 'b', 'c']},
        {'A': [1, 2, 3], 'C': ['a', 'b', 'c'], 'D': [5, 5, 5, 7]},
    ]
    assert compare_dicts_ignoring_order(iterable) == False

    # comparing dictionaries with different values
    iterable = [
        {'A': [1, 2, 3], 'B': ['a', 'b', 'c']},
        {'A': [4, 5, 6], 'B': ['d', 'e', 'f']},
    ]
    assert compare_dicts_ignoring_order(iterable) == False

    # comparing dictionaries with invalid input
    with pytest.raises(ValueError):
        compare_dicts_ignoring_order(['not a dictionary', {}])

    with pytest.raises(ValueError):
        compare_dicts_ignoring_order('not a dictionary')


def test_find_non_allowed_types():
    """
    Test the find_non_allowed_types function.
    This function tests the find_non_allowed_types function with valid and 
    invalid input, and checks if the function correctly identifies rows with 
    non-allowed types, handles invalid input, and raises the correct errors.
    """
    # Test with valid input
    df = pd.DataFrame({'A': [1, 2, '3', 4], 'B': ['a', 'b', 'c', 'd']})
    assert find_non_allowed_types(
        dataframe=df,
        allowed_types=(int,),
        target_col_header='A',
        return_col_header='B'
    ) == ['c']

    # Test with no non-allowed types
    df = pd.DataFrame({'A': [1, 2, 3, 4], 'B': ['a', 'b', 'c', 'd']})
    assert find_non_allowed_types(
        dataframe=df,
        allowed_types=(int,),
        target_col_header='A',
        return_col_header='B'
    ) == []

    # Test with return_col_header=None
    df = pd.DataFrame({'A': [1, 2, '3', 4], 'B': ['a', 'b', 'c', 'd']})
    assert find_non_allowed_types(
        dataframe=df,
        allowed_types=(int,),
        target_col_header='A',
    ) == ['3']

    # Test with invalid input
    with pytest.raises(ValueError):
        find_non_allowed_types(
            dataframe='not a dataframe',
            allowed_types=(int,),
            target_col_header='A',
        )
    with pytest.raises(ValueError):
        find_non_allowed_types(
            dataframe=df,
            allowed_types='not a tuple',
            target_col_header='A',
        )
    with pytest.raises(ValueError):
        find_non_allowed_types(
            dataframe=df,
            allowed_types=(int,),
            target_col_header='not a column',
        )
    with pytest.raises(ValueError):
        find_non_allowed_types(
            dataframe=df,
            allowed_types=(int,),
            target_col_header='A',
            return_col_header='not a column',
        )


def test_find_dict_key_corresponding_to_value():
    """
    Test the function find_dict_key_corresponding_to_value.
    This function tests three scenarios: the target value exists in the 
    dictionary; the target value does not exist in the dictionary; the 
    provided argument is not a dictionary.

    Raises:
        TypeError: If the provided argument is not a dictionary.
    """
    dictionary = {'a': 1, 'b': 2, 'c': 3}

    # Test with a dictionary where the target value exists
    target_value = 2
    assert find_dict_keys_corresponding_to_value(
        dictionary, target_value) == 'b'

    # Test with a dictionary where the target value does not exist
    target_value = 4
    assert find_dict_keys_corresponding_to_value(
        dictionary, target_value) is None

    # Test with a non-dictionary argument
    with pytest.raises(TypeError):
        find_dict_keys_corresponding_to_value("not a dictionary", target_value)


def test_calulate_values_difference():
    # Test relative difference
    assert calculate_values_difference(10, 5) == 1.0
    assert calculate_values_difference(5, 10) == -0.5
    assert calculate_values_difference(0, 10) == -1.0
    assert calculate_values_difference(10, 0) == float('inf')

    # Test absolute difference
    assert calculate_values_difference(10, 5, False) == 5
    assert calculate_values_difference(5, 10, False) == -5
    assert calculate_values_difference(0, 10, False) == -10
    assert calculate_values_difference(10, 0, False) == 10

    # Test module of difference
    assert calculate_values_difference(10, 5, False, True) == 5
    assert calculate_values_difference(5, 10, False, True) == 5
    assert calculate_values_difference(0, 10, False, True) == 10
    assert calculate_values_difference(10, 0, False, True) == 10

    # Test with non-numeric values
    assert calculate_values_difference('a', 10, ignore_nan=True) is None
    assert calculate_values_difference(10, 'a', ignore_nan=True) is None
    assert calculate_values_difference('a', 'b', ignore_nan=True) is None

    # Test with None values
    assert calculate_values_difference(None, 10, ignore_nan=True) is None
    assert calculate_values_difference(10, None, ignore_nan=True) is None
    assert calculate_values_difference(None, None, ignore_nan=True) is None

    # Test ValueError when ignore_nan_values is False
    with pytest.raises(ValueError):
        calculate_values_difference('a', 10, True, False, False)
    with pytest.raises(ValueError):
        calculate_values_difference(10, 'a', True, False, False)
    with pytest.raises(ValueError):
        calculate_values_difference('a', 'b', True, False, False)
