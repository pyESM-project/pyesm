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
    pass
