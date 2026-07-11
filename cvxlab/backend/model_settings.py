"""Module defining ModelSettings and ModelPaths: validated containers for model configuration.

All path computation and settings-consistency checks are consolidated here.
``ModelSettings`` validates operational flags on construction; ``ModelPaths``
computes derived paths and validates the model-directory layout.
"""
from __future__ import annotations

from pathlib import Path

from cvxlab.defaults import Defaults
from cvxlab.log_exc import exceptions as exc
from cvxlab.log_exc.logger import Logger
from cvxlab.support import util


class ModelSettings:
    """Validated container for model operational settings.

    Accepts the raw keyword arguments from :class:`Model.__init__`, runs all
    consistency checks, and stores only clean, normalized values as plain
    attributes.

    Raises:
        exc.SettingsError: If any settings combination is invalid.
    """

    def __init__(
        self,
        *,
        logger: Logger,
        log_level: Defaults.LiteralTypes.LogLevel,
        model_name: str,
        model_settings_from: Defaults.LiteralTypes.SettingsSource,
        use_existing_data: bool,
        multiple_input_files: bool,
        input_data_files_type: Defaults.LiteralTypes.DataFileType,
        detailed_validation: bool,
    ) -> None:
        """Validate and store model settings.

        Args:
            logger: Logger instance (used only during construction).
            log_level: Logging verbosity level.
            model_name: Name of the model directory.
            model_settings_from: Format of the model settings source file
                ('yml' or 'xlsx').
            use_existing_data: Whether to rely on a pre-existing database and
                input files instead of generating fresh ones.
            multiple_input_files: Whether input data is split into one file per
                data table instead of a single multi-tab file.
            input_data_files_type: Format of input data files ('xlsx' or 'csv').
            detailed_validation: Whether to emit verbose validation logs.

        Raises:
            exc.SettingsError: If any settings combination is invalid.
        """
        err_msg: list[str] = []

        # CSV input files require multiple_input_files=True
        if input_data_files_type == 'csv' and not multiple_input_files:
            err_msg.append(
                "Input data files of type 'csv' can only be used when "
                "'multiple_input_files' setting is True."
            )

        # Add further checks below...

        if err_msg:
            for msg in err_msg:
                logger.error(msg)
            raise exc.SettingsError("Model settings validation | Failed.")

        logger.debug("Model settings validation | Success.")

        self.log_level = log_level
        self.model_name = model_name
        self.model_settings_from = model_settings_from
        self.use_existing_data = use_existing_data
        self.multiple_input_files = multiple_input_files
        self.input_data_files_type = input_data_files_type
        self.detailed_validation = detailed_validation

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"model_name='{self.model_name}', "
            f"model_settings_from='{self.model_settings_from}', "
            f"use_existing_data={self.use_existing_data})"
        )


class ModelPaths:
    """Validated container for model file-system paths.

    Computes all derived paths from *model_dir_path* and validates that the
    model directory contains the files and sub-directories required by the
    current settings.

    Raises:
        exc.SettingsError: If the model directory or any required file is
            missing.
    """

    def __init__(
        self,
        *,
        logger: Logger,
        model_dir_path: Path,
        model_settings_from: Defaults.LiteralTypes.SettingsSource,
        use_existing_data: bool,
    ) -> None:
        """Compute paths and validate the model directory layout.

        Args:
            logger: Logger instance (used only during construction).
            model_dir_path: Absolute path to the model directory.
            model_settings_from: Settings source format, used to determine
                which setup files must be present ('yml' or 'xlsx').
            use_existing_data: When ``True``, also checks for the sets Excel
                file, SQLite database, and input-data directory.

        Raises:
            exc.SettingsError: If the model directory or a required file /
                sub-directory is missing.
        """
        config = Defaults.ConfigFiles

        self.model_dir = model_dir_path
        self.input_data_dir = model_dir_path / config.INPUT_DATA_DIR
        self.sets_excel_file = model_dir_path / config.SETS_FILE
        self.sqlite_database = model_dir_path / config.SQLITE_DATABASE_FILE

        # Validate the settings-source selection before checking files
        util.validate_selection(
            valid_selections=config.AVAILABLE_SETUP_SOURCES,
            selection=model_settings_from,
        )

        files_to_check: list[str] = []
        subdir_to_check: list[str] = []

        if model_settings_from == 'yml':
            files_to_check += [
                file + '.yml'
                for file in config.SETUP_INFO.values()
            ]
        elif model_settings_from == 'xlsx':
            files_to_check += [config.SETUP_XLSX_FILE]

        if use_existing_data:
            files_to_check += [
                config.SETS_FILE,
                config.SQLITE_DATABASE_FILE,
            ]
            subdir_to_check += [config.INPUT_DATA_DIR]

        if not model_dir_path.exists():
            logger.error(
                "Model directory validation | Model directory is missing."
            )
            raise exc.SettingsError("Model directory validation | Failed.")

        err_msg: list[str] = []

        for subdir in subdir_to_check:
            if not (model_dir_path / subdir).exists():
                err_msg.append(
                    f"Model directory validation | '{subdir}' directory is missing."
                )

        for file in files_to_check:
            if not (model_dir_path / file).exists():
                err_msg.append(
                    f"Model directory validation | '{file}' file is missing."
                )

        if err_msg:
            for msg in err_msg:
                logger.error(msg)
            raise exc.SettingsError("Model directory validation | Failed.")

        logger.debug("Model directory validation | Success.")

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"model_dir='{self.model_dir}')"
        )
