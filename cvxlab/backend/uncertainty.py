"""Tools for collecting uncertain parameters from exogenous data tables."""

from typing import Any, Dict, List, Tuple

import pandas as pd
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
         
        """Collect uncertain parameters from uncertainty-enabled exogenous tables

             Returns:
                pd.DataFrame: Mapping table containing parameter names, table names,
                row identifiers, bounds, and coordinate labels. 
        """
        records: List[Dict[str, Any]] = []


        id_col = Defaults.Labels.ID_FIELD['id'][0]
        values_col = Defaults.Labels.VALUES_FIELD['values'][0]
        is_uncertain_col = Defaults.Labels.IS_UNCERTAIN_FIELD['is_uncertain'][0]
        lower_col = Defaults.Labels.LOWER_BOUND_FIELD['lower_bound'][0]
        upper_col = Defaults.Labels.UPPER_BOUND_FIELD['upper_bound'][0]
  
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
                            "parameter_name": f"{table_name}||{row_id}",
                            "table_name": table_name,
                            "id": row_id,
                            "variable_name": var_keys[0],
                            "lower_bound": lower_val,
                            "upper_bound": upper_val,
                            "coordinate_label": coordinate_label,
                }
            )
                    

        mapping_df = pd.DataFrame(
            records,
            columns=[
                "parameter_name",
                "table_name",
                "id",
                "lower_bound",
                "upper_bound",
                "coordinate_label",
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
            "names": mapping_df["parameter_name"].tolist(),
            "bounds": mapping_df[["lower_bound", "upper_bound"]].values.tolist(),
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
                f"lower_bound={lower}, upper_bound={upper}"
            )

        if lower_val >= upper_val:
            raise ValueError(
                f"Invalid bounds in table '{table_name}', id '{row_id}'. "
                f"lower_bound >= upper_bound ({lower_val} >= {upper_val})"
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
                pd.DataFrame: Sample matrix with ``run_id`` as explicit column.
            """
            problem = self.create_sampling_problem()
            sampler = self.SAMPLERS[method]

            samples = sampler(problem, **kwargs)

            samples_df = pd.DataFrame(samples, columns=problem["names"])
            samples_df.index.name = "run_id"
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
        samples_long = samples_df.melt(
            id_vars="run_id",
            var_name="parameter_name",
            value_name="sampled_value",
        )

        coordinates_df = mapping_df[
            ["parameter_name", "coordinate_label"]
        ].drop_duplicates()

        samples_df_save = samples_long.merge(
            coordinates_df,
            on="parameter_name",
            how="left",
        )
        samples_df_save = samples_df_save[["run_id", "coordinate_label", "parameter_name", "sampled_value"]]
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

        file_path = self.paths["model_dir"] / f"uncertainty_samples.{file_format}"

        if file_format == "xlsx":
            samples_df_save.to_excel(file_path, index=False)
        elif file_format == "csv":
            samples_df_save.to_csv(file_path, index=False)
        elif file_format == "parquet":
            samples_df_save.to_parquet(file_path, index=False)



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
        is_uncertain_header = Defaults.Labels.IS_UNCERTAIN_FIELD["is_uncertain"][0]

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

            if getattr(variable, "is_uncertain", False):
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

            if not getattr(variable, "is_uncertain", False):
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
        uncertainty columns, such as `lower_bound` and `upper_bound`, are removed
        before returning the dataframe, so that the output can be passed to the
        standard CVXLab reshaping pipeline.

        Args:
            table_df: DataFrame extracted from the SQLite data table.
            table_name: Name of the SQLite data table.
            samples_df: DataFrame containing sampled values. Expected columns are
                `run_id` plus one column per uncertain parameter.
            run_id: Identifier of the uncertainty-analysis run to inject.
            separator: Separator used in sampled-parameter names.

        Returns:
            A copy of `table_df` with sampled values written into the `values`
            column and uncertainty-bound columns removed.

        Raises:
            MissingDataError: If required columns are missing, if `run_id` is not
                found, if it is duplicated, or if sampled parameters are missing.
        """

        id_header = Defaults.Labels.ID_FIELD["id"][0]
        values_header = Defaults.Labels.VALUES_FIELD["values"][0]

        # If these labels already exist in Defaults, use them.
        # Otherwise, keep the explicit strings.
        lower_bound_header = getattr(
            Defaults.Labels,
            "LOWER_BOUND_FIELD",
            {"lower_bound": ["lower_bound"]},
        )["lower_bound"][0]

        upper_bound_header = getattr(
            Defaults.Labels,
            "UPPER_BOUND_FIELD",
            {"upper_bound": ["upper_bound"]},
        )["upper_bound"][0]

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

        samples_df_run = samples_df.loc[samples_df["run_id"] == run_id]

        if samples_df_run.empty:
            msg = (
                "Sample injection failed | "
                f"No sampled values found for run_id={run_id}."
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