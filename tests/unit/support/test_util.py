"""Test for the cvxlab/support/util.py module."""
from cvxlab.support.util import *
from tests.unit.conftest import run_test_cases


def test_get_user_confirmation(monkeypatch):
    """Test the function 'confirm_action'.

    The 'monkeypatch' fixture is used to simulate user input.
    """
    monkeypatch.setattr('builtins.input', lambda _: 'y')
    assert get_user_confirmation("Confirm?") == True

    monkeypatch.setattr('builtins.input', lambda _: 'n')
    assert get_user_confirmation("Confirm?") == False


def test_validate_selection():
    """Test the 'validate_selection' method."""

    test_cases = [
        ((['opt1', 'opt2'], 'opt2'), None, None),
        ((['opt1', 2], 2), None, None),
        ((['opt1', 'opt2'], 'OPT2'), None, None, {'ignore_case': True}),
        ((['opt1', 4], 'OPT1'), None, ValueError, {'ignore_case': True}),
        ((['opt1', 'opt2'], 'invalid_option'), None, ValueError),
        (([], None), None, ValueError),
        ((['opt1', 'opt2'], ['opt3, opt4']), None, TypeError)
    ]

    run_test_cases(validate_selection, test_cases)


def test_items_in_list():
    """Test the 'items_in_list' method."""
    test_cases = [
        (([2, 3], [1, 2, 3, 4, 5]), True, None),
        (({2, 3}, {1, 2, 3, 4, 5}), True, None),
        (((2, 3), [1, 2, 3, 4, 5]), True, None),
        ((['a', 'd'], ['a', 'b', 'c']), False, None),
        (([4, 5], (1, 2, 3)), False, None),
        (([1, 2], []), False, None),
        (([], [1, 2, 3]), False, None),
        (('str', [1, 2, 3]), None, TypeError),
        (((1, 2), 'not_a_control_list'), None, TypeError),
        (({'a': 1}, {'a': 2, 'b': 3}), True, None)
    ]

    run_test_cases(items_in_list, test_cases)


def test_find_dict_depth():
    """Test the 'find_dict_depth' method."""
    test_cases = [
        ({1: 1, 2: 2}, 1, None),
        ({1: {2: 2, 3: {4: 4, 5: 5}}, 6: 6}, 3, None),
        ({}, 0, None),
        ({1: {2: 'two', 3: (4, 5)}, 6: [7, 8]}, 2, None),
        ([], None, TypeError),
        ('dictionary', None, TypeError),
    ]

    run_test_cases(find_dict_depth, test_cases)


def test_pivot_dict():
    """Test the function 'pivot_dict'"""
    data = {
        'key_1': ['item_1', 'item_2', 'item_3'],
        'key_2': [10, 20, 30]
    }

    expected_default = {
        'item_1': {10: None, 20: None, 30: None},
        'item_2': {10: None, 20: None, 30: None},
        'item_3': {10: None, 20: None, 30: None},
    }

    expected_reordered = {
        10: {'item_1': None, 'item_2': None, 'item_3': None},
        20: {'item_1': None, 'item_2': None, 'item_3': None},
        30: {'item_1': None, 'item_2': None, 'item_3': None},
    }

    test_cases = [
        ((data,), expected_default, None),
        ((data,), expected_reordered, None, {
         'keys_order': ['key_2', 'key_1']}),
        ((data,), None, ValueError, {'keys_order': ['key3', 'key2']}),
    ]

    run_test_cases(pivot_dict, test_cases)


def test_dict_cartesian_product():
    """Test the 'dict_cartesian_product' function."""
    data_1 = {'A': [1, 2], 'B': ['x', 'y']}
    data_2 = {'X': [10]}
    data_3 = {'A': [1, 2, 3], 'B': ['a'], 'C': [True, False]}

    expected_with_keys = [
        {'A': 1, 'B': 'x'},
        {'A': 1, 'B': 'y'},
        {'A': 2, 'B': 'x'},
        {'A': 2, 'B': 'y'},
    ]

    expected_without_keys = [
        [1, 'x'],
        [1, 'y'],
        [2, 'x'],
        [2, 'y'],
    ]

    expected_single = [{'X': 10}]

    expected_multiple = [
        {'A': 1, 'B': 'a', 'C': True},
        {'A': 1, 'B': 'a', 'C': False},
        {'A': 2, 'B': 'a', 'C': True},
        {'A': 2, 'B': 'a', 'C': False},
        {'A': 3, 'B': 'a', 'C': True},
        {'A': 3, 'B': 'a', 'C': False},
    ]

    test_cases = [
        ((data_1,), expected_with_keys, None),
        ((data_1,), expected_without_keys, None, {'include_dict_keys': False}),
        (({},), [], None),
        ((data_2,), expected_single, None),
        ((data_3,), expected_multiple, None),
        (('not_a_dict',), None, TypeError),
        ((data_1,), None, TypeError, {'include_dict_keys': 'invalid'}),
    ]

    run_test_cases(dict_cartesian_product, test_cases)


