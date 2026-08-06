import inspect
from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd
from SALib.analyze import (
    delta,
    morris as morris_analyze,
    rbd_fast,
    sobol as sobol_analyze,
)

from cvxlab.backend.index import Index
from cvxlab.defaults import Defaults
from cvxlab.log_exc import exceptions as exc
from cvxlab.log_exc.logger import Logger
from cvxlab.support import util


class UncertaintyAnalyzer:
    """Perform global sensitivity analysis on uncertainty-model outputs.

    The class validates the selected SALib analysis method, checks its
    compatibility with the sampling design, prepares aligned model-input and
    model-output arrays, executes the analysis, and converts the resulting
    sensitivity indices to CVXLab tabular format.

    The class does not own the uncertainty workflow state. Sampling problems,
    input samples, parameter mappings, and model-output measures are supplied
    explicitly by the caller.
    """

    ANALYZERS: dict[str, Callable[..., Any]] = {
        Defaults.UncertaintySettings.SOBOL:
            sobol_analyze.analyze,
        Defaults.UncertaintySettings.MORRIS:
            morris_analyze.analyze,
        Defaults.UncertaintySettings.DELTA:
            delta.analyze,
        Defaults.UncertaintySettings.RBD_FAST:
            rbd_fast.analyze,
    }

    def __init__(
        self,
        index: Index,
        logger: Logger,
    ) -> None:
        """Initialize the global sensitivity analysis manager.

        Args:
            index: Model index containing scenario and coordinate metadata.
            logger: Parent logger used to create the analysis-specific logger.
        """
        self.index = index
        self.logger = logger.get_child(__name__)
        self.uncertainty_defaults = Defaults.UncertaintySettings

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

    def _prepare_gsa_analysis_targets(
        self,
        samples_df: pd.DataFrame,
        measures_df: pd.DataFrame,
        method: str,
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
        run_id_col = self.uncertainty_defaults.RUN_ID
        scenario_col = self.uncertainty_defaults.SCENARIO

        technical_cols = {run_id_col,
                          scenario_col,
                          self.uncertainty_defaults.STATUS}

        samples_run_ids = samples_df[[run_id_col]].drop_duplicates()

        available_measures = [
            col for col in measures_df.columns
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

        has_scenarios = scenario_col in measures_df.columns

        if has_scenarios:
            available_scenarios = sorted(
                measures_df[scenario_col]
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
                df_target = measures_df.loc[
                    measures_df[scenario_col].astype(
                        str).eq(str(scenario))
                ].copy()
            else:
                df_target = measures_df.copy()

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

                    if method in self.uncertainty_defaults.NOT_NAN_COMPATIBLE_METHODS:
                        self.logger.warning(
                            "SALib target preparation failed | "
                            f"Analysis method '{method}' requires a complete "
                            "sampling design, unfeasible outputs "
                            f"were found for scenario '{scenario}', run_id(s): "
                            f"{missing_run_ids}."
                        )

                        break

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

    def _prepare_gsa_input_matrix(
        self,
        sampling_problem: dict,
        samples_df: pd.DataFrame,
    ) -> np.ndarray:
        """Convert samples_df into the SALib input matrix X.

        The column order must exactly match problem["names"].
        """

        run_id_col = self.uncertainty_defaults.RUN_ID
        parameter_names = sampling_problem["names"]

        samples_ordered = samples_df.sort_values(run_id_col)

        X = samples_ordered[parameter_names].to_numpy(dtype=float)

        return X

    def _build_gsa_inputs(
        self,
        sampling_problem,
        method: str,
        X: np.ndarray,
        Y: np.ndarray,
    ) -> dict[str, Any]:
        """Build the required positional inputs for the selected SALib analyzer."""

        required_inputs = self.uncertainty_defaults.ANALYZER_REQUIRED_INPUTS[method]

        inputs = {}

        if "problem" in required_inputs:
            inputs["problem"] = sampling_problem

        if "X" in required_inputs:
            inputs["X"] = X

        if "Y" in required_inputs:
            inputs["Y"] = Y

        return inputs

    def _gsa_result_to_dataframe(
            self,
            mapping_df: pd.DataFrame,
            result: Any,
            method: str,
            groups: bool,
            measure: str,
            scenario: str | None,
    ) -> pd.DataFrame:
        """Convert a SALib analysis result into a long-format dataframe."""

        parameter_name_col = self.uncertainty_defaults.PARAMETER_NAME
        group_name_col = self.uncertainty_defaults.UNCERTAINTY_GROUP_NAME_KEY

        result_dict = dict(result)
        result_names = result_dict.get(
            self.uncertainty_defaults.SALIB_RESULTS_NAME_COL)

        result_names = list(result_names)

        result_name_col = (
            group_name_col
            if groups
            else parameter_name_col
        )

        records: list[dict[str, Any]] = []

        for metric, values in result_dict.items():
            if metric == self.uncertainty_defaults.SALIB_RESULTS_NAME_COL:
                continue

            if np.ma.isMaskedArray(values):
                values_array = np.ma.filled(values, np.nan)
            else:
                values_array = np.asarray(values)

            if not np.issubdtype(values_array.dtype, np.number):
                continue

            if values_array.ndim != 1:
                continue

            if len(values_array) != len(result_names):
                raise exc.OperationalError(
                    "SALib result conversion failed | "
                    f"Metric '{metric}' contains "
                    f"{len(values_array)} values, but SALib returned "
                    f"{len(result_names)} names: {result_names}."
                )

            for result_name, value in zip(
                result_names,
                values_array,
            ):
                record = {
                    self.uncertainty_defaults.METHOD: method,
                    result_name_col: result_name,
                    self.uncertainty_defaults.INDEX_NAME: metric,
                    self.uncertainty_defaults.INDEX_VALUE: float(value),
                    self.uncertainty_defaults.OUTPUT_NAME: measure,
                }

                if scenario is not None:
                    record[
                        self.uncertainty_defaults.SCENARIO
                    ] = scenario

                records.append(record)

        result_df = pd.DataFrame(records)

        last_cols = [
            self.uncertainty_defaults.OUTPUT_NAME,
            self.uncertainty_defaults.INDEX_NAME,
            self.uncertainty_defaults.INDEX_VALUE,
        ]

        if not groups:
            excluded_metadata_cols = {
                Defaults.Labels.ID_FIELD["id"][0],
                parameter_name_col,
                self.uncertainty_defaults.LOWER_BOUND_KEY,
                self.uncertainty_defaults.UPPER_BOUND_KEY,
                self.uncertainty_defaults.METHOD,
                group_name_col,
            }

            split_problem_coordinate_cols = (
                util.get_split_problem_coordinate_columns(
                    sets=self.index.sets,
                    name_label=Defaults.Labels.NAME,
                )
            )

            metadata_cols = [
                column
                for column in mapping_df.columns
                if column not in excluded_metadata_cols
                and column not in split_problem_coordinate_cols
            ]

            parameter_mapping = (
                mapping_df[
                    [
                        parameter_name_col,
                        *metadata_cols,
                    ]
                ]
                .drop_duplicates()
            )

            result_df = result_df.merge(
                parameter_mapping,
                on=parameter_name_col,
                how="left",
                validate="many_to_one",
            )

            result_df = result_df.drop(
                columns=parameter_name_col,
            )

        first_cols = [
            column
            for column in result_df.columns
            if column not in last_cols
        ]

        return result_df[first_cols + last_cols]

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
        compatibility_map = self.uncertainty_defaults.ANALYSIS_COMPATIBILITY

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

        if method not in self.ANALYZERS:
            raise ValueError(
                f"GSA analysis method '{method}' not supported. "
                f"Available methods: {list(self.ANALYZERS.keys())}."
            )

        excluded_args = self.uncertainty_defaults.ANALYZER_REQUIRED_INPUTS[method]

        self._validate_analysis_kwargs(
            function=self.ANALYZERS[method],
            kwargs=kwargs,
            excluded_args=excluded_args,
            context="analysis",
        )

    def analyze_results(
        self,
        sampling_problem: dict,
        samples_df: pd.DataFrame,
        measures_df: pd.DataFrame,
        mapping_df: pd.DataFrame,
        method: str,
        groups: bool,
        measures: list[str] | None = None,
        scenarios: list[str] | None = None,
        **kwargs: Any,
    ) -> pd.DataFrame:
        """Run SALib GSA analysis for each selected measure-scenario pair.

        SALib analyzes one scalar output vector Y at a time. Therefore, when the
        model has multiple uncertainty measures and/or multiple scenarios, this
        method repeats the analysis for each selected combination.
        """

        if measures_df is None:
            raise ValueError(
                "No uncertainty-measure outputs found. "
                "Call model.run_uncertainty_analysis() before analyze_uncertainty()."
            )
        targets = self._prepare_gsa_analysis_targets(
            samples_df=samples_df,
            measures_df=measures_df,
            method=method,
            measures=measures,
            scenarios=scenarios,
        )

        analyzer = self.ANALYZERS[method]
        records = []
        for target in targets:
            selected_samples_df = (
                samples_df
                .set_index(self.uncertainty_defaults.RUN_ID)
                .loc[target["run_ids"]]
                .reset_index()
            )

            X = self._prepare_gsa_input_matrix(
                sampling_problem=sampling_problem,
                samples_df=selected_samples_df,
            )

            analysis_inputs = self._build_gsa_inputs(
                method=method,
                sampling_problem=sampling_problem,
                X=X,
                Y=target["Y"],
            )

            result = analyzer(
                **analysis_inputs,
                **kwargs,
            )

            result_df = self._gsa_result_to_dataframe(
                mapping_df=mapping_df,
                result=result,
                method=method,
                groups=groups,
                measure=target["measure"],
                scenario=target["scenario"],
            )

            records.append(result_df)

        if not records:
            return pd.DataFrame()

        records_df = pd.concat(records, ignore_index=True)

        return records_df
