import os
import tempfile
import pytest
from pySM.util.file_manager import FileManager


def test_load_file():
    """Test function for the load_file() function.

    This function creates temporary files to test loading of JSON and YAML files.
    It checks that the function returns a dictionary with the expected data.
    It also checks that the function raises a ValueError when trying to load a non-existent file.
    """

    files = FileManager()

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