def test_dict_values_cartesian_product():
    """Test the 'dict_values_cartesian_product' method.

    Test cases:
        - tests valid dictionaries 
        - tests an empty dictionary
        - tests a non-dictionary input
    """
    test_cases = [
        ({0: {'a', 'b', 'c', 'd'}}, 4, None),
        ({0: {'a', 'b'}, 1: {1, 2}}, 4, None),
        ({0: {'a', 'b', 'c'}, 1: {1, 2}}, 6, None),
        ({0: {'a', 'b', 'c'}, 1: {1, 2}, 3: {'d', 'e'}}, 12, None),
        ({0: {'a', 'b', 'c'}, 1: {1, 2}, 3: {}}, 0, None),
        ({}, 0, None),
        ('not_a_dict', None, TypeError),
    ]

    run_test_cases(dict_values_cartesian_product, test_cases)


def test_flattening_list():
    """Test the 'flattening_list' method."""
    nested_list = [1, [2, 3, [4]], 'a', ['b', ['c']], (5, 6)]

    test_cases = [
        ([[1, 2], [3]], [1, 2, 3], None),
        (nested_list, [1, 2, 3, 4, 'a', 'b', 'c', 5, 6], None),
        ('not_a_list', None, TypeError),
    ]

    run_test_cases(flattening_list, test_cases)


def test_unpivot_dict_to_dataframe():
    """Test the function 'unpivot_dict_to_dataframe'."""
    std_dict = {'A': [1, 2], 'B': [3, 4]}

    df_1 = pd.DataFrame({'A': [1, 1, 2, 2], 'B': [3, 4, 3, 4]})
    df_2 = pd.DataFrame({'A': [1, 1, 2, 2], 'B': [3, 4, 3, 4]})
    df_3 = pd.DataFrame({'B': [3, 3, 4, 4], 'A': [1, 2, 1, 2]})
    df_4 = pd.DataFrame({'B': [3, 4]})

    test_cases = [
        (std_dict, df_1, None),
        (std_dict, df_2, None, {'key_order': ['A', 'B']}),
        (std_dict, df_3, None, {'key_order': ['B', 'A']}),
        (std_dict, df_4, None, {'key_order': ['B']}),
        (std_dict, None, ValueError, {'key_order': ['Z']}),
        ('not_a_dict', None, TypeError),
        ({}, pd.DataFrame(), None),
    ]

    run_test_cases(unpivot_dict_to_dataframe, test_cases)


def test_add_item_to_dict():
    """Test the function 'add_item_to_dict'."""
    dictionary = {'key1': 'value1', 'key2': 'value2'}
    item = {'key3': 'value3'}
    expected_result = {**item, **dictionary}

    test_cases = [
        ((dictionary, item, 0), expected_result, None),
        ((dictionary, item, 10), None, ValueError),
        ((dictionary, 'not_a_dictionary'), None, TypeError),
        (('not_a_dictionary', item), None, TypeError),
    ]

    run_test_cases(add_item_to_dict, test_cases)


def test_check_dataframes_equality():
    """Test the 'check_dataframes_equality' function."""
    df1 = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
    df2 = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
    df3 = pd.DataFrame({'A': [1, 2, 3], 'B': [7, 8, 9]})
    df4 = pd.DataFrame({'B': [4, 5, 6], 'A': [1, 2, 3]})
    df5 = pd.DataFrame({'A': [3, 2, 1], 'B': [6, 5, 4]})
    df6 = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6], 'C': [7, 8, 9]})
    df7 = pd.DataFrame({'D': [1, 2, 3], 'E': [4, 5, 6]})
    df8 = pd.DataFrame()

    test_cases = [
        (([df1, df2],), True, None),
        (([df1, df3],), False, None),
        (([df1, df4],), True, None, {'cols_order_matters': False}),
        (([df1, df4],), False, None, {'cols_order_matters': True}),
        (([df1, df5],), True, None, {'rows_order_matters': False}),
        (([df1, df5],), False, None, {'rows_order_matters': True}),
        (([df1, df6],), True, None, {'skip_columns': ['C']}),
        (([df1, df7],), False, None),
        (([df1, df8],), False, None, {'skip_columns': ['A']}),
        (([df1, df6],), None, ValueError, {'skip_columns': ['column_2']}),
        (([df1, df3],), True, None, {'check_columns': ['A']}),
        (([df1, df5],), False, None, {
         'check_columns': ['A'], 'rows_order_matters': True}),
    ]

    run_test_cases(check_dataframes_equality, test_cases)


