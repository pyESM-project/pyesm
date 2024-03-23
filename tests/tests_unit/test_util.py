import pytest
from esm.support.util import *


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
