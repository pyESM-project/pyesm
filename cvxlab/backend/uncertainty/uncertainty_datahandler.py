"""Utilities for uncertainty metadata and sampled exogenous data."""

from __future__ import annotations

from fileinput import filename
from typing import Any

import pandas as pd

from cvxlab.backend.index import Index
from cvxlab.defaults import Defaults
from cvxlab.log_exc import exceptions as exc
from cvxlab.log_exc.logger import Logger
from cvxlab.support.sql_manager import SQLManager, db_handler
from cvxlab.support.file_manager import FileManager
from cvxlab.backend.model_settings import ModelPaths


class UncertaintyData:
    """Manage row-level uncertainty metadata and sampled-value injection."""

    def __init__(
        self,
        *,
        files: FileManager,
        paths: ModelPaths,
        sqltools: SQLManager,
        index: Index,
        logger: Logger,
    ) -> None:
        """Initialize the uncertainty-data manager."""

        self.files = files
        self.paths = paths
        self.sqltools = sqltools
        self.index = index
        self.logger = logger

        self.uncertainty_defaults = Defaults.UncertaintySettings

    def _check_bounds(
        self,
        table_name: str,
        row_id: Any,
        lower: Any,
        upper: Any,
    ):
        """Validate lower and upper bounds for uncertain parameters."""

        lower_val = pd.to_numeric(lower, errors="coerce")
        upper_val = pd.to_numeric(upper, errors="coerce")

        if pd.isna(lower_val) or pd.isna(upper_val):
            raise ValueError(
                f"Missing bounds in table '{table_name}', id '{row_id}'. "
                f"{self.uncertainty_defaults.LOWER_BOUND_KEY}={lower}, "
                f"{self.uncertainty_defaults.UPPER_BOUND_KEY}={upper}"
            )

        if lower_val >= upper_val:
            raise ValueError(
                f"Invalid bounds in table '{table_name}', id '{row_id}'. "
                f"{self.uncertainty_defaults.LOWER_BOUND_KEY} >= "
                f"{self.uncertainty_defaults.UPPER_BOUND_KEY} "
                f"({lower_val} >= {upper_val})"
            )

    def get_uncertainty_measure_vars_list(self) -> list[str]:
        """Return variables selected as uncertainty-analysis output measures.

        The method scans the variables defined in the model index and returns
        the keys of those marked with
        ``uncertainty_measure=True``.

        Returns:
            list[str]: Variable keys selected as uncertainty-analysis output
            measures.

        Raises:
            exc.SettingsError: If no variable is marked as an uncertainty-analysis
                measure.
        """
        uncertainty_measures_list = [
            var_key
            for var_key, variable in self.index.variables.items()
            if getattr(
                variable,
                self.uncertainty_defaults.UNCERTAINTY_MEASURE_KEY,
                False,
            ) is True
        ]

        if not uncertainty_measures_list:
            raise exc.SettingsError(
                "Uncertainty analysis configuration invalid | "
                "No uncertainty measures are defined. "
                "At least one endogenous scalar variable must be marked with "
                f"'{self.uncertainty_defaults.UNCERTAINTY_MEASURE_KEY}=True'."
            )

        return uncertainty_measures_list

    def check_uncertainty_measure_variables_are_scalar(self) -> None:
        """Check that variables marked as uncertainty measures are scalar."""

        invalid_vars = {}

        uncertainty_measure_vars = self.get_uncertainty_measure_vars_list()

        for var_key in uncertainty_measure_vars:
            variable = self.index.variables[var_key]

            shape_size = variable.shape_size

            if not shape_size:
                invalid_vars[var_key] = "Shape not available."
                continue

            n_elements = 1
            for dim_size in shape_size:
                n_elements *= dim_size

            if n_elements != 1:
                invalid_vars[var_key] = f"shape_size={shape_size}"

        if invalid_vars:
            for var_key, info in invalid_vars.items():
                self.logger.error(
                    "Uncertainty measure validation | "
                    f"Variable '{var_key}' is marked as "
                    f"{self.uncertainty_defaults.UNCERTAINTY_MEASURE_KEY}=True "
                    f"but is not scalar ({info})."
                )

            raise exc.SettingsError(
                "Uncertainty measure validation failed | "
                f"Only scalar variables can be marked as "
                f"{self.uncertainty_defaults.UNCERTAINTY_MEASURE_KEY}=True."
            )

    def collect_uncertain_parameters(self) -> pd.DataFrame:
        """Collect uncertain parameters from uncertainty-enabled exogenous tables.

        The uncertainty definition is row-level. Each uncertain parameter is
        identified by the pair (table_name, id), where ``id`` is the row identifier
        in the source SQLite data table.

        Returns:
            pd.DataFrame:
                Mapping table with one row per uncertain sampled parameter. The
                dataframe includes the SALib parameter name, source table, row id,
                lower and upper bounds, optional uncertainty group, and all
                coordinate columns of the source table.

        Raises:
            exc.SettingsError:
                If required uncertainty columns are missing, if uncertain rows have
                invalid bounds, or if duplicate row ids are found inside an
                uncertainty-enabled table.
        """

        records: list[dict[str, Any]] = []

        id_col = Defaults.Labels.ID_FIELD["id"][0]
        values_col = Defaults.Labels.VALUES_FIELD["values"][0]

        is_uncertain_col = (
            self.uncertainty_defaults.IS_UNCERTAIN_FIELD[
                self.uncertainty_defaults.IS_UNCERTAIN_KEY
            ][0]
        )

        lower_col = (
            self.uncertainty_defaults.LOWER_BOUND_FIELD[
                self.uncertainty_defaults.LOWER_BOUND_KEY
            ][0]
        )

        upper_col = (
            self.uncertainty_defaults.UPPER_BOUND_FIELD[
                self.uncertainty_defaults.UPPER_BOUND_KEY
            ][0]
        )

        group_name_col = (
            self.uncertainty_defaults.UNCERTAINTY_GROUP_NAME_FIELD[
                self.uncertainty_defaults.UNCERTAINTY_GROUP_NAME_KEY
            ][0]
        )

        parameter_name_col = self.uncertainty_defaults.PARAMETER_NAME
        table_name_col = Defaults.Labels.TABLE_NAME

        lower_bound_key = self.uncertainty_defaults.LOWER_BOUND_KEY
        upper_bound_key = self.uncertainty_defaults.UPPER_BOUND_KEY
        group_name_key = (
            self.uncertainty_defaults.UNCERTAINTY_GROUP_NAME_KEY
        )

        technical_columns = {
            id_col,
            values_col,
            is_uncertain_col,
            lower_col,
            upper_col,
            group_name_col,
        }

        uncertainty_tables = {
            table_key: table
            for table_key, table in self.index.data.items()
            if table.uncertainty_enabled
        }

        if not uncertainty_tables:
            self.logger.warning(
                "Uncertainty analysis is enabled, but no data table has "
                "'uncertainty_enabled=True'."
            )
            return pd.DataFrame()

        with db_handler(self.sqltools):

            for table_name, table in uncertainty_tables.items():

                df = self.sqltools.table_to_dataframe(table_name=table_name)

                is_uncertain_mask = (
                    df[is_uncertain_col]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                    .eq("true")
                )

                uncertain_df = df.loc[is_uncertain_mask].copy()

                coordinate_columns = [
                    column
                    for column in df.columns
                    if column not in technical_columns
                ]

                for _, row in uncertain_df.iterrows():

                    row_id = row[id_col]

                    lower_val = pd.to_numeric(row[lower_col], errors="coerce")
                    upper_val = pd.to_numeric(row[upper_col], errors="coerce")

                    coordinate_values = {
                        column: row[column]
                        for column in coordinate_columns
                    }

                    group_name = row[group_name_col]

                    parameter_name = self.uncertainty_defaults.UNCERTAIN_PARAMETER_NAME_TEMPLATE.format(
                        table_name=table_name,
                        row_id=row_id,
                    )
                    records.append(
                        {
                            parameter_name_col: parameter_name,
                            table_name_col: table_name,
                            id_col: row_id,
                            lower_bound_key: lower_val,
                            upper_bound_key: upper_val,
                            group_name_key: group_name,
                            **coordinate_values,
                        }
                    )

        return pd.DataFrame(records)

    def validate_uncertainty_data(self) -> None:
        """Validate row-level uncertainty information.

            The check is performed only for tables with
            ``uncertainty_enabled=True``.

            A row is valid when:

            - both bounds are empty and ``is_uncertain`` is not TRUE; or
            - both bounds are defined and valid, and ``is_uncertain`` is TRUE.

            No value is modified automatically.

            Raises:
                exc.SettingsError: If uncertainty information is inconsistent.
        """
        is_uncertain_col = (
            self.uncertainty_defaults.IS_UNCERTAIN_FIELD[
                self.uncertainty_defaults.IS_UNCERTAIN_KEY
            ][0]
        )

        lower_bound_col = (
            self.uncertainty_defaults.LOWER_BOUND_FIELD[
                self.uncertainty_defaults.LOWER_BOUND_KEY
            ][0]
        )

        upper_bound_col = (
            self.uncertainty_defaults.UPPER_BOUND_FIELD[
                self.uncertainty_defaults.UPPER_BOUND_KEY
            ][0]
        )

        id_col = Defaults.Labels.ID_FIELD["id"][0]

        if not self.index.is_uncertainty_analysis:
            return

        uncertainty_tables = {
            table_name: table
            for table_name, table in self.index.data.items()
            if table.uncertainty_enabled
        }

        if not uncertainty_tables:
            self.logger.warning(
                "Uncertainty analysis is enabled, but no uncertain "
                "data tables were defined."
            )
            return

        problems = []

        with db_handler(self.sqltools):

            for table_name, table in uncertainty_tables.items():

                table_df = self.sqltools.table_to_dataframe(
                    table_name=table_name,
                )

                required_columns = {
                    id_col,
                    is_uncertain_col,
                    lower_bound_col,
                    upper_bound_col,
                }

                missing_columns = required_columns - set(table_df.columns)

                if missing_columns:
                    problems.append(
                        f"Table '{table_name}' is uncertainty-enabled but "
                        f"is missing columns: {sorted(missing_columns)}."
                    )
                    continue

                uncertain_col = (
                    table_df[is_uncertain_col]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                    .eq("true")
                )

                lower_values = pd.to_numeric(
                    table_df[lower_bound_col],
                    errors="coerce",
                )

                upper_values = pd.to_numeric(
                    table_df[upper_bound_col],
                    errors="coerce",
                )

                # Table-level check
                uncertain_table_mask = (
                    uncertain_col
                    & lower_values.notna()
                    & upper_values.notna()
                )

                if not uncertain_table_mask.any():
                    self.logger.warning(
                        f"Table '{table_name}' has uncertainty enabled, but no "
                        "uncertain parameters are defined."
                    )

                for row_idx, row in table_df.iterrows():

                    row_id = row[id_col]
                    lower = row[lower_bound_col]
                    upper = row[upper_bound_col]

                    is_uncertain = bool(uncertain_col.loc[row_idx])

                    lower_val = pd.to_numeric(
                        lower,
                        errors="coerce",
                    )
                    upper_val = pd.to_numeric(
                        upper,
                        errors="coerce",
                    )

                    has_lower = not pd.isna(lower_val)
                    has_upper = not pd.isna(upper_val)

                    # Only one bound is defined
                    if has_lower != has_upper:
                        problems.append(
                            f"Table '{table_name}', id '{row_id}': "
                            "lower_bound and upper_bound must either both be "
                            "defined or both be empty."
                        )
                        continue

                    bounds_defined = has_lower and has_upper

                    # Bounds require is_uncertain=TRUE
                    if bounds_defined and not is_uncertain:
                        problems.append(
                            f"Table '{table_name}', id '{row_id}': "
                            "bounds are defined but is_uncertain is not TRUE."
                        )
                        continue

                    # is_uncertain=TRUE requires bounds
                    if is_uncertain and not bounds_defined:
                        problems.append(
                            f"Table '{table_name}', id '{row_id}': "
                            "is_uncertain is TRUE but bounds are missing."
                        )
                        continue

                    # Validate numerical order only for uncertain rows
                    if is_uncertain:
                        try:
                            self._check_bounds(
                                table_name=table_name,
                                row_id=row_id,
                                lower=lower,
                                upper=upper,
                            )
                        except ValueError as error:
                            problems.append(str(error))

        if problems:
            for problem in problems:
                self.logger.error(
                    f"Uncertainty data validation | {problem}"
                )

            raise exc.SettingsError(
                "Uncertainty data validation failed. "
                "Check is_uncertain, lower_bound and upper_bound values."
            )

    def get_deterministic_values_df(
            self,
            table_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Return row ids with deterministic values.

            Rows marked as uncertain are excluded because their values are expected
            to be replaced by sampled values during uncertainty runs. If the
            ``is_uncertain`` column is not present, all rows are considered
            deterministic.

            Args:
                table_df: DataFrame containing the data table.
                table_name: Name of the data table, used in error messages.

            Returns:
                A copy of the rows that are not marked as deterministic.
        """
        is_uncertain_header = (
            self.uncertainty_defaults.IS_UNCERTAIN_FIELD[
                self.uncertainty_defaults.IS_UNCERTAIN_KEY
            ][0]
        )

        if is_uncertain_header not in table_df.columns:
            return table_df.copy()

        is_uncertain = (
            table_df[is_uncertain_header]
            .fillna(False)
            .astype(str)
            .str.strip()
            .str.lower()
            .isin({"true"})
        )

        deterministic_df = table_df.loc[~is_uncertain].copy()

        return deterministic_df

    def get_uncertain_tables(self) -> list[str]:
        """Return uncertainty-enabled tables containing uncertain database rows.."""
        allowed_var_types = Defaults.SymbolicDefinitions.VARIABLE_TYPES

        uncertain_tables = [
            table_key
            for table_key, table in self.index.data.items()
            if table.type not in [
                allowed_var_types["ENDOGENOUS"],
                allowed_var_types["CONSTANT"],
            ]
            and table.uncertainty_enabled
        ]

        return uncertain_tables

    def get_deterministic_tables(self) -> list[str]:
        """Return exogenous data tables containing no uncertain variables."""

        allowed_var_types = Defaults.SymbolicDefinitions.VARIABLE_TYPES

        deterministic_tables = [
            table_key
            for table_key, table in self.index.data.items()
            if table.type not in [
                allowed_var_types["ENDOGENOUS"],
                allowed_var_types["CONSTANT"],
            ]
            and not table.uncertainty_enabled
        ]

        return deterministic_tables

    def get_vars_in_tables_list(self, table_list: list[str]) -> list[str]:
        """Return variable keys whose related table is included in table_list."""

        allowed_var_types = Defaults.SymbolicDefinitions.VARIABLE_TYPES

        vars_list = []

        for var_key, variable in self.index.variables.items():
            if variable.related_table not in table_list:
                continue

            if variable.type in [
                allowed_var_types["ENDOGENOUS"],
                allowed_var_types["CONSTANT"],
            ]:
                continue

            vars_list.append(var_key)

        return sorted(set(vars_list))

    def inject_sampled_values_by_row(
        self,
        table_df: pd.DataFrame,
        samples_df: pd.DataFrame,
        run_id: int,
        table_name: str,
    ) -> pd.DataFrame:
        """Inject sampled values only in rows marked as uncertain.

        Rows with the uncertainty flag set to TRUE receive sampled values.
        All other rows keep their original DB values.
        """

        values_col = Defaults.Labels.VALUES_FIELD["values"][0]
        id_col = Defaults.Labels.ID_FIELD["id"][0]
        is_uncertain_col = self.uncertainty_defaults.IS_UNCERTAIN_FIELD[
            self.uncertainty_defaults.IS_UNCERTAIN_KEY
        ][0]

        resolved_df = table_df.copy()

        if is_uncertain_col not in resolved_df.columns:
            return resolved_df

        uncertain_mask = (
            resolved_df[is_uncertain_col]
            .astype(str)
            .str.lower()
            .eq("true")
        )

        if not uncertain_mask.any():
            return resolved_df

        run_id_col = self.uncertainty_defaults.RUN_ID

        samples_run = samples_df.loc[samples_df[run_id_col].eq(run_id)]

        sample_values = samples_run.drop(
            columns=[run_id_col]).iloc[0].to_dict()

        for idx in resolved_df.loc[uncertain_mask].index:
            row_id = resolved_df.at[idx, id_col]

            parameter_name = self.uncertainty_defaults.UNCERTAIN_PARAMETER_NAME_TEMPLATE.format(
                table_name=table_name,
                row_id=row_id,
            )

            resolved_df.at[idx, values_col] = sample_values[parameter_name]

        return resolved_df

    def load_samples_files(
        self,
        file_format: str,
    ) -> pd.DataFrame:
        """Load previously generated uncertainty samples."""

        file_name = (
            f"{self.uncertainty_defaults.SAMPLES_FILE_NAME}."
            f"{file_format}"
        )

        results_dir = (
            self.paths.model_dir
            / self.uncertainty_defaults.RESULTS_DIR
        )

        samples_df = self.files.file_to_dataframe(
            file_name=file_name,
            file_dir_path=results_dir,
        )

        return samples_df

    def load_temp_measures_files(
        self,
        file_format: str,
    ) -> pd.DataFrame:
        """Load temporary uncertainty measures from a previous run."""

        file_name = (
            f"{self.uncertainty_defaults.MEASURES_TEMP_FILE_NAME}."
            f"{file_format}"
        )

        results_dir = (
            self.paths.model_dir
            / self.uncertainty_defaults.RESULTS_DIR
        )

        try:
            measures_df = self.files.file_to_dataframe(
                file_name=file_name,
                file_dir_path=results_dir,
            )

        except FileNotFoundError as error:
            msg = (
                "Cannot resume uncertainty analysis because the temporary "
                f"measures file '{file_name}' was not found in "
                f"'{results_dir}'. \n Temporary results from a previous uncertainty "
                "run are required when 'resume=True'."
            )
            self.logger.error(msg)
            raise FileNotFoundError(msg) from error

        return measures_df

    def save_uncertainty_result(
        self,
        dataframe: pd.DataFrame,
        result_type: str,
        file_format: str,
    ):
        """Save an uncertainty-analysis dataframe in the results directory.

        The output file name is selected from the standard uncertainty-result
        names defined in ``self.uncertainty_defaults.RESULT_FILE_NAMES``.

        Args:
            dataframe: Uncertainty-analysis dataframe to export.
            result_type: Type of uncertainty result to save, such as ``samples``,
                ``measures``, ``temp_measures``, or ``gsa_results``.
            file_format: Output file format.

        Raises:
            TypeError: If ``dataframe`` is not a pandas DataFrame.
            ValueError: If ``result_type`` is unsupported.
        """
        if not isinstance(dataframe, pd.DataFrame):
            raise TypeError(
                "'dataframe' must be a pandas DataFrame. "
                f"Received type: '{type(dataframe).__name__}'."
            )

        try:
            file_name = self.uncertainty_defaults.RESULT_FILE_NAMES[result_type]
        except KeyError as error:
            raise ValueError(
                f"Unsupported uncertainty result type '{result_type}'. "
                "Available result types: "
                f"{sorted(self.uncertainty_defaults.RESULT_FILE_NAMES)}."
            ) from error

        output_path = (
            self.paths.model_dir
            / self.uncertainty_defaults.RESULTS_DIR
            / f"{file_name}.{file_format}"
        )

        return self.files.save_dataframe(
            dataframe=dataframe,
            output_path=output_path,
            file_format=file_format,
            sheet_name=file_name
        )