def test_check_dataframe_columns_equality():
    """Test the check_dataframe_columns_equality function."""
    df1 = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
    df2 = pd.DataFrame({'A': [5, 6], 'B': [7, 8]})
    df3 = pd.DataFrame({'A': [9, 10], 'C': [11, 12]})
    df4 = 'not_a_dataframe'
    df5 = pd.DataFrame()

    test_cases = [
        (([df1, df2],), True, None),
        (([df1, df3],), False, None),
        (([df1, df2, df3],), False, None),
        (([df1, df2],), True, None, {'skip_columns': ['B']}),
        (([df1, df3],), True, None, {'skip_columns': ['B', 'C']}),
        (([df1, df4],), None, TypeError, {'skip_columns': ['B', 'C']}),
        (([],), None, ValueError),
        (([df1, df5],), False, None),
    ]

    run_test_cases(check_dataframe_columns_equality, test_cases)


def test_add_column_to_dataframe():
    """Test the 'add_column_to_dataframe' function."""
    df_base = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
    df_col_c = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6], 'C': [7, 8, 9]})
    df_none = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6], 'C': None})
    df_empty_expected = pd.DataFrame({'A': [None]}, index=[0])

    test_cases = [
        # Adding new column with values
        ((df_base.copy(), 'C', [7, 8, 9]), df_col_c, None),
        # Adding column that already exists (no change)
        ((df_base.copy(), 'A'), df_base, None),
        # Adding new column with None values
        ((df_base.copy(), 'C', None), df_none, None),
        # Passing an empty dataframe must return a dataframe with one index row (0)
        ((pd.DataFrame(), 'A', None), df_empty_expected, None),
        # Invalid column_header type
        ((df_base.copy(), 123), None, TypeError),
        # Invalid dataframe input
        (("not a dataframe", 'D'), None, TypeError),
        # Invalid column_position out of bounds
        ((df_base.copy(), 'D', None, 10), None, ValueError),
        # Invalid number of values (length mismatch)
        ((df_base.copy(), 'E', [1, 4]), None, ValueError),
    ]

    run_test_cases(add_column_to_dataframe, test_cases)


def test_substitute_dict_keys():
    """Test the substitute_dict_keys function."""
    source_dict = {'A': 1, 'B': 2, 'C': 3}
    key_mapping_dict = {'A': 'X', 'B': 'Y', 'C': 'Z'}
    expected_dict = {'X': 1, 'Y': 2, 'Z': 3}

    test_cases = [
        ((source_dict, key_mapping_dict), expected_dict, None),
        ((source_dict, {'D': 'W'}), None, ValueError),
        ((source_dict, {'A': 'X', 'D': 'W'}), None, ValueError),
        (("not a dictionary", key_mapping_dict), None, TypeError),
        ((source_dict, "not a dictionary"), None, TypeError),
    ]

    run_test_cases(substitute_dict_keys, test_cases)


def test_fetch_dict_primary_key():
    """
    Test the fetch_dict_primary_key function.

    This function tests various scenarios:
    - Finding a single matching primary key
    """
    dict_single = {
        'key1': {'dim': 'rows'},
        'key2': {'dim': 'cols'},
    }
    dict_multiple = {
        'key1': {'dim': 'rows'},
        'key2': {'dim': 'cols'},
        'key3': {'dim': 'rows'},
    }
    dict_not_nested = {
        'key1': 'not_a_dict',
    }
    not_a_dict = 'not_a_dict'

    test_cases = [
        ((dict_single, 'dim', 'rows'), ['key1'], None),
        ((dict_single, 'dim', 'cols'), ['key2'], None),
        ((dict_single, 'dim', 'depth'), [], None),
        ((dict_multiple, 'dim', 'rows'), ['key1', 'key3'], None),
        ((dict_multiple, 'dim', 'cols'), ['key2'], None),
        ((dict_multiple, 'dim', 'depth'), [], None),
        ((dict_not_nested, 'dim', 'rows'), [], None),
        ((not_a_dict, 'dim', 'rows'), None, TypeError),
    ]

    run_test_cases(fetch_dict_primary_key, test_cases)


