from pathlib import Path
from unittest.mock import patch

import pandas as pd
import numpy as np
import pytest

from esm.log_exc.logger import Logger
from esm.support.sql_manager import SQLManager, db_handler


std_table_name = 'test_table'
std_table_fields = {
    'id': ['id', 'INTEGER PRIMARY KEY'],
    'name': ['name', 'TEXT'],
    'value': ['value', 'REAL'],
}


@pytest.fixture
def sqlite_db():

    manager = SQLManager(
        logger=Logger(__name__),
        database_path=Path(':memory:'),
        database_name='test_db',
    )

    return manager


@pytest.fixture
def small_df():
    np.random.seed(0)
    return pd.DataFrame({
        'id': np.arange(10),
        'name': np.random.choice(['a', 'b', 'c'], 10),
        'value': np.random.randn(10)
    })


@pytest.fixture
def large_df():
    np.random.seed(0)
    return pd.DataFrame({
        'id': np.arange(10000),
        'name': np.random.choice(['a', 'b', 'c'], 10000),
        'value': np.random.randn(10000)
    })
