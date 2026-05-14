"""Tools for collecting uncertain parameters from exogenous data tables."""

from typing import Any, Dict, List, Tuple

import pandas as pd
import numpy as np
from typing import Any, Callable
import inspect
from SALib.sample import sobol, latin, morris
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
        "sobol": sobol.sample,
        "latin": latin.sample,
        "morris": morris.sample
    }

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

             Returns:
                pd.DataFrame: Mapping table containing parameter names, table names,
                row identifiers, bounds, and coordinate labels. 
        """
        records: List[Dict[str, Any]] = []

        id_col = Defaults.Labels.ID_FIELD['id'][0]
        values_col = Defaults.Labels.VALUES_FIELD['values'][0]
        is_uncertain_col = Defaults.Labels.IS_UNCERTAIN_FIELD[
            Defaults.Labels.IS_UNCERTAIN_KEY
        ][0]
        lower_col = Defaults.Labels.LOWER_BOUND_FIELD[
            Defaults.Labels.LOWER_BOUND_KEY
        ][0]
        upper_col = Defaults.Labels.UPPER_BOUND_FIELD[
            Defaults.Labels.UPPER_BOUND_KEY
        ][0]
        parameter_name_col = Defaults.Labels.PARAMETER_NAME
        table_name_col = Defaults.Labels.TABLE_NAME
        variable_name_col = Defaults.Labels.VARIABLE_NAME
        coordinate_label_col = Defaults.Labels.COORDINATE_LABEL

        technical_columns = {
            id_col,
            values_col,
            is_uncertain_col,
            lower_col,
            upper_col,
        }

        uncertain_tables = {}

        for var_key, variable in self.index.variables.items():
            if variable.is_uncertain:
                table_name = variable.related_table
                uncertain_tables.setdefault(table_name, []).append(var_key)

        with db_handler(self.sqltools):

            for table_name, var_keys in uncertain_tables.items():
                df = self.sqltools.table_to_dataframe(table_name=table_name)

                uncertain_df = df[
                    df[is_uncertain_col].astype(str).str.lower() == "true"
                ]

                coordinate_columns = [
                    column
                    for column in df.columns
                    if column not in technical_columns
                ]

                for _, row in uncertain_df.iterrows():
                    row_id = row[id_col]

                    coordinate_label = "||".join(
                        f"{column} = {row[column]}"
                        for column in coordinate_columns
                    )

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
                            "id": row_id,
                            variable_name_col: var_keys[0],
                            Defaults.Labels.LOWER_BOUND_KEY: lower_val,
                            Defaults.Labels.UPPER_BOUND_KEY: upper_val,
                            coordinate_label_col: coordinate_label,
                        }
                    )

        mapping_df = pd.DataFrame(
            records,
            columns=[
                parameter_name_col,
                table_name_col,
                "id",
                Defaults.Labels.LOWER_BOUND_KEY,
                Defaults.Labels.UPPER_BOUND_KEY,
                coordinate_label_col,
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
            "names": mapping_df[Defaults.Labels.PARAMETER_NAME].tolist(),
            "bounds": mapping_df[[
                Defaults.Labels.LOWER_BOUND_KEY,
                Defaults.Labels.UPPER_BOUND_KEY,
            ]].values.tolist(),
        }

        return problem

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
                f"{Defaults.Labels.LOWER_BOUND_KEY}={lower}, "
                f"{Defaults.Labels.UPPER_BOUND_KEY}={upper}"
            )

        if lower_val >= upper_val:
            raise ValueError(
                f"Invalid bounds in table '{table_name}', id '{row_id}'. "
                f"{Defaults.Labels.LOWER_BOUND_KEY} >= "
                f"{Defaults.Labels.UPPER_BOUND_KEY} "
                f"({lower_val} >= {upper_val})"
            )

        return lower_val, upper_val

    def sample_data(
        self,
        method: str,
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
        problem = self.create_sampling_problem()
        sampler = self.SAMPLERS[method]

        samples = sampler(problem, **kwargs)

        samples_df = pd.DataFrame(samples, columns=problem["names"])
        samples_df.index.name = Defaults.Labels.RUN_ID
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

    def _prepare_samples_dataframe_for_saving(
            self,
            samples_df: pd.DataFrame,
            mapping_df: pd.DataFrame,
    ) -> pd.DataFrame:
        run_id_col = Defaults.Labels.RUN_ID
        parameter_name_col = Defaults.Labels.PARAMETER_NAME
        sampled_value_col = Defaults.Labels.SAMPLED_VALUE
        coordinate_label_col = Defaults.Labels.COORDINATE_LABEL

        samples_long = samples_df.melt(
            id_vars=run_id_col,
            var_name=parameter_name_col,
            value_name=sampled_value_col,
        )

        coordinates_df = mapping_df[
            [parameter_name_col, coordinate_label_col]
        ].drop_duplicates()

        samples_df_save = samples_long.merge(
            coordinates_df,
            on=parameter_name_col,
            how="left",
        )
        samples_df_save = samples_df_save[[
            run_id_col,
            coordinate_label_col,
            parameter_name_col,
            sampled_value_col,
        ]]
        return samples_df_save

    def save_samples(
            self,
            samples_df: pd.DataFrame,
            file_format: str = "xlsx"
    ) -> None:
        """Export generated uncertainty samples to file.

            Args:
                samples_df (pd.DataFrame): Sample dataframe returned by ``sample_data``.
                file_format (str): Output format. Supported values are ``xlsx``, ``csv``,
                    and ``parquet``.

            Raises:
                ValueError: If the requested file format is not supported.
        """
        file_format = file_format.lower()
        allowed_formats = ["xlsx", "csv", "parquet"]
        if file_format not in allowed_formats:
            raise ValueError(
                f"Save format '{file_format}' not supported. "
                f"Available formats: {allowed_formats}"
            )

        mapping_df = self.collect_uncertain_parameters()

        samples_df_save = self._prepare_samples_dataframe_for_saving(
            samples_df=samples_df,
            mapping_df=mapping_df,
        )

        file_path = self.paths["model_dir"] / \
            f"uncertainty_samples.{file_format}"

        if file_format == "xlsx":
            samples_df_save.to_excel(file_path, index=False)
        elif file_format == "csv":
            samples_df_save.to_csv(file_path, index=False)
        elif file_format == "parquet":
            samples_df_save.to_parquet(file_path, index=False)

    def get_uncertainty_measure_vars_list(self) -> list[str]:
        """Return variables marked as uncertainty-analysis output measures."""
        uncertainty_measures = [
            var_key
            for var_key, variable in self.index.variables.items()
            if getattr(
                variable,
                Defaults.Labels.UNCERTAINTY_MEASURE_KEY,
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
                    f"{Defaults.Labels.UNCERTAINTY_MEASURE_KEY}=True "
                    f"but is not scalar ({info})."
                )

            raise exc.SettingsError(
                "Uncertainty measure validation failed | "
                f"Only scalar variables can be marked as "
                f"{Defaults.Labels.UNCERTAINTY_MEASURE_KEY}=True."
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
        is_uncertain_header = Defaults.Labels.IS_UNCERTAIN_FIELD[
            Defaults.Labels.IS_UNCERTAIN_KEY
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

            if getattr(variable, Defaults.Labels.IS_UNCERTAIN_KEY, False):
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

            if not getattr(variable, Defaults.Labels.IS_UNCERTAIN_KEY, False):
                deterministic_vars.append(var_key)

        return deterministic_vars

    def inject_sampled_values(
        self,
        table_df: pd.DataFrame,
        table_name: str,
        samples_df: pd.DataFrame,
        run_id: int,
        separator: str = "||",
    ) -> pd.DataFrame:
        """Inject sampled uncertainty values into a normalized data-table dataframe.

        The function maps each row of `table_df` to one sampled parameter using
        the convention:

            {table_name} || {id}

        and writes the sampled value into the standard `values` column. Auxiliary
        uncertainty bound columns are removed
        before returning the dataframe, so that the output can be passed to the
        standard CVXLab reshaping pipeline.

        Args:
            table_df: DataFrame extracted from the SQLite data table.
            table_name: Name of the SQLite data table.
            samples_df: DataFrame containing sampled values. Expected columns are
                the run identifier plus one column per uncertain parameter.
            run_id: Identifier of the uncertainty-analysis run to inject.
            separator: Separator used in sampled-parameter names.

        Returns:
            A copy of `table_df` with sampled values written into the `values`
            column and uncertainty-bound columns removed.

        Raises:
            MissingDataError: If required columns are missing, if the selected run is not
                found, if it is duplicated, or if sampled parameters are missing.
        """

        id_header = Defaults.Labels.ID_FIELD["id"][0]
        values_header = Defaults.Labels.VALUES_FIELD["values"][0]
        lower_bound_header = Defaults.Labels.LOWER_BOUND_FIELD[
            Defaults.Labels.LOWER_BOUND_KEY
        ][0]
        upper_bound_header = Defaults.Labels.UPPER_BOUND_FIELD[
            Defaults.Labels.UPPER_BOUND_KEY
        ][0]
        run_id_col = Defaults.Labels.RUN_ID

        required_table_columns = [id_header, values_header]
        missing_table_columns = [
            col for col in required_table_columns
            if col not in table_df.columns
        ]

        if missing_table_columns:
            msg = (
                "Sample injection failed | "
                f"Table '{table_name}' is missing required column(s): "
                f"{missing_table_columns}."
            )
            self.logger.error(msg)
            raise exc.MissingDataError(msg)

        samples_df_run = samples_df.loc[samples_df[run_id_col] == run_id]

        if samples_df_run.empty:
            msg = (
                "Sample injection failed | "
                f"No sampled values found for "
                f"{Defaults.Labels.RUN_ID}={run_id}."
            )
            self.logger.error(msg)
            raise exc.MissingDataError(msg)

        samples_series = samples_df_run.iloc[0]

        result_df = table_df.copy()

        parameter_names = (
            table_name
            + separator
            + result_df[id_header].astype(str)
        )

        missing_parameters = [
            parameter_name
            for parameter_name in parameter_names
            if parameter_name not in samples_df.columns
        ]

        if missing_parameters:
            if len(missing_parameters) > 5:
                missing_parameters = (
                    missing_parameters[:5]
                    + [f"(total items {len(missing_parameters)})"]
                )

            msg = (
                "Sample injection failed | "
                f"Missing sampled parameter column(s) for table '{table_name}': "
                f"{missing_parameters}."
            )
            self.logger.error(msg)
            raise exc.MissingDataError(msg)

        result_df[values_header] = parameter_names.map(samples_series).values

        result_df[values_header] = pd.to_numeric(
            result_df[values_header],
            errors="coerce",
        )

        null_sampled_values = result_df.loc[
            result_df[values_header].isna(),
            id_header,
        ].tolist()

        if null_sampled_values:
            if len(null_sampled_values) > 5:
                null_sampled_values = (
                    null_sampled_values[:5]
                    + [f"(total items {len(null_sampled_values)})"]
                )

            msg = (
                "Sample injection failed | "
                f"Sampled values for table '{table_name}' contain null/non-numeric "
                f"values at id row(s): {null_sampled_values}."
            )
            self.logger.error(msg)
            raise exc.MissingDataError(msg)

        result_df = result_df.drop(
            columns=[lower_bound_header, upper_bound_header],
            errors="ignore",
        )

        return result_df

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

                    if record_key not in records:

                        record = {Defaults.Labels.RUN_ID: run_id}

                        if scenario_key is not None:
                            record["scenario"] = scenario_key

                        records[record_key] = record

                    value = self._extract_scalar_value(
                        cvxpy_obj=cvxpy_obj,
                        var_key=var_key,
                        scenario_key=scenario_key,
                    )

                    records[record_key][var_key] = value

        if not records:
            return pd.DataFrame([{Defaults.Labels.RUN_ID: run_id}])

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
            if getattr(variable, Defaults.Labels.IS_UNCERTAIN_KEY, False):
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
        is_uncertain_col = Defaults.Labels.IS_UNCERTAIN_FIELD[
            Defaults.Labels.IS_UNCERTAIN_KEY
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

        run_id_col = Defaults.Labels.RUN_ID

        samples_run = samples_df.loc[samples_df[run_id_col].eq(run_id)]

        if samples_run.empty:
            raise exc.MissingDataError(
                f"No sampled values found for "
                f"{Defaults.Labels.RUN_ID}={run_id}."
            )

        if len(samples_run) > 1:
            raise exc.OperationalError(
                f"Multiple sampled rows found for "
                f"{Defaults.Labels.RUN_ID}={run_id}."
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
                    f"{Defaults.Labels.RUN_ID}={run_id}."
                )

            resolved_df.at[idx, values_col] = sample_values[parameter_name]

        return resolved_df