def test_filter_dataframe():
    """Test the filter_dataframe function."""
    df = pd.DataFrame({
        'items': ['item_1', 'item_2', 'item_3', 'item_1', 'item_2', 'item_3'],
        'techs': ['tech_1', 'tech_1', 'tech_1', 'tech_2', 'tech_2', 'tech_2'],
        'values': [1, 2, 3, 4, 5, 6]
    })

    expected_1 = pd.DataFrame({
        'items': ['item_1', 'item_2', 'item_1', 'item_2'],
        'techs': ['tech_1', 'tech_1', 'tech_2', 'tech_2'],
        'values': [1, 2, 4, 5]
    })

    expected_2 = pd.DataFrame({
        'items': ['item_1', 'item_2'],
        'techs': ['tech_1', 'tech_1'],
        'values': [1, 2]
    })

    expected_3 = pd.DataFrame({
        'techs': ['tech_2', 'tech_2'],
        'items': ['item_1', 'item_2'],
        'values': [4, 5]
    })

    expected_4 = pd.DataFrame({
        'techs': ['tech_2', 'tech_2'],
        'items': ['item_1', 'item_2'],
        'values': [4, 5]
    })
    expected_4.index = [3, 4]

    expected_5 = pd.DataFrame({
        'items': ['item_2', 'item_2', 'item_1', 'item_1'],
        'techs': ['tech_2', 'tech_1', 'tech_2', 'tech_1'],
        'values': [5, 2, 4, 1]
    })

    expected_6 = pd.DataFrame({
        'techs': ['tech_2', 'tech_2', 'tech_1', 'tech_1'],
        'items': ['item_3', 'item_1', 'item_3', 'item_1'],
        'values': [6, 4, 3, 1]
    })
    expected_6.index = [5, 3, 2, 0]

    test_cases = [
        ((df.copy(), {'items': ['item_1', 'item_2']}), expected_1, None),
        ((df.copy(), {'techs': ['tech_1'], 'items': [
         'item_1', 'item_2']}), expected_2, None),
        ((df.copy(), {'techs': ['tech_2'], 'items': ['item_1', 'item_2']}), expected_3, None,
         {'reorder_cols_based_on_filter': True}),
        ((df.copy(), {'techs': ['tech_2'], 'items': ['item_1', 'item_2']}), expected_4, None,
         {'reset_index': False, 'reorder_cols_based_on_filter': True}),
        ((df.copy(), {'items': ['item_2', 'item_1']}), expected_1, None),
        ((df.copy(), {'items': ['item_2', 'item_1'], 'techs': ['tech_2', 'tech_1']}), expected_5, None,
         {'reorder_rows_based_on_filter': True}),
        ((df.copy(), {'techs': ['tech_2', 'tech_1'], 'items': ['item_3', 'item_1']}), expected_6, None,
         {'reset_index': False, 'reorder_rows_based_on_filter': True, 'reorder_cols_based_on_filter': True}),
        ((df.copy(), {'D': ['apple', 'banana', 'cherry']}), None, ValueError),
        (("not a dataframe", {'items': ['item_1']}), None, ValueError),
    ]

    run_test_cases(filter_dataframe, test_cases)


def test_find_non_allowed_types():
    """Test the find_non_allowed_types function."""
    allowed_types = (int, float)

    df1 = pd.DataFrame({'A': [1, 2, '3', 4], 'B': ['a', 'b', 'c', 'd']})
    df2 = pd.DataFrame({'A': [1, 2, 3, 4], 'B': ['a', 'b', 'c', 'd']})
    df3 = pd.DataFrame({'A': [1, None, '3', 4], 'B': ['a', 'b', 'c', 'd']})
    df4 = pd.DataFrame({'A': [1, None, 3, 4], 'B': ['a', 'b', 'c', 'd']})

    test_cases = [
        # Valid input with non-allowed types
        ((df1, allowed_types, 'A', 'B'), ['c'], None),
        # No non-allowed types
        ((df2, allowed_types, 'A', 'B'), [], None),
        # return_col_header=None
        ((df1, allowed_types, 'A'), ['3'], None),
        # allow_none=True
        ((df3, allowed_types, 'A', 'B'), ['c'], None, {'allow_none': True}),
        # allow_none=False
        ((df4, allowed_types, 'A', 'B'), ['b'], None, {'allow_none': False}),
        # Invalid dataframe
        (('not a dataframe', allowed_types, 'A'), None, ValueError),
        # Invalid allowed_types
        ((df1, 'not a tuple', 'A'), None, ValueError),
        # Invalid target_col_header
        ((df1, allowed_types, 'not a column'), None, ValueError),
        # Invalid return_col_header
        ((df1, allowed_types, 'A', 'not a column'), None, ValueError),
    ]

    run_test_cases(find_non_allowed_types, test_cases)


