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


@patch('builtins.input', lambda *args: 'y')
def test_dataframe_to_table_overwrite(
        sqlite_db: SQLManager,
        large_df: pd.DataFrame,
        benchmark,
):

    with db_handler(sqlite_db):
        sqlite_db.create_table(std_table_name, std_table_fields)

        def setup_and_run():
            sqlite_db.dataframe_to_table(
                table_name=std_table_name,
                dataframe=large_df,
                operation='overwrite',
            )

        benchmark(setup_and_run)
