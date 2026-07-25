import pytest

from tests.unit.conftest import run_test_cases
from cvxlab.backend.data_table import DataTable
from cvxlab.log_exc.logger import Logger


@pytest.fixture
def logger():
    return Logger("test_logger")


@pytest.fixture
def minimal_table_info():
    return {
        "description": "Test table",
        "type": "test_type",
        "domain": None,
        "coordinates": ["x", "y"],
        "variables_info": {"var1": {}, "var2": {}, },
    }


def test_initialization_and_attributes(logger, minimal_table_info):
    dt = DataTable(logger, "test_table", **minimal_table_info)

    assert dt.name == "test_table"
    assert dt.description == "Test table"
    assert dt.type == "test_type"
    assert dt.domain is None
    assert isinstance(dt.coordinates, list)
    assert set(dt.variables_list) == {"var1", "var2"}