def test_find_dict_key_corresponding_to_value():
    """Test the function find_dict_keys_corresponding_to_value."""
    dictionary = {'a': 1, 'b': 2, 'c': 2, 'd': 3}

    test_cases = [
        ((dictionary, 2), ['b', 'c'], None),
        ((dictionary, 4), [], None),
        (("not a dictionary", 2), None, TypeError),
    ]

    run_test_cases(find_dict_keys_corresponding_to_value, test_cases)


def test_calulate_values_difference():
    """Test the calculate_values_difference function."""
    test_cases = [
        # Relative difference
        ((10, 5), 1.0, None),
        ((5, 10), -0.5, None),
        ((0, 10), -1.0, None),
        ((10, 0), float('inf'), None),

        # Absolute difference
        ((10, 5, False), 5, None),
        ((5, 10, False), -5, None),
        ((0, 10, False), -10, None),
        ((10, 0, False), 10, None),

        # Module of difference
        ((10, 5, False, True), 5, None),
        ((5, 10, False, True), 5, None),
        ((0, 10, False, True), 10, None),
        ((10, 0, False, True), 10, None),

        # Non-numeric values with ignore_nan=True
        (('a', 10), None, None, {'ignore_nan': True}),
        ((10, 'a'), None, None, {'ignore_nan': True}),
        (('a', 'b'), None, None, {'ignore_nan': True}),

        # None values with ignore_nan=True
        ((None, 10), None, None, {'ignore_nan': True}),
        ((10, None), None, None, {'ignore_nan': True}),
        ((None, None), None, None, {'ignore_nan': True}),

        # ValueError when ignore_nan=False
        (('a', 10, True, False, False), None, ValueError),
        ((10, 'a', True, False, False), None, ValueError),
        (('a', 'b', True, False, False), None, ValueError),
    ]

    run_test_cases(calculate_values_difference, test_cases)


def test_remove_empty_items_from_dict():
    """
    Test the remove_empty_items_from_dict function.

    This test verifies that the remove_empty_items_from_dict function correctly removes
    empty items from a nested dictionary based on default empty values and custom empty values.
    """
    input_dict = {
        'a': 1,
        'b': '',
        'c': None,
        'd': {
            'e': 2,
            'f': '',
            'g': {
                'h': 3,
                'i': None
            },
            'j': [],
        },
        'k': {},
        'l': 'non-empty',
    }

    expected_default = {
        'a': 1,
        'd': {
            'e': 2,
            'g': {
                'h': 3,
            },
        },
        'l': 'non-empty',
    }

    expected_custom = {
        'a': 1,
        'b': '',
        'c': None,
        'd': {
            'e': 2,
            'f': '',
            'g': {
                'h': 3,
                'i': None
            },
            'j': [],
        },
        'l': 'non-empty',
    }

    test_cases = [
        ((input_dict,), expected_default, None),
        ((input_dict,), expected_custom, None, {'empty_values': [{}]}),
        (('not a dictionary',), None, TypeError),
        ((input_dict,), None, ValueError, {
         'empty_values': ['not in default']}),
    ]

    run_test_cases(remove_empty_items_from_dict, test_cases)


