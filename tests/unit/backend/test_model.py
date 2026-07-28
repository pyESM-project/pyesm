"""Unit tests for the Model class."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from cvxlab.backend.model import Model
from cvxlab.log_exc import exceptions as exc


@pytest.fixture
def model_for_table_key_validation() -> Model:
    """Create a minimal Model instance for testing table-key validation."""
    model = Model.__new__(Model)
    model.logger = Mock()
    return model


@pytest.mark.parametrize("table_key_list", [None, []])
def test_setting_table_keys_uses_valid_keys_as_default(
        model_for_table_key_validation: Model,
        table_key_list,
) -> None:
    """None and an empty list select all valid table keys."""
    valid_table_keys = ["demand", "cost"]

    result = model_for_table_key_validation._setting_table_keys(
        table_key_list=table_key_list,
        valid_table_keys=valid_table_keys,
    )

    assert result == valid_table_keys
    assert result is not valid_table_keys


def test_setting_table_keys_returns_copy_of_valid_selection(
        model_for_table_key_validation: Model,
) -> None:
    """A valid explicit selection is returned as a defensive copy."""
    table_key_list = ["demand"]

    result = model_for_table_key_validation._setting_table_keys(
        table_key_list=table_key_list,
        valid_table_keys=["demand", "cost"],
    )

    assert result == table_key_list
    assert result is not table_key_list


@pytest.mark.parametrize(
    "table_key_list",
    [
        "demand",
        ("demand",),
        ["demand", 1],
    ],
)
def test_setting_table_keys_rejects_invalid_types(
        model_for_table_key_validation: Model,
        table_key_list,
) -> None:
    """Invalid container and item types raise TypeError and are logged."""
    with pytest.raises(TypeError):
        model_for_table_key_validation._setting_table_keys(
            table_key_list=table_key_list,
            valid_table_keys=["demand", "cost"],
        )

    model_for_table_key_validation.logger.error.assert_called_once()


def test_setting_table_keys_reports_only_invalid_keys(
        model_for_table_key_validation: Model,
) -> None:
    """The error identifies invalid keys without listing the valid scope."""
    with pytest.raises(
        exc.SettingsError,
        match=r"Invalid table key\(s\): \['unknown', 'other'\]\.",
    ):
        model_for_table_key_validation._setting_table_keys(
            table_key_list=["demand", "unknown", "other"],
            valid_table_keys=["demand", "cost"],
        )

    model_for_table_key_validation.logger.error.assert_called_once_with(
        "Invalid table key(s): ['unknown', 'other']."
    )


def test_generate_input_data_files_propagates_force_overwrite(tmp_path) -> None:
    """The public overwrite option is forwarded to the Database layer."""
    model = Model.__new__(Model)
    model.logger = Mock()
    model.logger.log_timing.return_value = nullcontext()
    model.paths = SimpleNamespace(input_data_dir=tmp_path)
    model.core = SimpleNamespace(
        index=SimpleNamespace(list_exogenous_data_tables=["demand"]),
        database=Mock(),
    )

    model.generate_input_data_files(
        table_key_list=["demand"],
        force_overwrite=True,
    )

    model.core.database.generate_blank_data_input_files.assert_called_once_with(
        table_key_list=["demand"],
        values_cleanup=True,
        force_overwrite=True,
    )
