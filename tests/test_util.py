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
        1: {"key1": {"subkey1": 1, "subkey2": "value"}},
        2: {"key1": {"subkey1": 1, "subkey2": 2}},
        3: {"key1": {"subkey1": 1, "subkey2": "value", "subkey3": "extra"}},
    }

    validation_structures = {
        1: {"subkey1": int, "subkey2": str},
        2: {"subkey1": int, "subkey2": str},
        3: {"subkey1": int, "subkey2": str},
    }

    expected_outputs = {
        1: True,
        2: False,
        3: False,
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

    test_items = [
        ({1: 1, 2: 2}, 1),
        ({1: {2: 2, 3: {4: 4, 5: 5}}, 6: 6}, 3),
        ({}, 0),
        ({1: {2: 'two', 3: (4, 5)}, 6: [7, 8]}, 2),
        ([], 0),
        ('dictionary', 0),
    ]

    for item in test_items:
        assert find_dict_depth(item[0]) == item[1]


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