def test_merge_dicts():
    """Test the merge_dicts function.

    Test cases:
        - Merge multiple dictionaries with overlapping keys (allow duplicates)
        - Merge multiple dictionaries with unique_values=True
        - Merge dictionaries with None values (should skip None)
        - Merge empty dictionaries
        - Merge dictionaries with non-iterable values (convert to list)
        - Merge dictionaries with string values (keep atomic)
        - Merge dictionaries with bytes values (keep atomic)
        - Single dictionary in list
        - Empty list of dictionaries
    """
    dict1 = {'a': [1, 2], 'b': [3]}
    dict2 = {'a': [2, 3], 'c': [4]}
    dict3 = {'a': [1], 'b': [5], 'd': [6]}

    # Expected results
    expected_merged = {'a': [1, 2, 2, 3, 1], 'b': [3, 5], 'c': [4], 'd': [6]}
    expected_unique = {'a': [1, 2, 3], 'b': [3, 5], 'c': [4], 'd': [6]}
    expected_with_none = {'a': [1, 2], 'b': [3]}
    expected_single = {'x': [10], 'y': [20]}
    expected_scalar = {'a': [1, 2], 'b': ['text'], 'c': [True]}

    test_cases = [
        # Merge with duplicates allowed
        (([dict1, dict2, dict3],), expected_merged, None),

        # Merge with unique values only
        (([dict1, dict2, dict3],), expected_unique,
         None, {'unique_values': True}),

        # Merge with None values (should be skipped)
        (([{'a': [1, 2], 'b': None}, {'a': None, 'b': [3]}],),
         expected_with_none, None),

        # Empty dictionaries
        (([{}, {}],), {}, None),

        # Non-iterable values converted to list
        (([{'a': 1, 'b': 'text', 'c': True}, {'a': 2}],), expected_scalar, None),

        # String values kept atomic
        (([{'text': 'hello'}, {'text': 'world'}],),
         {'text': ['hello', 'world']}, None),

        # Bytes values kept atomic
        (([{'data': b'abc'}, {'data': b'def'}],),
         {'data': [b'abc', b'def']}, None),

        # Single dictionary
        (([{'x': [10], 'y': [20]}],), expected_single, None),

        # Empty list
        (([],), {}, None),

        # List with None dictionaries
        (([None, {'a': [1]}, None],), {'a': [1]}, None),
    ]

    run_test_cases(merge_dicts, test_cases)


def test_transform_dict_none_to_values():
    """Test the transform_dict_none_to_values function.

    Test cases:
        - Transform None values to a specified value (string)
        - Transform None values to a specified value (integer)
        - Transform None values to a specified value (empty dict)
        - Dictionary with no None values (no transformation)
        - Empty dictionary
        - Invalid input: non-dictionary (TypeError)
    """

    dict_with_nones = {'a': 1, 'b': None, 'c': 'text', 'd': None}
    dict_no_nones = {'a': 1, 'b': 2, 'c': 'text'}

    expected_to_zero = {'a': 1, 'b': 0, 'c': 'text', 'd': 0}
    expected_to_empty_str = {'a': 1, 'b': '', 'c': 'text', 'd': ''}
    expected_to_dict = {'a': 1, 'b': {}, 'c': 'text', 'd': {}}

    test_cases = [
        ((dict_with_nones, 0), expected_to_zero, None),
        ((dict_with_nones, ''), expected_to_empty_str, None),
        ((dict_with_nones, {}), expected_to_dict, None),
        ((dict_no_nones, 0), dict_no_nones, None),
        (({}, 'any_value'), {}, None),
        (('not a dictionary', 0), None, TypeError),
    ]

    run_test_cases(transform_dict_none_to_values, test_cases)


