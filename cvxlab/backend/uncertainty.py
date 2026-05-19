"""Tools for collecting uncertain parameters from exogenous data tables."""

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

    """Handle uncertainty metadata, sampling, and sample export.

    This class provides the uncertainty-analysis layer of CVXLab. It identifies
    uncertain parameters from exogenous data tables, validates their lower and
    upper bounds, builds the sampling problem required by SALib, generates
    sampled parameter values, and optionally exports the generated samples.


    ASSAKRORFPPOF AGGIUNGERE ALTRE COSE CHE POI METTO RICORDARSIIIII

    Attributes:
        sqltools (SQLManager): SQLite manager used to read model data tables.
        index (Index): Model index containing variables, data tables, and
            their metadata.
        paths (Dict): Dictionary of model paths, including the model directory.
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
        """
         SCRIVERE QUIII AAAAA RICORDATIIIIIAAAA
        """

        self.sqltools = sqltools
        self.index = index
        self.paths = paths
        self.logger = logger.get_child(__name__)

    def collect_uncertain_parameters(self) -> pd.DataFrame:
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

        parameter_name_col = Defaults.UncertaintySettings.PARAMETER_NAME
        table_name_col = Defaults.Labels.TABLE_NAME
        variable_name_col = Defaults.Labels.VARIABLE_NAME

        technical_columns = {
            id_col,
            values_col,
            is_uncertain_col,
            lower_col,
            upper_col,
        }

        uncertain_vars_by_table: dict[str, list[str]] = {}

        for var_key, variable in self.index.variables.items():
            if variable.is_uncertain:
                uncertain_vars_by_table.setdefault(
                    variable.related_table,
                    [],
                ).append(var_key)

        with db_handler(self.sqltools):

            for table_name, var_keys in uncertain_vars_by_table.items():
                df = self.sqltools.table_to_dataframe(table_name=table_name)

                uncertain_df = df[
                    df[is_uncertain_col].astype(str).str.lower().eq("true")
                ]

                coordinate_columns = [
                    column
                    for column in df.columns
                    if column not in technical_columns
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

                    lower_val, upper_val = self._check_bounds(
                        table_name=table_name,
                        row_id=row_id,
                        lower=row[lower_col],
                        upper=row[upper_col],
                    )

                    records.append(
                        {
                            parameter_name_col: f"{table_name}||{row_id}",
                            table_name_col: table_name,
                            id_col: row_id,
                            variable_name_col: variable_name,
                            Defaults.UncertaintySettings.LOWER_BOUND_KEY: lower_val,
                            Defaults.UncertaintySettings.UPPER_BOUND_KEY: upper_val,
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

    def create_sampling_problem(
        self,
    ) -> Dict[str, Any]:
        """Create the SALib problem dictionary from uncertain parameters.    
        Returns:
            Dict[str, Any]: SALib-compatible problem dictionary
        """
        mapping_df = self.collect_uncertain_parameters()

        problem = {
            "num_vars": len(mapping_df),
            "names": mapping_df[
                Defaults.UncertaintySettings.PARAMETER_NAME
            ].tolist(),
            "bounds": mapping_df[[
                Defaults.UncertaintySettings.LOWER_BOUND_KEY,
                Defaults.UncertaintySettings.UPPER_BOUND_KEY,
            ]].values.tolist(),
        }

        return mapping_df, problem

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

        return lower_val, upper_val

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
            kwargs: dict[str, Any],
    ) -> None:
        """Validate the selected sampling method and its keyword arguments.

        Args:
            method (str): Sampling method name.
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

    # def inject_sampled_values(
    #     self,
    #     table_df: pd.DataFrame,
    #     table_name: str,
    #     samples_df: pd.DataFrame,
    #     run_id: int,
    #     separator: str = "||",
    # ) -> pd.DataFrame:
    #     """Inject sampled uncertainty values into a normalized data-table dataframe.

    #     The function maps each row of `table_df` to one sampled parameter using
    #     the convention:

    #         {table_name} || {id}

    #     and writes the sampled value into the standard `values` column. Auxiliary
    #     uncertainty bound columns are removed
    #     before returning the dataframe, so that the output can be passed to the
    #     standard CVXLab reshaping pipeline.

    #     Args:
    #         table_df: DataFrame extracted from the SQLite data table.
    #         table_name: Name of the SQLite data table.
    #         samples_df: DataFrame containing sampled values. Expected columns are
    #             the run identifier plus one column per uncertain parameter.
    #         run_id: Identifier of the uncertainty-analysis run to inject.
    #         separator: Separator used in sampled-parameter names.

    #     Returns:
    #         A copy of `table_df` with sampled values written into the `values`
    #         column and uncertainty-bound columns removed.

    #     Raises:
    #         MissingDataError: If required columns are missing, if the selected run is not
    #             found, if it is duplicated, or if sampled parameters are missing.
    #     """

    #     id_header = Defaults.Labels.ID_FIELD["id"][0]
    #     values_header = Defaults.Labels.VALUES_FIELD["values"][0]
    #     lower_bound_header = Defaults.UncertaintySettings.LOWER_BOUND_FIELD[
    #         Defaults.UncertaintySettings.LOWER_BOUND_KEY
    #     ][0]
    #     upper_bound_header = Defaults.UncertaintySettings.UPPER_BOUND_FIELD[
    #         Defaults.UncertaintySettings.UPPER_BOUND_KEY
    #     ][0]
    #     run_id_col = Defaults.UncertaintySettings.RUN_ID

    #     required_table_columns = [id_header, values_header]
    #     missing_table_columns = [
    #         col for col in required_table_columns
    #         if col not in table_df.columns
    #     ]

    #     if missing_table_columns:
    #         msg = (
    #             "Sample injection failed | "
    #             f"Table '{table_name}' is missing required column(s): "
    #             f"{missing_table_columns}."
    #         )
    #         self.logger.error(msg)
    #         raise exc.MissingDataError(msg)

    #     samples_df_run = samples_df.loc[samples_df[run_id_col] == run_id]

    #     if samples_df_run.empty:
    #         msg = (
    #             "Sample injection failed | "
    #             f"No sampled values found for "
    #             f"{Defaults.UncertaintySettings.RUN_ID}={run_id}."
    #         )
    #         self.logger.error(msg)
    #         raise exc.MissingDataError(msg)

    #     samples_series = samples_df_run.iloc[0]

    #     result_df = table_df.copy()

    #     parameter_names = (
    #         table_name
    #         + separator
    #         + result_df[id_header].astype(str)
    #     )

    #     missing_parameters = [
    #         parameter_name
    #         for parameter_name in parameter_names
    #         if parameter_name not in samples_df.columns
    #     ]

    #     if missing_parameters:
    #         if len(missing_parameters) > 5:
    #             missing_parameters = (
    #                 missing_parameters[:5]
    #                 + [f"(total items {len(missing_parameters)})"]
    #             )

    #         msg = (
    #             "Sample injection failed | "
    #             f"Missing sampled parameter column(s) for table '{table_name}': "
    #             f"{missing_parameters}."
    #         )
    #         self.logger.error(msg)
    #         raise exc.MissingDataError(msg)

    #     result_df[values_header] = parameter_names.map(samples_series).values

    #     result_df[values_header] = pd.to_numeric(
    #         result_df[values_header],
    #         errors="coerce",
    #     )

    #     null_sampled_values = result_df.loc[
    #         result_df[values_header].isna(),
    #         id_header,
    #     ].tolist()

    #     if null_sampled_values:
    #         if len(null_sampled_values) > 5:
    #             null_sampled_values = (
    #                 null_sampled_values[:5]
    #                 + [f"(total items {len(null_sampled_values)})"]
    #             )

    #         msg = (
    #             "Sample injection failed | "
    #             f"Sampled values for table '{table_name}' contain null/non-numeric "
    #             f"values at id row(s): {null_sampled_values}."
    #         )
    #         self.logger.error(msg)
    #         raise exc.MissingDataError(msg)

    #     result_df = result_df.drop(
    #         columns=[lower_bound_header, upper_bound_header],
    #         errors="ignore",
    #     )

    #     return result_df

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
    ) -> pd.DataFrame:
        """Collect uncertainty-measure values after one uncertainty run.

        Returns one row per scenario if the model is split into multiple problems.
        """

        cvxpy_var_header = Defaults.Labels.CVXPY_VAR
        sub_problem_key_header = Defaults.Labels.SUB_PROBLEM_KEY

        uncertainty_measure_vars = self.get_uncertainty_measure_vars_list()

        records = {}

        for var_key in uncertainty_measure_vars:
            variable = self.index.variables[var_key]

            variable_data_by_problem = self._normalize_variable_data_by_problem(
                variable.data
            )

            for problem_key, variable_data in variable_data_by_problem.items():

                for row_idx, row in variable_data.iterrows():
                    cvxpy_obj = row[cvxpy_var_header]

                    scenario_key = row.get(sub_problem_key_header, None)

                    if pd.isna(scenario_key):
                        scenario_key = None

                    record_key = scenario_key

                    scenario_name = self._get_scenario_name(scenario_key)

                    record_key = scenario_name

                    if record_key not in records:

                        record = {Defaults.UncertaintySettings.RUN_ID: run_id}

                        if scenario_key is not None:
                            record["scenario"] = scenario_name

                        records[record_key] = record

                    value = self._extract_scalar_value(
                        cvxpy_obj=cvxpy_obj,
                        var_key=var_key,
                        scenario_key=scenario_key,
                    )

                    records[record_key][var_key] = value

        if not records:
            return pd.DataFrame(
                [{Defaults.UncertaintySettings.RUN_ID: run_id}]
            )

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
                f"for scenario '{scenario_key}'. Problem may not have been solved."
            )

        value_array = np.asarray(cvxpy_obj.value).reshape(-1)

        if value_array.size != 1:
            raise ValueError(
                f"Uncertainty measure '{var_key}' is not scalar "
                f"for scenario '{scenario_key}'. Shape: {np.asarray(cvxpy_obj.value).shape}. "
                "Only scalar uncertainty measures can be collected."
            )

        return float(value_array[0])

    def get_uncertainty_hybrid_tables_list(self) -> list[str]:
        """Return data tables containing at least one uncertain variable."""

        uncertainty_tables = []

        for var_key, variable in self.index.variables.items():
            if getattr(
                variable,
                Defaults.UncertaintySettings.IS_UNCERTAIN_KEY,
                False,
            ):
                if variable.related_table is not None:
                    uncertainty_tables.append(variable.related_table)

        return sorted(set(uncertainty_tables))

    def get_fully_deterministic_tables_list(self) -> list[str]:
        """Return exogenous data tables containing no uncertain variables."""

        allowed_var_types = Defaults.SymbolicDefinitions.VARIABLE_TYPES

        deterministic_tables = []

        for table_key, table in self.index.data.items():
            if table.type in [
                allowed_var_types["ENDOGENOUS"],
                allowed_var_types["CONSTANT"],
            ]:
                continue

            table_has_uncertain_vars = any(
                self.index.variables[var_key].is_uncertain
                for var_key in table.variables_info
            )

            if not table_has_uncertain_vars:
                deterministic_tables.append(table_key)

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
            parameter_name = f"{table_name}||{row_id}"

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

        X = self._prepare_GSA_input_matrix(
            problem=problem,
            samples_df=samples_df,
        )

        targets = self._prepare_GSA_analysis_targets(
            samples_df=samples_df,
            uncertainty_measures_df=uncertainty_measures_df,
            measures=measures,
            scenarios=scenarios,
        )

        analyzer = self.ANALYZERS[method]
        records = []
        for target in targets:
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

        return targets, X

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
        """Prepare one output vector Y for each selected measure-scenario pair."""

        run_id_col = Defaults.UncertaintySettings.RUN_ID
        scenario_col = Defaults.UncertaintySettings.SCENARIO

        technical_cols = {run_id_col, scenario_col}
        samples_run_ids = samples_df[[run_id_col]]

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
                if merged[measure].isna().any():
                    missing_run_ids = merged.loc[
                        merged[measure].isna(),
                        run_id_col,
                    ].tolist()

                    raise exc.MissingDataError(
                        "SALib target preparation failed | "
                        f"Missing output values for measure '{measure}', "
                        f"scenario '{scenario}', run_id(s): {missing_run_ids}."
                    )

                Y = merged[measure].to_numpy(dtype=float)

                targets.append(
                    {
                        "measure": measure,
                        "scenario": scenario,
                        "Y": Y,
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

        parameter_name_col = Defaults.UncertaintySettings.PARAMETER_NAME
        parameter_names = list(problem["names"])

        metadata_keys = {"names"}
        records = []

        result_dict = dict(result)

        for metric, values in result_dict.items():

            if metric in metadata_keys:
                continue

            if np.ma.isMaskedArray(values):
                values_array = np.ma.filled(values, np.nan)
            else:
                values_array = np.asarray(values)

            values_array = np.asarray(values_array)

            if values_array.ndim != 1:
                continue

            if len(values_array) != len(parameter_names):
                continue

            if not np.issubdtype(values_array.dtype, np.number):
                continue

            for parameter_name, value in zip(parameter_names, values_array):
                record = {
                    "method": method,
                    "measure": measure,
                    parameter_name_col: parameter_name,
                    "metric": metric,
                    "value": float(value) if pd.notna(value) else np.nan,
                }

                if scenario is not None:
                    record["scenario"] = scenario

                records.append(record)

        result_df = pd.DataFrame(records)

        if mapping_df is None or result_df.empty:
            return result_df

        excluded_metadata_cols = {
            Defaults.Labels.ID_FIELD["id"][0],
            parameter_name_col,
            Defaults.UncertaintySettings.LOWER_BOUND_KEY,
            Defaults.UncertaintySettings.UPPER_BOUND_KEY,
            Defaults.UncertaintySettings.METHOD,

        }

        split_problem_coordinate_cols = self._get_split_problem_coordinate_columns()

        metadata_cols = [
            col for col in mapping_df.columns
            if col not in excluded_metadata_cols
            and col not in split_problem_coordinate_cols
        ]

        result_df = result_df.merge(
            mapping_df[[parameter_name_col, *metadata_cols]].drop_duplicates(),
            on=parameter_name_col,
            how="left",
            validate="many_to_one",
        )

        result_df = result_df.drop(
            columns=[parameter_name_col],
            errors="ignore",
        )

        last_cols = ["measure", "metric", "value"]

        first_cols = [
            col for col in result_df.columns
            if col not in last_cols
        ]

        result_df = result_df[first_cols + last_cols]

        return result_df
