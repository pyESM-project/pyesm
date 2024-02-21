from src.support.util import *


def test_find_dict_depth():
    """
    Test for find_dict_depth() function.

    This script:
     - tests a dictionary with only 1 depth
     - tests a dictionary with 3 depth
     - tests an empty dictionary
     - tests a dictionary with other data types inside of it
     - tests a non-dictionary input
     - tests a non-dictionary input
    """

    test_items = [
        [{1: 1, 2: 2}, 1],
        [{1: {2: 2, 3: {4: 4, 5: 5}}, 6: 6}, 3],
        [{}, 0],
        [{1: {2: 'two', 3: (4, 5)}, 6: [7, 8]}, 2],
        [[], 0],
        ['dictionary', 0],
    ]

    for item in test_items:
        assert find_dict_depth(item[0]) == item[1]