def test_pivot_dataframe_to_data_structure():

    data = {
        'set_structure': {
            'set_key': ['resources', 'products', 'product_data'],
            'description': ['environmental transactions', 'products of the system', 'ancillary data'],
            'split_problem': ['TRUE', None, None],
            'copy_from': [None, None, None],
            'filters': [None, None, "{category: [energy_use_0, learning_rate, profit]}"]
        },

        'data_table_structure': {
            'table_key': ['x', 'a', 'product_data', 'product_data', 'product_data', 'b'],
            'description': [
                'products supply',
                'energy use',
                'product data',
                'product data',
                'product data',
                'energy availability',
            ],
            'type': [
                "1: 'endogenous', 2: 'exogenous'",
                "1: 'endogenous', 2: 'exogenous'",
                'exogenous',
                'exogenous',
                'exogenous',
                'exogenous',
            ],
            'integer': [None, None, None, None, None, None],
            'coordinates': [
                'resources, products',
                'resources, products',
                'products, product_data',
                'products, product_data',
                'products, product_data',
                'resources',
            ],
            'variables_info': ['x', 'a', 'c', 'a_0', 'lr', 'b'],
            'value': [None, None, None, None, None, None],
            'products': [
                "dim: cols",
                "dim: cols",
                "dim: cols",
                "dim: cols",
                "dim: cols",
                None,
            ],
            'resources': [None, None, None, None, None, None],
            'product_data': [
                None,
                None,
                "dim: rows, filters: {category: profit}",
                "dim: rows, filters: {category: energy_use_0}",
                "dim: rows, filters: {category: learning_rate}",
                None,
            ],
        },
        'problem_structure': {
            'problem_key': [1, 1, 1, 2],
            'objective': ['Maximize(c @ tran(x))', None, None, None],
            'expressions': [
                None,
                "a @ tran(x) - b <= 0",
                "x >= 0",
                "a - a_0 - lr @ diag(x) == 0",
            ],
        },
    }

    parameters = {
        'set_structure': {'primary_key': 'set_key', 'secondary_key': None, 'merge_dict': None},
        'data_table_structure': {'primary_key': 'table_key', 'secondary_key': 'variables_info', 'merge_dict': None},
        'problem_structure': {'primary_key': 'problem_key', 'secondary_key': None, 'merge_dict': True},
    }

    expected_structure = {
        'set_structure': {
            'resources': {
                'description': 'environmental transactions',
                'split_problem': True
            },
            'products': {
                'description': 'products of the system'
            },
            'product_data': {
                'description': 'ancillary data',
                'filters': {
                    'category': ['energy_use_0', 'learning_rate', 'profit']
                }
            }
        },
        'data_table_structure': {
            'x': {
                'description': 'products supply',
                'type': {1: 'endogenous', 2: 'exogenous'},
                'coordinates': ['resources', 'products'],
                'variables_info': {'x': {'products': {'dim': 'cols'}}}
            },
            'a': {
                'description': 'energy use',
                'type': {1: 'endogenous', 2: 'exogenous'},
                'coordinates': ['resources', 'products'],
                'variables_info': {'a': {'products': {'dim': 'cols'}}}
            },
            'product_data': {
                'description': 'product data',
                'type': 'exogenous',
                'coordinates': ['products', 'product_data'],
                'variables_info': {
                    'c': {
                        'product_data': {'dim': 'rows', 'filters': {'category': 'profit'}},
                        'products': {'dim': 'cols'}
                    },
                    'a_0': {
                        'product_data': {'dim': 'rows', 'filters': {'category': 'energy_use_0'}},
                        'products': {'dim': 'cols'}
                    },
                    'lr': {
                        'product_data': {'dim': 'rows', 'filters': {'category': 'learning_rate'}},
                        'products': {'dim': 'cols'}
                    }
                },
            },
            'b': {
                'description': 'energy availability',
                'type': 'exogenous',
                'coordinates': 'resources',
                'variables_info': {'b': {}},
            },
        },
        'problem_structure': {
            1: {
                'objective': ['Maximize(c @ tran(x))'],
                'expressions': [
                    'a @ tran(x) - b <= 0',
                    'x >= 0',
                ],
            },
            2: {
                'expressions': ['a - a_0 - lr @ diag(x) == 0'],
            },
        },
    }

    for key, value in data.items():

        structure = pivot_dataframe_to_data_structure(
            data=pd.DataFrame(value),
            primary_key=parameters[key].get('primary_key'),
            secondary_key=parameters[key].get('secondary_key'),
            merge_dict=parameters[key].get('merge_dict'),
        )

        assert structure == expected_structure[key]


def test_is_sparse():
    """Test the is_sparse function.

    Test cases:
        - Array with proportion of zeros above threshold (should be sparse)
        - Array with proportion of zeros below threshold (should not be sparse)
        - Array with proportion of zeros equal to threshold (should be sparse)
        - Array with all zeros (should return False - edge case)
        - Array with no zeros (should not be sparse)
        - Array with exactly at threshold
    """
    # Array with 70% zeros (above 50% threshold)
    array_70_zeros = np.array([0, 0, 0, 0, 0, 0, 0, 1, 2, 3])
    # Array with 30% zeros (below 50% threshold)
    array_30_zeros = np.array([0, 0, 0, 1, 2, 3, 4, 5, 6, 7])
    # Array with exactly 50% zeros
    array_50_zeros = np.array([0, 0, 0, 0, 0, 1, 2, 3, 4, 5])
    # Array with all zeros
    array_all_zeros = np.array([0, 0, 0, 0, 0])
    # Array with no zeros
    array_no_zeros = np.array([1, 2, 3, 4, 5])

    test_cases = [
        # Sparse: 70% zeros with 0.5 threshold
        ((array_70_zeros, 0.5), True, None),
        # Not sparse: 30% zeros with 0.5 threshold
        ((array_30_zeros, 0.5), False, None),
        # Sparse: exactly at threshold (50% zeros, 0.5 threshold)
        ((array_50_zeros, 0.5), True, None),
        # Edge case: all zeros should return False
        ((array_all_zeros, 0.5), False, None),
        # Not sparse: no zeros
        ((array_no_zeros, 0.5), False, None),
        # Sparse with lower threshold
        ((array_30_zeros, 0.2), True, None),
        # Not sparse with higher threshold
        ((array_70_zeros, 0.8), False, None),
        # Invalid input: non-numeric array
        (('not_an_array', 0.5), None, TypeError),
        # Invalid input: threshold out of bounds
        ((array_70_zeros, 1.5), None, ValueError),
        ((array_70_zeros, -0.1), None, ValueError),
    ]

    run_test_cases(is_sparse, test_cases)


