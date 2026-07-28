"""Unit tests for the Database class."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call

import pandas as pd
import pytest

from cvxlab.backend.database import Database
from cvxlab.log_exc import exceptions as exc


def _database_for_input_loading(
        input_data_dir: Path,
        multiple_input_files: bool,
) -> Database:
    """Create a minimal Database instance for input-loading tests."""
    database = Database.__new__(Database)
    database.logger = Mock()
    database.files = Mock()
    database.sqltools = Mock()
    database.index = SimpleNamespace(
        list_exogenous_data_tables=["demand", "cost"],
        list_data_tables=["demand", "cost"],
    )
    database.settings = SimpleNamespace(
        input_data_files_type="xlsx",
        multiple_input_files=multiple_input_files,
    )
    database.paths = SimpleNamespace(input_data_dir=input_data_dir)
    return database


def test_load_single_input_file_parses_only_requested_sheets(tmp_path) -> None:
    """Valid unselected sheets are ignored during a partial refresh."""
    database = _database_for_input_loading(tmp_path, False)
    database.files.get_excel_sheet_names.return_value = ["demand", "cost"]
    database.files.excel_to_dataframes_dict.return_value = {
        "demand": pd.DataFrame({"value": [1]}),
    }

    database.load_data_input_files_to_database(["demand"])

    database.files.excel_to_dataframes_dict.assert_called_once_with(
        excel_file_dir_path=tmp_path,
        excel_file_name="input_data.xlsx",
        sheet_names=["demand"],
    )
    database.sqltools.dataframe_to_table.assert_called_once()
    assert (
        database.sqltools.dataframe_to_table.call_args.kwargs["table_name"]
        == "demand"
    )


def test_load_multiple_input_files_parses_only_requested_files(tmp_path) -> None:
    """Valid unselected files are ignored during a partial refresh."""
    database = _database_for_input_loading(tmp_path, True)
    (tmp_path / "demand.xlsx").touch()
    (tmp_path / "cost.xlsx").touch()
    database.files.file_to_dataframe.return_value = pd.DataFrame(
        {"value": [1]}
    )

    database.load_data_input_files_to_database(["demand"])

    database.files.file_to_dataframe.assert_called_once_with(
        file_name="demand.xlsx",
        file_dir_path=tmp_path,
    )
    database.sqltools.dataframe_to_table.assert_called_once()
    assert (
        database.sqltools.dataframe_to_table.call_args.kwargs["table_name"]
        == "demand"
    )


def test_load_input_data_collects_missing_and_invalid_keys(tmp_path) -> None:
    """Source-key errors are collected before any data is parsed or written."""
    database = _database_for_input_loading(tmp_path, False)
    database.files.get_excel_sheet_names.return_value = [
        "demand",
        "unknown",
    ]

    with pytest.raises(exc.SettingsError) as error:
        database.load_data_input_files_to_database(["demand", "cost"])

    assert str(error.value) == "Data table keys validation | Failed."
    assert database.logger.error.call_args_list == [
        call("Missing input data key(s): ['cost']."),
        call("Invalid input data key(s): ['unknown']."),
    ]
    database.files.excel_to_dataframes_dict.assert_not_called()
    database.sqltools.open_connection.assert_not_called()


def test_generate_excel_input_files_propagates_force_overwrite(tmp_path) -> None:
    """The overwrite choice is forwarded for every selected Excel sheet."""
    database = _database_for_input_loading(tmp_path, False)
    database.sqltools.table_to_dataframe.return_value = pd.DataFrame(
        {"value": [1]}
    )

    database.generate_blank_data_input_files(
        table_key_list=["demand", "cost"],
        force_overwrite=False,
    )

    assert database.files.dataframe_to_excel.call_count == 2
    assert all(
        call.kwargs["force_overwrite"] is False
        for call in database.files.dataframe_to_excel.call_args_list
    )


def test_generate_csv_input_files_propagates_force_overwrite(tmp_path) -> None:
    """The overwrite choice is forwarded to the CSV writer."""
    database = _database_for_input_loading(tmp_path, True)
    database.settings.input_data_files_type = "csv"
    database.sqltools.table_to_dataframe.return_value = pd.DataFrame(
        {"value": [1]}
    )

    database.generate_blank_data_input_files(
        table_key_list=["demand"],
        force_overwrite=True,
    )

    database.files.dataframe_to_csv.assert_called_once()
    assert (
        database.files.dataframe_to_csv.call_args.kwargs["force_overwrite"]
        is True
    )
