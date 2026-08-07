"""SALib problem construction and uncertainty sampling."""

import inspect

from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd
from SALib.sample import latin, morris, sobol

from cvxlab.backend.uncertainty.uncertainty_datahandler import UncertaintyData
from cvxlab.defaults import Defaults
from cvxlab.log_exc.logger import Logger


class UncertaintySampler:
    """Build SALib problem specifications and generate input samples."""

    SAMPLERS: dict[str, Callable[..., np.ndarray]] = {
        Defaults.UncertaintySettings.SOBOL: sobol.sample,
        Defaults.UncertaintySettings.LATIN: latin.sample,
        Defaults.UncertaintySettings.MORRIS: morris.sample,
    }

    def __init__(
        self,
        *,
        uncertainty_datahandler: UncertaintyData,
        logger: Logger,
    ) -> None:
        """Initialize the uncertainty-sampling manager."""

        self.uncertainty_datahandler = uncertainty_datahandler
        self.logger = logger
        self.uncertainty_defaults = Defaults.UncertaintySettings

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

    def _create_sampling_problem(
        self,
        groups: bool = False,
    ) -> dict[str, Any]:
        """Create the SALib problem dictionary from uncertain parameters.

        Args:
            groups: If True, include uncertainty groups in the SALib problem.

        Returns:
            SALib-compatible  sampling problem dictionary.
        Raises:
            exc.SettingsError: If grouped sampling is enabled and one or more
            parameters have no group name, or fewer than two distinct groups are
            defined.
        """

        mapping_df = self.uncertainty_datahandler.collect_uncertain_parameters()

        parameter_name_col = (
            self.uncertainty_defaults.PARAMETER_NAME
        )

        group_name_key = (
            self.uncertainty_defaults.UNCERTAINTY_GROUP_NAME_KEY
        )

        problem = {
            "num_vars": len(mapping_df),
            "names": mapping_df[
                parameter_name_col
            ].tolist(),
            "bounds": mapping_df[[
                self.uncertainty_defaults.LOWER_BOUND_KEY,
                self.uncertainty_defaults.UPPER_BOUND_KEY,
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

    def _sample_data(
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
        samples_df.index.name = self.uncertainty_defaults.RUN_ID
        samples_df.reset_index(inplace=True)

        return samples_df

    def _validate_sampling_config(
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
            self.uncertainty_defaults.MORRIS,
            self.uncertainty_defaults.SOBOL,
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

    def generate_samples(
        self,
        method: str,
        groups: bool,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], pd.DataFrame]:
        """Build the SALib problem and generate uncertainty samples.

        The method collects the uncertain parameters defined in the model data,
        creates the corresponding SALib problem specification, and generates the
        sample matrix using the selected sampling method.

        Args:
            method: Name of the selected SALib sampling method.
            groups: Whether uncertainty groups must be included in the sampling
                problem.
            **kwargs: Method-specific keyword arguments passed to the selected
                SALib sampler.

        Returns:
            tuple[dict[str, Any], pd.DataFrame]: A tuple containing:

            - the SALib problem specification;
            - the generated uncertainty sample dataframe.

        Raises:
            exc.SettingsError: If the uncertain-parameter configuration or group
                definition is invalid.
            ValueError: If the selected sampling method is unsupported or sample
                generation fails.
            TypeError: If the sampler arguments are missing or invalid.
        """

        self._validate_sampling_config(
            method=method,
            groups=groups,
            kwargs=kwargs
        )

        mappping_df, sampling_problem = (
            self._create_sampling_problem(
                groups=groups
            )
        )

        samples_df = (
            self._sample_data(
                method=method,
                problem=sampling_problem,
                **kwargs
            )
        )

        return mappping_df, sampling_problem, samples_df

    def load_samples(
        self,
        file_format: str,
        method: str,
        groups: bool,
        **kwargs: Any,
    ) -> tuple[dict[str, Any], pd.DataFrame]:
        """Load previously generated uncertainty samples.

        The method rebuilds the SALib sampling problem from the current model
        configuration and loads an existing uncertainty sample dataframe from
        the results directory.

        The loaded samples are assumed to have been generated using the same
        uncertainty configuration and sampling settings currently defined in
        the model.

        Args:
            method: Name of the selected SALib sampling method.
            groups: Whether uncertainty groups must be included in the sampling
                problem.
            file_format: File format used to store the uncertainty samples.
            **kwargs: Method-specific keyword arguments used to validate the
                current sampling configuration.

        Returns:
            tuple[dict[str, Any], pd.DataFrame]: A tuple containing:

            - the SALib problem specification;
            - the previously generated uncertainty sample dataframe.

        Raises:
            exc.SettingsError: If the uncertain-parameter configuration or group
                definition is invalid.
            FileNotFoundError: If the uncertainty samples file does not exist.
            ValueError: If the selected sampling method is unsupported.
            TypeError: If the sampling arguments are missing or invalid.
        """

        self._validate_sampling_config(
            method=method,
            groups=groups,
            kwargs=kwargs
        )

        mappping_df, sampling_problem = (
            self._create_sampling_problem(
                groups=groups
            )
        )

        samples_df = self.uncertainty_datahandler.load_samples_files(
            file_format)

        self.logger.warning(
            "Loading previously generated uncertainty samples... \n  "
            "The sampling problem has been rebuilt from the current model "
            "configuration. \n Ensure that the uncertainty configuration and "
            "sampling settings have not changed since the samples were generated; \n "
            "otherwise, the loaded samples may not correspond to the current "
            "sampling problem."
        )

        return mappping_df, sampling_problem, samples_df
