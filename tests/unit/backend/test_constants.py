"""Unit tests for the Defaults class in cvxlab.defaults module."""

from cvxlab.defaults import Defaults
from tests.unit.conftest import run_test_cases


def test_getattr_method():
    """Test the '__getattr__' method of the Defaults class."""

    test_cases = [
        ('SETUP_XLSX_FILE', 'model_settings.xlsx', None),
        ('NAME', 'name', None),
        ('NON_EXISTENT_CONSTANT', None, AttributeError),
        ('ALLOWED_TEXT_TYPE', str, None),
    ]

    run_test_cases(Defaults.__getattr__, test_cases)
