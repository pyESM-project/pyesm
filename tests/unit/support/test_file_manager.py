"""Unit tests for the FileManager class."""

from unittest.mock import Mock

import pandas as pd

from cvxlab.support.file_manager import FileManager
from cvxlab.support import util


def _file_manager_for_excel_tests() -> FileManager:
    """Create a minimal FileManager configured for openpyxl."""
    files = FileManager.__new__(FileManager)
    files.logger = Mock()
    files.xls_engine = "openpyxl"
    return files


def test_get_excel_sheet_names_preserves_workbook_order(tmp_path) -> None:
    """Excel sheet names are returned without parsing their data."""
    file_path = tmp_path / "inputs.xlsx"
    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        pd.DataFrame({"value": [1]}).to_excel(
            writer,
            sheet_name="demand",
            index=False,
        )
        pd.DataFrame({"value": [2]}).to_excel(
            writer,
            sheet_name="cost",
            index=False,
        )

    files = _file_manager_for_excel_tests()

    result = files.get_excel_sheet_names(
        excel_file_name=file_path.name,
        excel_file_dir_path=tmp_path,
    )

    assert result == ["demand", "cost"]


def test_dataframe_to_excel_adds_new_sheet_without_confirmation(
        tmp_path,
        monkeypatch,
) -> None:
    """Adding a sheet to an existing workbook is not an overwrite."""
    files = _file_manager_for_excel_tests()
    confirmation = Mock(return_value=False)
    monkeypatch.setattr(util, "get_user_confirmation", confirmation)

    files.dataframe_to_excel(
        dataframe=pd.DataFrame({"value": [1]}),
        excel_filename="inputs.xlsx",
        excel_dir_path=tmp_path,
        sheet_name="demand",
    )
    files.dataframe_to_excel(
        dataframe=pd.DataFrame({"value": [2]}),
        excel_filename="inputs.xlsx",
        excel_dir_path=tmp_path,
        sheet_name="cost",
    )

    confirmation.assert_not_called()
    assert files.get_excel_sheet_names(
        excel_file_name="inputs.xlsx",
        excel_file_dir_path=tmp_path,
    ) == ["demand", "cost"]


def test_dataframe_to_excel_preserves_sheet_when_overwrite_declined(
        tmp_path,
        monkeypatch,
) -> None:
    """An existing sheet remains unchanged when confirmation is declined."""
    files = _file_manager_for_excel_tests()
    files.dataframe_to_excel(
        dataframe=pd.DataFrame({"value": [1]}),
        excel_filename="inputs.xlsx",
        excel_dir_path=tmp_path,
        sheet_name="demand",
    )
    monkeypatch.setattr(
        util,
        "get_user_confirmation",
        Mock(return_value=False),
    )

    files.dataframe_to_excel(
        dataframe=pd.DataFrame({"value": [2]}),
        excel_filename="inputs.xlsx",
        excel_dir_path=tmp_path,
        sheet_name="demand",
        force_overwrite=False,
    )

    result = pd.read_excel(tmp_path / "inputs.xlsx", sheet_name="demand")
    assert result["value"].tolist() == [1]


def test_dataframe_to_excel_force_overwrites_without_confirmation(
        tmp_path,
        monkeypatch,
) -> None:
    """force_overwrite replaces an existing sheet without prompting."""
    files = _file_manager_for_excel_tests()
    files.dataframe_to_excel(
        dataframe=pd.DataFrame({"value": [1]}),
        excel_filename="inputs.xlsx",
        excel_dir_path=tmp_path,
        sheet_name="demand",
    )
    confirmation = Mock(return_value=False)
    monkeypatch.setattr(util, "get_user_confirmation", confirmation)

    files.dataframe_to_excel(
        dataframe=pd.DataFrame({"value": [2]}),
        excel_filename="inputs.xlsx",
        excel_dir_path=tmp_path,
        sheet_name="demand",
        force_overwrite=True,
    )

    confirmation.assert_not_called()
    result = pd.read_excel(tmp_path / "inputs.xlsx", sheet_name="demand")
    assert result["value"].tolist() == [2]
