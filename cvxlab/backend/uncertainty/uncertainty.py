"""Tools for collecting uncertain parameters from exogenous data tables."""


from typing import Any

import pandas as pd
import numpy as np

from cvxlab.defaults import Defaults
from cvxlab.backend.index import Index
from cvxlab.backend.model_settings import ModelPaths
from cvxlab.support.file_manager import FileManager
from cvxlab.support.sql_manager import SQLManager
from cvxlab.support import util
from cvxlab.log_exc import exceptions as exc
from cvxlab.log_exc.logger import Logger
from cvxlab.backend.uncertainty.uncertainty_datahandler import UncertaintyData
from cvxlab.backend.uncertainty.uncertainty_datasampler import UncertaintySampler
from cvxlab.backend.uncertainty.uncertainty_analyzer import UncertaintyAnalyzer


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

    def __init__(
        self,
        sqltools: SQLManager,
        index: Index,
        files: FileManager,
        paths: ModelPaths,
        logger: Logger
    ):
        """Initialize the uncertainty-analysis manager.

        Args:
            sqltools: SQLite manager used to retrieve and update data-table values.
            index: Model index containing uncertainty-enabled tables, variables,
                sets and scenario information.
            paths: Dictionary-like object containing model and result paths.
            files: File manager used to export uncertainty-analysis results.
            logger: Parent logger from which the uncertainty-specific child logger
                is created.
        """

        self.sqltools = sqltools
        self.index = index
        self.paths = paths
        self.logger = logger.get_child(__name__)
        self.files = files

        self.uncertainty_datahandler = UncertaintyData(
            files=self.files,
            paths=self.paths,
            sqltools=self.sqltools,
            index=self.index,
            logger=self.logger,
        )

        self.uncertainty_sampler = UncertaintySampler(
            uncertainty_datahandler=self.uncertainty_datahandler,
            logger=self.logger,
        )

        self.uncertainty_analyzer = UncertaintyAnalyzer(
            index=self.index,
            logger=self.logger,
        )

        self.uncertainty_defaults = Defaults.UncertaintySettings

        self.sampling_problem: dict[str, Any] | None = None
        self.uncertainty_samples: pd.DataFrame | None = None
        self.gsa_results: pd.DataFrame | None = None
        self.par_mapping: pd.DataFrame | None = None
        self.uncertainty_measures: pd.DataFrame | None = None
        self.uncertainty_measure_records: list | None = None
        self.failed_runs_report: dict | None = None

    def _warn_failed_model_runs(
        self,
        scenarios,
        failed_runs_report: dict[int, dict],
    ) -> None:
        """Log a summary warning for infeasible uncertainty-analysis runs."""

        if not failed_runs_report:
            return

        if not scenarios:
            failed_run_ids = list(failed_runs_report.keys())

            self.logger.warning(
                "Uncertainty analysis | Failed runs detected. "
                f"Failed run_id values: {failed_run_ids}."
            )

            return

        warning_lines = [
            "Uncertainty analysis | Failed scenario-runs detected."
        ]

        for run_id, failed_scenarios in failed_runs_report.items():
            scenario_info = []

            for scenario_key, status in failed_scenarios.items():
                scenario_name = util.get_scenario_name(
                    scenario_key=scenario_key,
                    scenarios_info=self.index.scenarios_info,
                    coordinates_column=(
                        Defaults.Labels.SCENARIO_COORDINATES
                    ),
                )
                if scenario_name in [None, ""]:
                    scenario_name = scenario_key

                scenario_info.append(f"{scenario_name} is {status}")

            warning_lines.append(
                f"run_id={run_id} | failed scenarios: "
                + "; ".join(scenario_info)
            )

        self.logger.warning("\n".join(warning_lines))

    def _extract_measure_value(
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
            )

        value_array = np.asarray(cvxpy_obj.value).reshape(-1)

        if value_array.size != 1:
            raise ValueError(
                f"Uncertainty measure '{var_key}' is not scalar "
                f"for scenario '{scenario_key}'. Shape: {np.asarray(cvxpy_obj.value).shape}. "
                "Only scalar uncertainty measures can be collected."
            )

        return float(value_array[0])

    def _collect_measure_records_for_run(
        self,
        run_id: int,
        statuses_by_scenario: dict[int | None, str],
    ) -> tuple[pd.DataFrame, dict[int | None, str]]:
        """Collect uncertainty-measure records for one model run.

        Successful scenarios produce records containing the solved uncertainty
        measures. Failed scenarios produce records with NaN measure values and
        retain their solver status.

        Args:
            run_id: Identifier of the uncertainty run.
            statuses_by_scenario: Solver status associated with each scenario.

        Returns:
            A tuple containing the measure records generated for the run and
            the failed scenarios with their corresponding solver status.
        """
        solved_scenarios = [
            scenario_key
            for scenario_key, status in statuses_by_scenario.items()
            if status == "optimal"
        ]

        failed_scenarios = {
            scenario_key: status
            for scenario_key, status in statuses_by_scenario.items()
            if status != "optimal"
        }

        records: list[pd.DataFrame] = []

        if solved_scenarios:
            solved_records = self._collect_uncertainty_measures_for_run(
                run_id=run_id,
                scenarios_to_collect=solved_scenarios,
            )

            if not solved_records.empty:
                records.append(solved_records)

        if failed_scenarios:
            failed_records = self._create_failed_measure_records_for_run(
                run_id=run_id,
                failed_scenarios=failed_scenarios,
            )

            if not failed_records.empty:
                records.append(failed_records)

        if not records:
            return pd.DataFrame(), failed_scenarios

        run_records = pd.concat(
            records,
            ignore_index=True,
        )

        return run_records, failed_scenarios

    def _collect_uncertainty_measures_for_run(
        self,
        run_id: int,
        scenarios_to_collect: list | None = None,
    ) -> pd.DataFrame:
        """Collect scalar uncertainty-measure values after one solved uncertainty run.

        If the model has split scenarios and ``scenarios_to_collect`` is provided,
        collect only those scenario keys. For non-split models, scenario filtering is
        skipped because the single problem may be represented either as ``None`` or
        as ``0`` in different internal dataframes.
        """

        cvxpy_var_header = Defaults.Labels.CVXPY_VAR
        sub_problem_key_header = Defaults.Labels.SUB_PROBLEM_KEY

        run_id_col = self.uncertainty_defaults.RUN_ID
        scenario_col = self.uncertainty_defaults.SCENARIO

        status_col = getattr(
            self.uncertainty_defaults,
            "STATUS",
            Defaults.Labels.PROBLEM_STATUS,
        )

        uncertainty_measure_vars = self.uncertainty_datahandler.get_uncertainty_measure_vars_list()

        records = {}
        has_split_scenarios = bool(self.index.sets_split_problem_dict)

        for var_key in uncertainty_measure_vars:

            variable = self.index.variables[var_key]

            variable_data_by_problem = util.normalize_dataframe_by_key(
                variable.data
            )

            for _, variable_data in variable_data_by_problem.items():

                if variable_data is None or variable_data.empty:
                    continue

                for _, row in variable_data.iterrows():

                    cvxpy_obj = row[cvxpy_var_header]

                    scenario_key = row.get(sub_problem_key_header, None)

                    if pd.isna(scenario_key):
                        scenario_key = None

                    if (
                        has_split_scenarios
                        and scenarios_to_collect is not None
                        and scenario_key not in scenarios_to_collect
                    ):
                        continue

                    scenario_name = None

                    if has_split_scenarios:
                        scenario_name = util.get_scenario_name(
                            scenario_key=scenario_key,
                            scenarios_info=self.index.scenarios_info,
                            coordinates_column=Defaults.Labels.SCENARIO_COORDINATES,
                        )

                    record_key = scenario_name if has_split_scenarios else None

                    if record_key not in records:

                        record = {
                            run_id_col: run_id,
                            status_col: "optimal",
                        }

                        if scenario_name is not None:
                            record[scenario_col] = scenario_name

                        records[record_key] = record

                    value = self._extract_measure_value(
                        cvxpy_obj=cvxpy_obj,
                        var_key=var_key,
                        scenario_key=scenario_key,
                    )

                    records[record_key][var_key] = value

        if not records:
            raise exc.OperationalError(
                "Uncertainty-measure collection failed | "
                f"No measure value was collected for run_id={run_id}. "
                f"Measure variables found: {uncertainty_measure_vars}. "
                "Check variable.data, sub_problem_key filtering, and cvxpy values."
            )

        records_df = pd.DataFrame(records.values())

        return records_df

    def _create_failed_measure_records_for_run(
        self,
        run_id: int,
        failed_scenarios: dict,
    ) -> pd.DataFrame:
        """Create NaN uncertainty-measure records for failed scenario-runs.

        `failed_scenarios` maps scenario keys to solver status. For a model without
        split scenarios, use {None: status}.
        """

        records = []

        run_id_col = self.uncertainty_defaults.RUN_ID
        scenario_col = self.uncertainty_defaults.SCENARIO
        status_col = self.uncertainty_defaults.STATUS

        uncertainty_measure_vars = self.uncertainty_datahandler.get_uncertainty_measure_vars_list()

        for scenario_key, status in failed_scenarios.items():
            scenario_name = util.get_scenario_name(
                scenario_key=scenario_key,
                scenarios_info=self.index.scenarios_info,
                coordinates_column=Defaults.Labels.SCENARIO_COORDINATES,
            )
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

    def _rebuild_failed_runs_report(
        self,
        temporary_measures: pd.DataFrame,
    ) -> dict[int, dict[int, str]]:
        """Rebuild the failed-runs report from temporary uncertainty measures.

        Args:
            temporary_measures: Previously saved uncertainty-measure records.

        Returns:
            Mapping of run IDs to failed scenario keys and their solver status.
        """
        run_id_col = self.uncertainty_defaults.RUN_ID
        scenario_col = self.uncertainty_defaults.SCENARIO
        status_col = self.uncertainty_defaults.STATUS

        failed_rows = (
            temporary_measures[
                temporary_measures[status_col] != "optimal"
            ]
            .drop_duplicates(
                subset=[
                    run_id_col,
                    scenario_col,
                    status_col,
                ]
            )
        )

        failed_runs_report: dict[int, dict[int, str]] = {}

        for _, row in failed_rows.iterrows():

            run_id = int(row[run_id_col])
            scenario_name = row[scenario_col]
            status = str(row[status_col])

            scenario_key = next(
                (
                    int(key)
                    for key in self.index.scenarios_info.index
                    if util.get_scenario_name(
                        scenario_key=key,
                        scenarios_info=self.index.scenarios_info,
                        coordinates_column=(
                            Defaults.Labels.SCENARIO_COORDINATES
                        ),
                    ) == scenario_name
                ),
                None,
            )

            if scenario_key is None:
                continue

            failed_runs_report.setdefault(
                run_id,
                {}
            )[scenario_key] = status

        return failed_runs_report

    def validate_uncertainty_data(self) -> None:
        """Validate row-level uncertainty metadata."""

        self.uncertainty_datahandler.validate_uncertainty_data()

    def collect_uncertain_parameters(self) -> pd.DataFrame:
        """Collect uncertain parameters from uncertainty-enabled data tables."""

        return self.uncertainty_datahandler.collect_uncertain_parameters()

    def initialize_sampling(
        self,
        resume: bool,
        method: str,
        groups: bool,
        save_samples: bool,
        file_format: str | None,
        **method_kwargs: Any,
    ) -> None:
        """Initialize the uncertainty sampling workflow.

        Generate the SALib sampling problem and uncertainty samples through the
        configured uncertainty sampler, store them in the workflow state, and
        optionally save the generated samples to file.

        Args:
            method: Name of the SALib sampling method.
            groups: Whether uncertainty groups are included in the sampling
                problem.
            save_samples: Whether the generated uncertainty samples are saved to
                file.
            file_format: Output file format used when saving the samples. This
                argument is ignored when ``save_samples`` is ``False``.
            **method_kwargs: Method-specific arguments passed to the selected
                SALib sampler.
        """

        if not resume:

            (
                self.par_mapping,
                self.sampling_problem,
                self.uncertainty_samples,
            ) = self.uncertainty_sampler.generate_samples(
                method=method,
                groups=groups,
                **method_kwargs,
            )

            if save_samples:
                self.uncertainty_datahandler.save_uncertainty_result(
                    dataframe=self.uncertainty_samples,
                    result_type=self.uncertainty_defaults.SAMPLES,
                    file_format=file_format
                )
        elif resume:

            (
                self.par_mapping,
                self.sampling_problem,
                self.uncertainty_samples,
            ) = self.uncertainty_sampler.load_samples(
                file_format=file_format,
                method=method,
                groups=groups,
                ** method_kwargs
            )

    def get_deterministic_vars(self):
        """Return variables belonging to fully deterministic data tables.

        Fully deterministic tables are tables that do not contain any uncertain
        data rows and therefore need to be loaded only once before executing the
        uncertainty runs.

        Returns:
            Names of the exogenous variables associated with fully deterministic
            tables.
        """
        deterministic_tables = (
            self.uncertainty_datahandler.get_deterministic_tables()
        )

        return self.uncertainty_datahandler.get_vars_in_tables_list(
            deterministic_tables
        )

    def get_uncertain_vars(self):
        """Return variables belonging to fully deterministic data tables.

        Fully deterministic tables are tables that do not contain any uncertain
        data rows and therefore need to be loaded only once before executing the
        uncertainty runs.

        Returns:
            Names of the exogenous variables associated with fully deterministic
            tables.
        """
        uncertain_tables = (
            self.uncertainty_datahandler.get_uncertain_tables()
        )

        return self.uncertainty_datahandler.get_vars_in_tables_list(
            uncertain_tables
        )

    def initialize_run_results(
            self,
            resume: bool,
            file_format: str,
    ) -> None:
        """Initialize result containers for an uncertainty campaign.

        When resuming a previous campaign, previously collected temporary
        uncertainty measures are loaded and restored in the result container.

        Args:
            resume: Whether to resume a previously interrupted uncertainty campaign.
            file_format: File format used for temporary uncertainty results.

        Returns:
            First run ID to execute.
        """

        run_ids = self.uncertainty_samples[Defaults.UncertaintySettings.RUN_ID]

        if not resume:
            self.uncertainty_measure_records = []
            self.failed_runs_report = {}

        elif resume:

            temporary_measures = self.uncertainty_datahandler.load_temp_measures_files(
                file_format=file_format,
            )

            self.uncertainty_measure_records = [temporary_measures]

            run_id_col = self.uncertainty_defaults.RUN_ID

            run_id_start = int(temporary_measures[run_id_col].max() + 1)

            self.failed_runs_report = (
                self._rebuild_failed_runs_report(
                    temporary_measures
                )
            )

            run_ids = range(run_id_start, int(run_ids.max()) + 1)

        return run_ids

    def sampled_data_to_df(
        self,
        table_df: pd.DataFrame,
        run_id: int,
        table_name: str,
    ) -> pd.DataFrame:
        """Inject sampled values into an uncertainty-enabled data table.

        Args:
            table_df: Exogenous data table to update.
            run_id: Identifier of the uncertainty sample to inject.
            table_name: Name of the table being updated.

        Returns:
            A dataframe containing the sampled values associated with the selected
            uncertainty run.
        """
        return self.uncertainty_datahandler.inject_sampled_values_by_row(
            table_df=table_df,
            samples_df=self.uncertainty_samples,
            run_id=run_id,
            table_name=table_name,
        )

    def update_run_results(
        self,
        run_id: int,
        statuses_by_scenario: dict,
        temp_save: bool,
        file_format: str | None,
    ) -> None:
        """Update the accumulated results of an uncertainty run.

        Store the uncertainty-measure records generated for the current run,
        register any failed scenarios, and optionally save the measures collected
        up to the current run.

        Args:
            run_id: Identifier of the completed uncertainty run.
            run_records: Measure records collected for the run.
            failed_scenarios: Mapping of failed scenarios to their solver status.
            temp_save: Whether accumulated measure records are saved after the run.
            file_format: File format used for temporary result storage. This
                argument is ignored when ``temp_save`` is ``False``.
        """
        run_records, failed_scenarios = (
            self._collect_measure_records_for_run(
                run_id=run_id,
                statuses_by_scenario=statuses_by_scenario,
            )
        )

        if not run_records.empty:
            self.uncertainty_measure_records.append(run_records)

        if failed_scenarios:
            self.failed_runs_report[run_id] = failed_scenarios

        if temp_save and self.uncertainty_measure_records:

            temporary_measures = pd.concat(
                self.uncertainty_measure_records,
                ignore_index=True,
            )

            self.uncertainty_datahandler.save_uncertainty_result(
                dataframe=temporary_measures,
                result_type=self.uncertainty_defaults.TEMP_MEASURES,
                file_format=file_format,
            )

    def finalize_run_results(
        self,
        save_measures: bool,
        file_format: str | None,
        scenarios: dict[Any, Any],
    ) -> None:
        """Finalize and store the results of an uncertainty campaign.

        Concatenate the collected measure records, store the resulting dataframe,
        optionally save it to file, and report failed scenario-runs.

        Args:
            save_measures: Whether final uncertainty measures are saved to file.
            file_format: File format used for final measure storage.
            scenarios: Scenario metadata used to report failed scenario-runs.

        Raises:
            exc.MissingDataError: If no uncertainty-measure records were collected.
        """
        if not self.uncertainty_measure_records:
            msg = (
                "Uncertainty analysis completed without producing "
                "measure records."
            )
            self.logger.error(msg)
            raise exc.MissingDataError(msg)

        uncertainty_measures = pd.concat(
            self.uncertainty_measure_records,
            ignore_index=True,
        )

        self.uncertainty_measures = uncertainty_measures

        if save_measures:
            self.uncertainty_datahandler.save_uncertainty_result(
                dataframe=uncertainty_measures,
                result_type=Defaults.UncertaintySettings.MEASURES,
                file_format=file_format,
            )
        if self.failed_runs_report:
            self._warn_failed_model_runs(
                scenarios=scenarios,
                failed_runs_report=self.failed_runs_report,
            )

    def validate_gsa_configuration(
        self,
        *,
        sampling_method: str,
        analysis_method: str,
        method_kwargs: dict[str, Any],
    ) -> None:
        """Validate the GSA analysis configuration."""
        self.uncertainty_analyzer.validate_analysis_config(
            method=analysis_method,
            kwargs=method_kwargs,
        )

        self.uncertainty_analyzer.validate_sampling_analysis_compatibility(
            sampling_method=sampling_method,
            analysis_method=analysis_method,
        )

    def get_results_analysis(
            self,
            method: str,
            groups: bool,
            measures: list[str] | None = None,
            scenarios: list[str] | None = None,
            save_analysis: bool = True,
            file_format: str | None = None,
            **method_kwargs: Any,
    ) -> None:
        """Perform and optionally save global sensitivity analysis.

        Delegate the computation of sensitivity indices to the GSA analyzer,
        store the resulting dataframe in the workflow state, and optionally save
        it to file.

        Args:
            method: Name of the SALib sensitivity-analysis method.
            groups: Whether the sampling problem was generated using uncertainty
                groups.
            measures: Uncertainty measures to analyze. If omitted, all available
                measures are analyzed.
            scenarios: Scenarios to analyze. If omitted, all available scenarios
                are analyzed.
            save_analysis: Whether the computed GSA results are saved to file.
            file_format: Output file format used when saving the results. This
                argument is ignored when ``save_analysis`` is ``False``.
            **method_kwargs: Method-specific arguments passed to the selected
                SALib analyzer.

        Returns:
            Global sensitivity analysis results in long-format tabular form.

        Raises:
            exc.MissingDataError: If the sampling problem, uncertainty samples,
                uncertainty measures, or parameter mapping are unavailable.
        """
        self.gsa_results = self.uncertainty_analyzer.analyze_results(
            sampling_problem=self.sampling_problem,
            samples_df=self.uncertainty_samples,
            measures_df=self.uncertainty_measures,
            mapping_df=self.par_mapping,
            method=method,
            groups=groups,
            measures=measures,
            scenarios=scenarios,
            **method_kwargs,
        )

        if save_analysis:
            self.uncertainty_datahandler.save_uncertainty_result(
                dataframe=self.gsa_results,
                result_type=self.uncertainty_defaults.GSA_RESULTS,
                file_format=file_format,
            )
