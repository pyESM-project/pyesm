import os
import tempfile
import pytest

from pySM.src.util import *


def test_load_file():
    """Test function for the load_file() function.

    This function creates temporary files to test loading of JSON and YAML files.
    It checks that the function returns a dictionary with the expected data.
    It also checks that the function raises a ValueError when trying to load a non-existent file.
    """

    # Create a temporary directory and file for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, 'test.json')
        with open(file_path, 'w') as file:
            file.write('{"name": "Matteo", "age": 30}')

        # Test loading a JSON file
        result = load_file(
            file_name='test.json',
            file_type='json',
            folder_path=tmpdir)
        assert isinstance(result, dict)
        assert result == {'name': 'Matteo', 'age': 30}

        # Test loading a YAML file
        file_path = os.path.join(tmpdir, 'test.yaml')
        with open(file_path, 'w') as file:
            file.write('name: Matteo\nage: 25\n')

        result = load_file(
            file_name='test.yaml',
            file_type='yaml',
            folder_path=tmpdir)
        assert isinstance(result, dict)
        assert result == {'name': 'Matteo', 'age': 25}

        # Test loading a non-existent file
        with pytest.raises(FileNotFoundError, match=r'No such file or directory:'):
            load_file(
                file_name='nonexistent.json',
                file_type='json',
                folder_path=tmpdir)


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
    assert find_dict_depth({1: 1, 2: 2}) == 1
    assert find_dict_depth({1: {2: 2, 3: {4: 4, 5: 5}}, 6: 6}) == 3
    assert find_dict_depth({}) == 0
    assert find_dict_depth({1: {2: 'two', 3: (4, 5)}, 6: [7, 8]}) == 2
    assert find_dict_depth([]) == 0
    assert find_dict_depth('dictionary') == 0
