"""Tools for collecting uncertain parameters from exogenous data tables."""

from tokenize import group
from typing import Any, Dict, List, Tuple

import pandas as pd
import numpy as np
from typing import Any, Callable
import inspect
from SALib.sample import sobol, latin, morris
from SALib.analyze import (
    sobol as sobol_analyze,
    morris as morris_analyze,
    delta,
    rbd_fast,
)
from cvxlab.defaults import Defaults
from cvxlab.backend.index import Index
from cvxlab.support.sql_manager import SQLManager, db_handler
from cvxlab.log_exc import exceptions as exc
from cvxlab.log_exc.logger import Logger


class Uncertainty:

    """Manage data sampling and global sensitivity analysis workflows for 
    uncertain model parameters.

    The class implements the uncertainty-analysis layer of CVXLab. It maps
    row-level uncertain parameters data stored in SQLite tables to SALib format,
    validates parameters' uncertain bounds and uncertainty metadata, constructs 
    a Salib format sampling problems, generates sample matrices, injects sampled 
    values into CVXPY parameters,collects scalar model outputs, and executes
    results' global sensitivity analyses..

    Attributes:
        sqltools: SQLite manager used to read and update model data tables.
        index: Model index containing data tables, variables, sets and scenario
            metadata.
        paths: Model paths, including the model directory and result folders.
        logger: Child logger used for uncertainty-related validation and
            execution messages.

    Class Attributes:
        SAMPLERS: Mapping between supported sampling-method names and SALib
            sampling functions.
        ANALYZERS: Mapping between supported GSA-method names and SALib
            analyzer functions.
        ANALYZER_REQUIRED_INPUTS: Positional inputs supplied internally to each
            analyzer and therefore excluded from user-defined keyword
            arguments.
    """
    SAMPLERS: dict[str, Callable] = {
        Defaults.UncertaintySettings.SOBOL: sobol.sample,
        Defaults.UncertaintySettings.LATIN: latin.sample,
        Defaults.UncertaintySettings.MORRIS: morris.sample,
    }

    ANALYZERS: dict[str, Callable] = {
        Defaults.UncertaintySettings.SOBOL: sobol_analyze.analyze,
        Defaults.UncertaintySettings.MORRIS: morris_analyze.analyze,
        Defaults.UncertaintySettings.DELTA: delta.analyze,
        Defaults.UncertaintySettings.RBD_FAST: rbd_fast.analyze,
    }

    ANALYZER_REQUIRED_INPUTS = Defaults.UncertaintySettings.ANALYZER_REQUIRED_INPUTS

    def __init__(self,
                 sqltools: SQLManager,
                 index: Index,
                 paths: Dict,
                 logger: Logger
                 ):
        """Initialize the uncertainty-analysis manager.

        Args:
            sqltools: SQLite manager used to retrieve and update data-table values.
            index: Model index containing uncertainty-enabled tables, variables,
                sets and scenario information.
            paths: Dictionary-like object containing model and result paths.
            logger: Parent logger from which the uncertainty-specific child logger
                is created.
        """

        self.sqltools = sqltools
        self.index = index
        self.paths = paths
        self.logger = logger.get_child(__name__)

    def collect_uncertain_parameters_old(self) -> pd.DataFrame:
        """Collect uncertain parameters from uncertainty-enabled exogenous tables.

        Returns a mapping table with one row per uncertain sampled parameter.
        The table includes the SALib parameter name, source table, row id,
        variable name, bounds, and one column per coordinate.
        """

        records: list[dict[str, Any]] = []

        id_col = Defaults.Labels.ID_FIELD["id"][0]
        values_col = Defaults.Labels.VALUES_FIELD["values"][0]

        is_uncertain_col = Defaults.UncertaintySettings.IS_UNCERTAIN_FIELD[
            Defaults.UncertaintySettings.IS_UNCERTAIN_KEY
        ][0]
        lower_col = Defaults.UncertaintySettings.LOWER_BOUND_FIELD[
            Defaults.UncertaintySettings.LOWER_BOUND_KEY
        ][0]
        upper_col = Defaults.UncertaintySettings.UPPER_BOUND_FIELD[
            Defaults.UncertaintySettings.UPPER_BOUND_KEY
        ][0]

        group_name_col = (
            Defaults.UncertaintySettings.UNCERTAINTY_GROUP_NAME_FIELD[
                Defaults.UncertaintySettings.UNCERTAINTY_GROUP_NAME_KEY
            ][0]
        )

        parameter_name_col = Defaults.UncertaintySettings.PARAMETER_NAME
        table_name_col = Defaults.Labels.TABLE_NAME
        variable_name_col = Defaults.Labels.VARIABLE_NAME

        technical_columns = {
            id_col,
            values_col,
            is_uncertain_col,
            lower_col,
            upper_col,
            group_name_col,
        }

        if not self.index.is_uncertainty_analysis:
            return pd.DataFrame()

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

                uncertain_df = df[
                    df[is_uncertain_col].astype(str).str.lower().eq("true")
                ]

                coordinate_columns = [
                    column
                    for column in df.columns
                    if column not in technical_columns
                ]

                var_keys = [
                    var_key
                    for var_key, variable in self.index.variables.items()
                    if variable.related_table == table_name
                ]

                for _, row in uncertain_df.iterrows():

                    row_id = row[id_col]
                    matched_var_keys = []

                    for var_key in var_keys:

                        variable = self.index.variables[var_key]

                        matches_variable = True

                        for header, allowed_values in variable.all_coordinates_w_headers.items():
                            if row[header] not in allowed_values:
                                matches_variable = False
                                break

                        if matches_variable:
                            matched_var_keys.append(var_key)

                    if len(matched_var_keys) != 1:
                        raise exc.OperationalError(
                            "Uncertain-parameter mapping failed | "
                            f"Table '{table_name}', id '{row_id}' matches "
                            f"{len(matched_var_keys)} uncertain variables: "
                            f"{matched_var_keys}. Expected exactly one."
                        )

                    variable_name = matched_var_keys[0]

                    coordinate_values = {
                        column: row[column]
                        for column in coordinate_columns
                    }

                    lower_val = pd.to_numeric(row[lower_col], errors="coerce")
                    upper_val = pd.to_numeric(row[upper_col], errors="coerce")
                    group_name = row[group_name_col]

                    records.append(
                        {
                            parameter_name_col: self._build_parameter_name(
                                table_name=table_name,
                                row_id=row_id,
                            ),
                            table_name_col: table_name,
                            id_col: row_id,
                            variable_name_col: variable_name,
                            Defaults.UncertaintySettings.LOWER_BOUND_KEY: lower_val,
                            Defaults.UncertaintySettings.UPPER_BOUND_KEY: upper_val,
                            Defaults.UncertaintySettings.UNCERTAINTY_GROUP_NAME_KEY: group_name,
                            **coordinate_values,

                        }
                    )

            return pd.DataFrame(records)

        mapping_df = pd.DataFrame(
            records,
            columns=[
                parameter_name_col,
                table_name_col,
                "id",
                Defaults.UncertaintySettings.LOWER_BOUND_KEY,
                Defaults.UncertaintySettings.UPPER_BOUND_KEY,
            ],
        )

        return mapping_df

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
            Defaults.UncertaintySettings.IS_UNCERTAIN_FIELD[
                Defaults.UncertaintySettings.IS_UNCERTAIN_KEY
            ][0]
        )

        lower_col = (
            Defaults.UncertaintySettings.LOWER_BOUND_FIELD[
                Defaults.UncertaintySettings.LOWER_BOUND_KEY
            ][0]
        )

        upper_col = (
            Defaults.UncertaintySettings.UPPER_BOUND_FIELD[
                Defaults.UncertaintySettings.UPPER_BOUND_KEY
            ][0]
        )

        group_name_col = (
            Defaults.UncertaintySettings.UNCERTAINTY_GROUP_NAME_FIELD[
                Defaults.UncertaintySettings.UNCERTAINTY_GROUP_NAME_KEY
            ][0]
        )

        parameter_name_col = Defaults.UncertaintySettings.PARAMETER_NAME
        table_name_col = Defaults.Labels.TABLE_NAME

        lower_bound_key = Defaults.UncertaintySettings.LOWER_BOUND_KEY
        upper_bound_key = Defaults.UncertaintySettings.UPPER_BOUND_KEY
        group_name_key = (
            Defaults.UncertaintySettings.UNCERTAINTY_GROUP_NAME_KEY
        )

        technical_columns = {
            id_col,
            values_col,
            is_uncertain_col,
            lower_col,
            upper_col,
            group_name_col,
        }

        if not self.index.is_uncertainty_analysis:
            return pd.DataFrame()

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

        required_columns = {
            id_col,
            is_uncertain_col,
            lower_col,
            upper_col,
            group_name_col,
        }

        with db_handler(self.sqltools):

            for table_name, table in uncertainty_tables.items():

                df = self.sqltools.table_to_dataframe(table_name=table_name)

                missing_columns = required_columns.difference(df.columns)
                if missing_columns:
                    raise exc.SettingsError(
                        "Uncertainty parameter collection failed | "
                        f"Table '{table_name}' is uncertainty-enabled but is "
                        f"missing required columns: {sorted(missing_columns)}."
                    )

                if df[id_col].duplicated().any():
                    duplicated_ids = (
                        df.loc[df[id_col].duplicated(), id_col]
                        .dropna()
                        .tolist()
                    )
                    raise exc.SettingsError(
                        "Uncertainty parameter collection failed | "
                        f"Table '{table_name}' contains duplicated ids: "
                        f"{duplicated_ids}."
                    )

                is_uncertain_mask = (
                    df[is_uncertain_col]
                    .astype(str)
                    .str.strip()
                    .str.lower()
                    .isin(["true"])
                )

                uncertain_df = df.loc[is_uncertain_mask].copy()

                if uncertain_df.empty:
                    continue

                coordinate_columns = [
                    column
                    for column in df.columns
                    if column not in technical_columns
                ]

                for _, row in uncertain_df.iterrows():

                    row_id = row[id_col]

                    lower_val = pd.to_numeric(row[lower_col], errors="coerce")
                    upper_val = pd.to_numeric(row[upper_col], errors="coerce")

                    if pd.isna(lower_val) or pd.isna(upper_val):
                        raise exc.SettingsError(
                            "Uncertainty parameter collection failed | "
                            f"Table '{table_name}', id '{row_id}' is marked as "
                            "uncertain but has missing or non-numeric bounds. "
                            f"lower_bound='{row[lower_col]}', "
                            f"upper_bound='{row[upper_col]}'."
                        )

                    if lower_val > upper_val:
                        raise exc.SettingsError(
                            "Uncertainty parameter collection failed | "
                            f"Table '{table_name}', id '{row_id}' has invalid "
                            f"bounds: lower_bound={lower_val} > "
                            f"upper_bound={upper_val}."
                        )

                    coordinate_values = {
                        column: row[column]
                        for column in coordinate_columns
                    }

                    group_name = row[group_name_col]

                    records.append(
                        {
                            parameter_name_col: self._build_parameter_name(
                                table_name=table_name,
                                row_id=row_id,
                            ),
                            table_name_col: table_name,
                            id_col: row_id,
                            lower_bound_key: lower_val,
                            upper_bound_key: upper_val,
                            group_name_key: group_name,
                            **coordinate_values,
                        }
                    )

        return pd.DataFrame(records)

    def create_sampling_problem(
        self,
        groups: bool = False,
    ) -> tuple[pd.DataFrame, Dict[str, Any]]:
        """Create the SALib problem dictionary from uncertain parameters.

        Args:
            groups: If True, include uncertainty groups in the SALib problem.

        Returns:
            A tuple containing the parameter mapping dataframe and the
            SALib-compatible problem dictionary.
        Raises:
            exc.SettingsError: If grouped sampling is enabled and one or more
            parameters have no group name, or fewer than two distinct groups are
            defined.
        """

        mapping_df = self.collect_uncertain_parameters()

        parameter_name_col = (
            Defaults.UncertaintySettings.PARAMETER_NAME
        )

        group_name_key = (
            Defaults.UncertaintySettings.UNCERTAINTY_GROUP_NAME_KEY
        )

        problem = {
            "num_vars": len(mapping_df),
            "names": mapping_df[
                parameter_name_col
            ].tolist(),
            "bounds": mapping_df[[
                Defaults.UncertaintySettings.LOWER_BOUND_KEY,
                Defaults.UncertaintySettings.UPPER_BOUND_KEY,
            ]].values.tolist(),
        }

        if groups:

            group_names = mapping_df[group_name_key]

            missing_group_mask = (
                group_names.isna()
                | group_names.astype(str).str.strip().eq("")
            )

            if missing_group_mask.any():
                missing_parameters = mapping_df.loc[
                    missing_group_mask,
                    parameter_name_col,
                ].tolist()

                raise exc.SettingsError(
                    "Grouped sampling requires every uncertain parameter "
                    "to belong to a group. "
                    f"Missing group name for parameters: {missing_parameters}."
                )

            normalized_group_names = (
                group_names
                .astype(str)
                .str.strip()
            )

            unique_group_names = (
                normalized_group_names
                .drop_duplicates()
                .tolist()
            )

            if len(unique_group_names) < 2:
                raise exc.SettingsError(
                    "Grouped sampling requires at least two distinct groups. "
                    f"Found groups: {unique_group_names}."
                )

            problem["groups"] = normalized_group_names.tolist()

        return mapping_df, problem

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
            Defaults.UncertaintySettings.IS_UNCERTAIN_FIELD[
                Defaults.UncertaintySettings.IS_UNCERTAIN_KEY
            ][0]
        )

        lower_bound_col = (
            Defaults.UncertaintySettings.LOWER_BOUND_FIELD[
                Defaults.UncertaintySettings.LOWER_BOUND_KEY
            ][0]
        )

        upper_bound_col = (
            Defaults.UncertaintySettings.UPPER_BOUND_FIELD[
                Defaults.UncertaintySettings.UPPER_BOUND_KEY
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
                f"{Defaults.UncertaintySettings.LOWER_BOUND_KEY}={lower}, "
                f"{Defaults.UncertaintySettings.UPPER_BOUND_KEY}={upper}"
            )

        if lower_val >= upper_val:
            raise ValueError(
                f"Invalid bounds in table '{table_name}', id '{row_id}'. "
                f"{Defaults.UncertaintySettings.LOWER_BOUND_KEY} >= "
                f"{Defaults.UncertaintySettings.UPPER_BOUND_KEY} "
                f"({lower_val} >= {upper_val})"
            )

    def sample_data(
        self,
        method: str,
        problem: dict,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """Generate sampled values for uncertain parameters.

        Args:
            method (str): Sampling method name. Must be one of the keys in
                ``SAMPLERS``.
            problem: SALib problem dictionary containing parameter names, bounds and,
                when enabled, uncertainty groups
            **kwargs: Keyword arguments passed to the selected SALib sampler.

        Returns:
            pd.DataFrame: Sample matrix with an explicit run identifier column.
        """
        sampler = self.SAMPLERS[method]

        samples = sampler(problem, **kwargs)

        samples_df = pd.DataFrame(samples, columns=problem["names"])
        samples_df.index.name = Defaults.UncertaintySettings.RUN_ID
        samples_df.reset_index(inplace=True)

        return samples_df

    def _validate_sampler_kwargs(
        self,
        sampler: Callable,
        kwargs: dict[str, Any],
    ) -> None:
        """Validate user keyword arguments against a SALib sampler signature.

        Args:
            sampler: SALib sampling function to inspect, selected by user
            kwargs: Method-specific sampling arguments, selected by user

        Raises:
            TypeError: If unsupported keyword arguments are provided or required
                sampler arguments are missing.
        """
        signature = inspect.signature(sampler)
        allowed_args = set(signature.parameters.keys()) - {"problem"}

        required_args = {
            name
            for name, parameter in signature.parameters.items()
            if name != "problem"
            and parameter.default is inspect.Parameter.empty
            and parameter.kind in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            )
        }

        unexpected = set(kwargs.keys()) - allowed_args
        if unexpected:
            raise TypeError(
                f"Unexpected sampling arguments: {unexpected}. "
                f"Allowed arguments: {allowed_args}"

            )
        missing = required_args - set(kwargs.keys())
        if missing:
            raise TypeError(
                f"Missing required sampling arguments: {missing}. "
                f"Required arguments: {required_args}."
            )

    def validate_sampling_config(
            self,
            method: str,
            groups: bool,
            kwargs: dict[str, Any],
    ) -> None:
        """Validate the selected sampling method and its keyword arguments.

        Args:
            method (str): Sampling method name.
            groups(bool): Whether grouped sampling is requested.
            kwargs (dict[str, Any]): Keyword arguments to validate.

        Raises:
            ValueError: If the sampling method is not supported.
            TypeError: If unexpected arguments are passed or required arguments are
                missing.
        """
        if method not in self.SAMPLERS:
            raise ValueError(
                f"Sampling method '{method}' not supported. "
                f"Available methods: {list(self.SAMPLERS.keys())}"
            )

        group_supported_methods = {
            Defaults.UncertaintySettings.MORRIS,
            Defaults.UncertaintySettings.SOBOL,
        }

        if groups and method not in group_supported_methods:
            raise ValueError(
                "Grouped sampling is only supported for "
                f"{sorted(group_supported_methods)}. "
                f"Selected method: '{method}'."
            )

        sampler = self.SAMPLERS[method]
        self._validate_sampler_kwargs(
            sampler=sampler,
            kwargs=kwargs,
        )

    def save_dataframe(
        self,
        dataframe: pd.DataFrame,
        file_name: str,
        file_format: str,
        folder_name: str | None = None,

    ) -> None:
        """Export a dataframe to the model directory.

        Args:
            dataframe (pd.DataFrame): Dataframe to export.
            file_name (str): Output file name without extension.
            file_format (str): Output format.

        Raises:
            ValueError: If the requested file format is not supported.
        """

        file_format = file_format.lower()

        allowed_formats = Defaults.UncertaintySettings.AVAILABLE_EXPORT_FORMATS

        if file_format not in allowed_formats:
            raise ValueError(
                f"Save format '{file_format}' not supported. "
                f"Available formats: {allowed_formats}."
            )

        output_dir = self.paths["model_dir"]

        if folder_name:
            output_dir = output_dir / folder_name
            output_dir.mkdir(parents=True, exist_ok=True)
            file_path = output_dir / f"{file_name}.{file_format}"

        else:

            file_path = self.paths["model_dir"] / f"{file_name}.{file_format}"

        if file_format == Defaults.UncertaintySettings.XLSX:
            dataframe.to_excel(file_path, index=False)

        elif file_format == Defaults.UncertaintySettings.CSV:
            dataframe.to_csv(file_path, index=False)

        elif file_format == Defaults.UncertaintySettings.PARQUET:
            dataframe.to_parquet(file_path, index=False)

    def get_uncertainty_measure_vars_list(self) -> list[str]:
        """Return variables marked as uncertainty-analysis output measures."""
        uncertainty_measures = [
            var_key
            for var_key, variable in self.index.variables.items()
            if getattr(
                variable,
                Defaults.UncertaintySettings.UNCERTAINTY_MEASURE_KEY,
                False,
            ) is True
        ]
        return uncertainty_measures

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
                    f"{Defaults.UncertaintySettings.UNCERTAINTY_MEASURE_KEY}=True "
                    f"but is not scalar ({info})."
                )

            raise exc.SettingsError(
                "Uncertainty measure validation failed | "
                f"Only scalar variables can be marked as "
                f"{Defaults.UncertaintySettings.UNCERTAINTY_MEASURE_KEY}=True."
            )

    def get_deterministic_values_df(
            self,
            table_df: pd.DataFrame,
            table_name: str,
    ) -> List[Any]:
        """Return row ids with NULL deterministic values.

        Rows marked as uncertain are excluded because their values are expected
        to be provided through sampled data during uncertainty runs.
        """
        values_header = Defaults.Labels.VALUES_FIELD["values"][0]
        id_header = Defaults.Labels.ID_FIELD["id"][0]
        is_uncertain_header = Defaults.UncertaintySettings.IS_UNCERTAIN_FIELD[
            Defaults.UncertaintySettings.IS_UNCERTAIN_KEY
        ][0]

        if values_header not in table_df.columns:
            msg = (
                f"Data coherence check | Table '{table_name}' | "
                f"Column '{values_header}' not found."
            )
            self.logger.error(msg)
            raise exc.MissingDataError(msg)

        if id_header not in table_df.columns:
            msg = (
                f"Data coherence check | Table '{table_name}' | "
                f"Column '{id_header}' not found."
            )
            self.logger.error(msg)
            raise exc.MissingDataError(msg)

        if is_uncertain_header not in table_df.columns:
            deterministic_df = table_df
        else:
            is_uncertain = (
                table_df[is_uncertain_header]
                .astype(str)
                .str.strip()
                .str.lower()
                .isin(["true", "1"])
            )

            deterministic_df = table_df.loc[~is_uncertain].copy()

        return deterministic_df

    def get_uncertain_vars_list(self) -> list[str]:
        """Return exogenous variables marked as uncertain."""
        allowed_var_types = Defaults.SymbolicDefinitions.VARIABLE_TYPES

        uncertain_vars = []

        for var_key, variable in self.index.variables.items():
            if variable.type in (
                allowed_var_types["ENDOGENOUS"],
                allowed_var_types["CONSTANT"],
            ):
                continue

            if getattr(
                variable,
                Defaults.UncertaintySettings.IS_UNCERTAIN_KEY,
                False,
            ):
                uncertain_vars.append(var_key)

        return uncertain_vars

    def get_deterministic_vars_list(self) -> list[str]:
        """Return exogenous variables not marked as uncertain."""
        allowed_var_types = Defaults.SymbolicDefinitions.VARIABLE_TYPES
        deterministic_vars = []

        for var_key, variable in self.index.variables.items():
            if variable.type in (
                allowed_var_types["ENDOGENOUS"],
                allowed_var_types["CONSTANT"],
            ):
                continue

            if not getattr(
                variable,
                Defaults.UncertaintySettings.IS_UNCERTAIN_KEY,
                False,
            ):
                deterministic_vars.append(var_key)

        return deterministic_vars

    def _get_scenario_name(self, scenario_key):
        """Return scenario name from scenario index/key."""

        scenario_coordinates_header = Defaults.Labels.SCENARIO_COORDINATES

        if pd.isna(scenario_key):
            return None

        scenarios_info = self.index.scenarios_info

        if scenarios_info is None or scenarios_info.empty:
            return scenario_key

        if scenario_key not in scenarios_info.index:
            return scenario_key

        scenario_coordinates = scenarios_info.loc[
            scenario_key,
            scenario_coordinates_header,
        ]

        if isinstance(scenario_coordinates, list):
            return " | ".join(str(item) for item in scenario_coordinates)

            return scenario_coordinates

    def collect_uncertainty_measures_for_run(
        self,
        run_id: int,
        scenarios_to_collect: list | None = None,
    ) -> pd.DataFrame:
        """Collect scalar uncertainty-measure values after one solved uncertainty run.

        If `scenarios_to_collect` is provided, collect only those scenario keys.
        This avoids extracting values from infeasible scenarios.
        """

        cvxpy_var_header = Defaults.Labels.CVXPY_VAR
        sub_problem_key_header = Defaults.Labels.SUB_PROBLEM_KEY

        run_id_col = Defaults.UncertaintySettings.RUN_ID
        scenario_col = Defaults.UncertaintySettings.SCENARIO
        status_col = Defaults.UncertaintySettings.STATUS

        uncertainty_measure_vars = self.get_uncertainty_measure_vars_list()

        records = {}

        for var_key in uncertainty_measure_vars:
            variable = self.index.variables[var_key]

            variable_data_by_problem = self._normalize_variable_data_by_problem(
                variable.data
            )

            for _, variable_data in variable_data_by_problem.items():

                for _, row in variable_data.iterrows():
                    cvxpy_obj = row[cvxpy_var_header]

                    scenario_key = row.get(sub_problem_key_header, None)

                    if pd.isna(scenario_key):
                        scenario_key = None

                    if scenarios_to_collect is not None and scenario_key not in scenarios_to_collect:
                        continue

                    scenario_name = self._get_scenario_name(scenario_key)
                    record_key = scenario_name

                    if record_key not in records:
                        record = {
                            run_id_col: run_id,
                            status_col: "optimal",
                        }

                        if scenario_name is not None:
                            record[scenario_col] = scenario_name

                        records[record_key] = record

                    value = self._extract_scalar_value(
                        cvxpy_obj=cvxpy_obj,
                        var_key=var_key,
                        scenario_key=scenario_key,
                    )

                    records[record_key][var_key] = value

        if not records:
            return pd.DataFrame([{run_id_col: run_id}])

        return pd.DataFrame(records.values())

    def _normalize_variable_data_by_problem(
            self,
            variable_data,
    ) -> dict:
        """Normalize variable.data to a dictionary keyed by problem/scenario key."""

        if isinstance(variable_data, pd.DataFrame):
            return {None: variable_data}

        if isinstance(variable_data, dict):
            return variable_data

    def _extract_scalar_value(
            self,
            cvxpy_obj,
            var_key: str,
            scenario_key=None,
    ) -> float:
        """Extract a scalar value from a solved CVXPY object."""

        if cvxpy_obj.value is None:
            raise ValueError(
                f"Uncertainty measure '{var_key}' has no value "
                f"for scenario '{scenario_key}'. "
                "The related problem was probably not solved successfully."
            )

        value_array = np.asarray(cvxpy_obj.value).reshape(-1)

        if value_array.size != 1:
            raise ValueError(
                f"Uncertainty measure '{var_key}' is not scalar "
                f"for scenario '{scenario_key}'. Shape: {np.asarray(cvxpy_obj.value).shape}. "
                "Only scalar uncertainty measures can be collected."
            )

        return float(value_array[0])

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

    def _build_parameter_name(
            self,
            table_name: str,
            row_id: Any,
    ) -> str:
        """Build the unique SALib name of an uncertain parameter."""

        return f"table: {table_name}; id: {row_id}"

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
        run_id: int,
        samples_df: pd.DataFrame,
        table_name: str,
    ) -> pd.DataFrame:
        """Inject sampled values only in rows marked as uncertain.

        Rows with the uncertainty flag set to TRUE receive sampled values.
        All other rows keep their original DB values.
        """

        values_col = Defaults.Labels.VALUES_FIELD["values"][0]
        id_col = Defaults.Labels.ID_FIELD["id"][0]
        is_uncertain_col = Defaults.UncertaintySettings.IS_UNCERTAIN_FIELD[
            Defaults.UncertaintySettings.IS_UNCERTAIN_KEY
        ][0]

        resolved_df = table_df.copy()

        if is_uncertain_col not in resolved_df.columns:
            return resolved_df

        uncertain_mask = (
            resolved_df[is_uncertain_col]
            .astype(str)
            .str.upper()
            .eq("TRUE")
        )

        if not uncertain_mask.any():
            return resolved_df

        run_id_col = Defaults.UncertaintySettings.RUN_ID

        samples_run = samples_df.loc[samples_df[run_id_col].eq(run_id)]

        if samples_run.empty:
            raise exc.MissingDataError(
                f"No sampled values found for "
                f"{Defaults.UncertaintySettings.RUN_ID}={run_id}."
            )

        if len(samples_run) > 1:
            raise exc.OperationalError(
                f"Multiple sampled rows found for "
                f"{Defaults.UncertaintySettings.RUN_ID}={run_id}."
            )

        sample_values = samples_run.drop(
            columns=[run_id_col]).iloc[0].to_dict()

        for idx in resolved_df.loc[uncertain_mask].index:
            row_id = resolved_df.at[idx, id_col]
            parameter_name = self._build_parameter_name(
                table_name=table_name,
                row_id=row_id,
            )

            if parameter_name not in sample_values:
                raise exc.MissingDataError(
                    f"Missing sampled value for uncertain parameter "
                    f"'{parameter_name}' in "
                    f"{Defaults.UncertaintySettings.RUN_ID}={run_id}."
                )

            resolved_df.at[idx, values_col] = sample_values[parameter_name]

        return resolved_df

    def _validate_analysis_kwargs(
        self,
        function: Callable,
        kwargs: dict[str, Any],
        excluded_args: set[str],
        context: str,
    ) -> None:
        """Validate user provided arguments against an analysis-function signature.

            Args:
                function: SALib analysis function (method) to inspect.
                kwargs: User-supplied analyzer keyword arguments.
                excluded_args: Function arguments provided internally by CVXLab and
                    therefore not expected from the user.
                context: Label used to construct validation error messages.

            Raises:
                TypeError: If unexpected arguments are supplied or mandatory analyzer
                arguments are missing.
        """
        signature = inspect.signature(function)

        allowed_args = set(signature.parameters.keys()) - excluded_args

        required_args = {
            name
            for name, parameter in signature.parameters.items()
            if name not in excluded_args
            and parameter.default is inspect.Parameter.empty
            and parameter.kind in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            )
        }

        unexpected = set(kwargs.keys()) - allowed_args
        if unexpected:
            raise TypeError(
                f"Unexpected {context} arguments: {unexpected}. "
                f"Allowed arguments: {allowed_args}."
            )

        missing = required_args - set(kwargs.keys())
        if missing:
            raise TypeError(
                f"Missing required {context} arguments: {missing}. "
                f"Required arguments: {required_args}."
            )

    def validate_sampling_analysis_compatibility(
        self,
        sampling_method: str,
        analysis_method: str,
    ) -> None:
        """Validate methodological compatibility between sampler and GSA analyzer.

        Some SALib analyzers require samples generated with a specific sampling
        design. For instance, Morris analysis requires Morris trajectories, while
        Sobol analysis requires a Sobol/Saltelli-compatible design. Latin
        Hypercube samples are compatible with analyzers that can operate on generic
        sample matrices, such as Delta and RBD-FAST.
        """

        sampling_method = sampling_method.lower()
        analysis_method = analysis_method.lower()

        compatibility_map = Defaults.UncertaintySettings.ANALYSIS_COMPATIBILITY

        compatible_sampling_methods = compatibility_map.get(analysis_method)

        if sampling_method not in compatible_sampling_methods:
            raise ValueError(
                "Sampling-analysis compatibility validation failed | "
                f"GSA analysis method '{analysis_method}' is not compatible "
                f"with sampling method '{sampling_method}'. "
                f"Compatible sampling methods for '{analysis_method}': "
                f"{sorted(compatible_sampling_methods)}."
            )

    def validate_analysis_config(
        self,
        method: str,
        kwargs: dict[str, Any],
    ) -> None:
        """Validate the selected GSA analysis method and its keyword arguments."""

        method = method.lower()
        uncertainty_settings = Defaults.UncertaintySettings

        if method not in self.ANALYZERS:
            raise ValueError(
                f"GSA analysis method '{method}' not supported. "
                f"Available methods: {list(self.ANALYZERS.keys())}."
            )

        excluded_args = uncertainty_settings.ANALYZER_REQUIRED_INPUTS[method]

        self._validate_analysis_kwargs(
            function=self.ANALYZERS[method],
            kwargs=kwargs,
            excluded_args=excluded_args,
            context="analysis",
        )

    def analyze_results(
        self,
        method: str,
        problem: dict[str, Any],
        samples_df: pd.DataFrame,
        uncertainty_measures_df: pd.DataFrame,
        mapping_df: pd.DataFrame,
        measures: list[str] | None = None,
        scenarios: list[str] | None = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """Run SALib GSA analysis for each selected measure-scenario pair.

        SALib analyzes one scalar output vector Y at a time. Therefore, when the
        model has multiple uncertainty measures and/or multiple scenarios, this
        method repeats the analysis for each selected combination.
        """

        method = method.lower()

        targets = self._prepare_GSA_analysis_targets(
            samples_df=samples_df,
            uncertainty_measures_df=uncertainty_measures_df,
            measures=measures,
            scenarios=scenarios,
        )

        analyzer = self.ANALYZERS[method]
        records = []
        for target in targets:
            selected_samples_df = (
                samples_df
                .set_index(Defaults.UncertaintySettings.RUN_ID)
                .loc[target["run_ids"]]
                .reset_index()
            )

            X = self._prepare_GSA_input_matrix(
                problem=problem,
                samples_df=selected_samples_df,
            )

            analysis_inputs = self._build_GSA_analysis_inputs(
                method=method,
                problem=problem,
                X=X,
                Y=target["Y"],
            )

            result = analyzer(
                **analysis_inputs,
                **kwargs,
            )

            result_df = self._GSA_result_to_dataframe(
                result=result,
                problem=problem,
                method=method,
                measure=target["measure"],
                scenario=target["scenario"],
                mapping_df=mapping_df
            )

            records.append(result_df)

        if not records:
            return pd.DataFrame()

        return pd.concat(records, ignore_index=True)

    def _prepare_GSA_input_matrix(
        self,
        problem: dict[str, Any],
        samples_df: pd.DataFrame,
    ) -> np.ndarray:
        """Convert samples_df into the SALib input matrix X.

        The column order must exactly match problem["names"].
        """

        run_id_col = Defaults.UncertaintySettings.RUN_ID
        parameter_names = problem["names"]

        samples_ordered = samples_df.sort_values(run_id_col)

        X = samples_ordered[parameter_names].to_numpy(dtype=float)

        return X

    def _prepare_GSA_analysis_targets(
        self,
        samples_df: pd.DataFrame,
        uncertainty_measures_df: pd.DataFrame,
        measures: list[str] | None = None,
        scenarios: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Build  GSA output vectors for selected measures and scenarios in SALib fridenly
        format.

        Sample and measure records are aligned by ``run_id``. Failed model runs and
        non-finite measure values are removed independently for each
        measure–scenario targe

        Args:
            samples_df: Input sample dataframe.
            uncertainty_measures_df: Model-output dataframe collected across runs.
            measures: Measures to include, or None for all available measures.
            scenarios: Scenarios to include, or None for all available scenarios.

        Returns:
            list[dict[str, Any]]: Analysis targets containing the selected measure,
            scenario, valid run identifiers and aligned output vector ``Y``.

        Raises:
            ValueError: If requested measures or scenarios are unavailable, or if no
                valid output remains for a target.
"""
        run_id_col = Defaults.UncertaintySettings.RUN_ID
        scenario_col = Defaults.UncertaintySettings.SCENARIO

        technical_cols = {run_id_col,
                          scenario_col,
                          Defaults.UncertaintySettings.STATUS}

        samples_run_ids = samples_df[[run_id_col]].drop_duplicates()

        available_measures = [
            col for col in uncertainty_measures_df.columns
            if col not in technical_cols
        ]

        if measures is None:
            measures = available_measures
        else:
            missing_measures = [
                measure for measure in measures
                if measure not in available_measures
            ]
            if missing_measures:
                raise exc.MissingDataError(
                    "SALib target preparation failed | "
                    f"Unknown uncertainty measure(s): {missing_measures}. "
                    f"Available measures: {available_measures}."
                )

        has_scenarios = scenario_col in uncertainty_measures_df.columns

        if has_scenarios:
            available_scenarios = sorted(
                uncertainty_measures_df[scenario_col]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            if scenarios is None:
                scenarios = available_scenarios
            else:
                scenarios = [str(scenario) for scenario in scenarios]

                missing_scenarios = [
                    scenario for scenario in scenarios
                    if scenario not in available_scenarios
                ]
                if missing_scenarios:
                    raise exc.MissingDataError(
                        "SALib target preparation failed | "
                        f"Unknown scenario(s): {missing_scenarios}. "
                        f"Available scenarios: {available_scenarios}."
                    )
        else:
            scenarios = [None]

        targets = []

        for scenario in scenarios:
            if has_scenarios:
                df_target = uncertainty_measures_df.loc[
                    uncertainty_measures_df[scenario_col].astype(
                        str).eq(str(scenario))
                ].copy()
            else:
                df_target = uncertainty_measures_df.copy()

            merged = samples_run_ids.merge(
                df_target,
                on=run_id_col,
                how="left",
                validate="one_to_one",
            ).sort_values(run_id_col)

            for measure in measures:
                missing_run_ids = merged.loc[
                    merged[measure].isna(),
                    run_id_col,
                ].tolist()

                if missing_run_ids:
                    self.logger.warning(
                        "SALib target preparation | "
                        f"Dropping missing/unfeasible output for measure '{measure}', "
                        f"scenario '{scenario}', run_id(s): {missing_run_ids}."
                    )

                merged_valid = merged.dropna(subset=[measure]).copy()

                if merged_valid.empty:
                    raise exc.MissingDataError(
                        "SALib target preparation failed | "
                        f"No valid output values left for measure '{measure}', "
                        f"scenario '{scenario}' after dropping NaNs."
                    )

                Y = merged_valid[measure].to_numpy(dtype=float)
                valid_run_ids = merged_valid[run_id_col].tolist()

                targets.append(
                    {
                        "measure": measure,
                        "scenario": scenario,
                        "Y": Y,
                        "run_ids": valid_run_ids,
                    }
                )

        return targets

    def _build_GSA_analysis_inputs(
        self,
        method: str,
        problem: dict[str, Any],
        X: np.ndarray,
        Y: np.ndarray,
    ) -> dict[str, Any]:
        """Build the required positional inputs for the selected SALib analyzer."""

        required_inputs = self.ANALYZER_REQUIRED_INPUTS[method]

        inputs = {}

        if "problem" in required_inputs:
            inputs["problem"] = problem

        if "X" in required_inputs:
            inputs["X"] = X

        if "Y" in required_inputs:
            inputs["Y"] = Y

        return inputs

    def _get_split_problem_coordinate_columns(self) -> set[str]:
        """Return coordinate column names associated with split-problem sets."""

        split_problem_coordinate_cols = set()

        for set_key, set_table in self.index.sets.items():
            if not getattr(set_table, "split_problem", False):
                continue

            table_headers = getattr(set_table, "table_headers", None)

            if table_headers is None:
                continue

            name_header = table_headers.get(Defaults.Labels.NAME)

            if name_header:
                split_problem_coordinate_cols.add(name_header[0])

        return split_problem_coordinate_cols

    def _GSA_result_to_dataframe(
            self,
            result: Any,
            problem: dict[str, Any],
            method: str,
            measure: str,
            scenario: str | None,
            mapping_df: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        """Convert a SALib analysis result into a long-format dataframe."""

        parameter_name_col = (
            Defaults.UncertaintySettings.PARAMETER_NAME
        )

        group_name_col = (
            Defaults.UncertaintySettings.UNCERTAINTY_GROUP_NAME_KEY
        )

        result_dict = dict(result)

        # SALib returns the names corresponding exactly to the sensitivity
        # arrays. For grouped analyses these are the group names.
        result_names = result_dict.get("names")

        if result_names is None:
            raise exc.OperationalError(
                "SALib result conversion failed | "
                "The analysis result does not contain the 'names' field."
            )

        result_names = list(result_names)

        is_grouped = "groups" in problem

        result_name_col = (
            group_name_col
            if is_grouped
            else parameter_name_col
        )

        metadata_keys = {"names"}
        records = []

        for metric, values in result_dict.items():

            if metric in metadata_keys:
                continue

            if np.ma.isMaskedArray(values):
                values_array = np.ma.filled(
                    values,
                    np.nan,
                )
            else:
                values_array = np.asarray(values)

            values_array = np.asarray(values_array)

            # Skip scalar metadata and multidimensional results.
            if values_array.ndim != 1:
                continue

            if len(values_array) != len(result_names):
                raise exc.OperationalError(
                    "SALib result conversion failed | "
                    f"Metric '{metric}' contains {len(values_array)} values, "
                    f"but SALib returned {len(result_names)} names: "
                    f"{result_names}."
                )

            if not np.issubdtype(
                values_array.dtype,
                np.number,
            ):
                continue

            for result_name, value in zip(
                result_names,
                values_array,
            ):
                record = {
                    "method": method,
                    result_name_col: result_name,
                    "metric": metric,
                    "value": (
                        float(value)
                        if pd.notna(value)
                        else np.nan
                    ),
                }

                if scenario is not None:
                    record["scenario"] = scenario

                record["measure"] = measure

                records.append(record)

        result_df = pd.DataFrame(records)

        if result_df.empty:
            raise exc.OperationalError(
                "SALib result conversion failed | "
                "No one-dimensional numerical sensitivity metric "
                "could be extracted from the analysis result. "
                f"Available result keys: {list(result_dict.keys())}."
            )

        last_cols = [
            "measure",
            "metric",
            "value",
        ]

        # Group-level results cannot be merged with the parameter mapping:
        # one group generally corresponds to multiple uncertain parameters.
        if is_grouped:
            first_cols = [
                col
                for col in result_df.columns
                if col not in last_cols
            ]

            return result_df[
                first_cols + last_cols
            ]

        # Parameter-level analysis without mapping metadata.
        if mapping_df is None:
            first_cols = [
                col
                for col in result_df.columns
                if col not in last_cols
            ]

            return result_df[
                first_cols + last_cols
            ]

        excluded_metadata_cols = {
            Defaults.Labels.ID_FIELD["id"][0],
            parameter_name_col,
            Defaults.UncertaintySettings.LOWER_BOUND_KEY,
            Defaults.UncertaintySettings.UPPER_BOUND_KEY,
            Defaults.UncertaintySettings.METHOD,
            group_name_col,
        }

        split_problem_coordinate_cols = (
            self._get_split_problem_coordinate_columns()
        )

        metadata_cols = [
            col
            for col in mapping_df.columns
            if col not in excluded_metadata_cols
            and col not in split_problem_coordinate_cols
        ]

        result_df = result_df.merge(
            mapping_df[
                [
                    parameter_name_col,
                    *metadata_cols,
                ]
            ].drop_duplicates(),
            on=parameter_name_col,
            how="left",
            validate="many_to_one",
        )

        result_df = result_df.drop(
            columns=[parameter_name_col],
            errors="ignore",
        )

        first_cols = [
            col
            for col in result_df.columns
            if col not in last_cols
        ]

        return result_df[
            first_cols + last_cols
        ]

    def create_failed_measure_records_for_run(
        self,
        run_id: int,
        failed_scenarios: dict,
    ) -> pd.DataFrame:
        """Create NaN uncertainty-measure records for failed scenario-runs.

        `failed_scenarios` maps scenario keys to solver status. For a model without
        split scenarios, use {None: status}.
        """

        records = []

        run_id_col = Defaults.UncertaintySettings.RUN_ID
        scenario_col = Defaults.UncertaintySettings.SCENARIO
        status_col = Defaults.UncertaintySettings.STATUS

        uncertainty_measure_vars = self.get_uncertainty_measure_vars_list()

        for scenario_key, status in failed_scenarios.items():
            scenario_name = self._get_scenario_name(scenario_key)

            record = {
                run_id_col: run_id,
                status_col: status,
            }

            if scenario_name is not None:
                record[scenario_col] = scenario_name

            for measure in uncertainty_measure_vars:
                record[measure] = np.nan

            records.append(record)

        return pd.DataFrame(records)