# def test_normalize_dataframe():
#     """Test the normalize_dataframe function.

#     Test cases:
#         - Basic normalization with NaN replacement
#         - Exclude specific columns from NaN replacement
#         - Cast numeric columns to specific dtype
#         - Replace NaNs and fill with specific value
#         - Replace NaNs with various sentinel values
#         - Invalid input: non-DataFrame (TypeError)
#         - Invalid exclude_columns (ValueError)
#         - Invalid numeric_columns (ValueError)
#         - Missing numeric_dtype when numeric_columns provided (ValueError)
#     """
#     # Base DataFrame with various NaN-like values
#     df_with_nans = pd.DataFrame({
#         'A': [1, 2, np.nan, 4],
#         'B': ['x', 'NaN', 'null', 'y'],
#         'C': [10.5, 'NA', 'na', 15.5],
#         'D': [100, 200, 300, 400]
#     })
#     # Expected: NaNs replaced with None
#     expected_basic = pd.DataFrame({
#         'A': [1.0, 2.0, np.nan, 4.0],
#         'B': ['x', None, None, 'y'],
#         'C': [10.5, np.nan, np.nan, 15.5],
#         'D': [100, 200, 300, 400]
#     })
#     # Expected: NaNs replaced, then filled with 0
#     expected_with_fill = pd.DataFrame({
#         'A': [1.0, 2.0, 0.0, 4.0],
#         'B': ['x', 0, 0, 'y'],
#         'C': [10.5, 0, 0, 15.5],
#         'D': [100, 200, 300, 400]
#     })
#     # Expected: Exclude column 'B' from NaN replacement
#     expected_exclude = pd.DataFrame({
#         'A': [1.0, 2.0, None, 4.0],
#         'B': ['x', 'NaN', 'null', 'y'],
#         'C': [10.5, None, None, 15.5],
#         'D': [100, 200, 300, 400]
#     })
#     # DataFrame for numeric casting
#     df_numeric = pd.DataFrame({
#         'A': ['1', '2', '3', '4'],
#         'B': ['10.5', '20.5', '30.5', '40.5'],
#         'C': ['x', 'y', 'z', 'w']
#     })

#     expected_numeric = pd.DataFrame({
#         'A': [1.0, 2.0, 3.0, 4.0],
#         'B': [10.5, 20.5, 30.5, 40.5],
#         'C': ['x', 'y', 'z', 'w']
#     })

#     test_cases = [
#         # Basic NaN replacement
#         ((df_with_nans.copy(),), expected_basic, None),
#         # NaN replacement with fill value
#         ((df_with_nans.copy(),), expected_with_fill, None,
#          {'nan_fill_value': 0}),
#         # Exclude columns from NaN replacement
#         ((df_with_nans.copy(),), expected_exclude, None,
#          {'exclude_columns': ['B']}),
#         # Cast numeric columns
#         ((df_numeric.copy(),), expected_numeric, None,
#          {'numeric_columns': ['A', 'B'], 'numeric_dtype': float}),
#         # No NaN replacement
#         ((df_with_nans.copy(),), df_with_nans.copy(), None,
#          {'replace_nans': False}),
#         # Invalid input: non-DataFrame
#         (('not a dataframe',), None, TypeError),
#         # Invalid exclude_columns
#         ((df_with_nans.copy(),), None, ValueError,
#          {'exclude_columns': ['NonExistent']}),
#         # Invalid numeric_columns
#         ((df_with_nans.copy(),), None, ValueError,
#          {'numeric_columns': ['NonExistent'], 'numeric_dtype': float}),
#         # Missing numeric_dtype
#         ((df_with_nans.copy(),), None, ValueError,
#          {'numeric_columns': ['A']}),
#     ]

#     run_test_cases(normalize_dataframe, test_cases)
