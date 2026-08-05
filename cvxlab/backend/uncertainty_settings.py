"""Validated containers for uncertainty-analysis settings."""

from __future__ import annotations

from typing import Any

from cvxlab.defaults import Defaults
from cvxlab.log_exc.logger import Logger


class SamplingSettings:
    """Validated container for uncertainty-sampling configuration.

    The class validates and stores the configuration selected through
    :meth:`Model.sampling_settings`.

    Attributes:
        method: Selected SALib sampling method.
        method_kwargs: Keyword arguments passed to the sampler.
        groups: Whether grouped sampling is enabled.
        save_samples: Whether generated samples are exported.
        save_measures: Whether uncertainty measures are exported.
        temp_save: Whether measures are saved progressively during the runs.
        file_format: Output format used for exported dataframes.
    """

    def __init__(
        self,
        *,
        is_uncertainty_analysis: bool = False,
        logger: Logger,
        method: str,
        method_kwargs: dict[str, Any] | None = None,
        groups: bool = False,
        save_samples: bool = True,
        save_measures: bool = True,
        temp_save: bool = True,
        file_format: str | None,
    ) -> None:
        """Validate, normalize and store sampling settings."""

        if method_kwargs is None:
            method_kwargs = {}

        if not isinstance(method, str):
            raise TypeError("'method' must be a string.")

        if not isinstance(groups, bool):
            raise TypeError("'groups' must be a boolean.")

        if not isinstance(save_samples, bool):
            raise TypeError("'save_samples' must be a boolean.")

        if not isinstance(save_measures, bool):
            raise TypeError("'save_measures' must be a boolean.")

        if not isinstance(temp_save, bool):
            raise TypeError("'temp_save' must be a boolean.")

        if not is_uncertainty_analysis:
            raise ValueError(
                "Uncertainty analysis is not enabled. "
                f"Create the model with "
                f"{Defaults.Labels.UNCERTAINTY_SETTING_KEY}=True."
            )

        method = method.lower()
        file_format = file_format.lower()

        allowed_formats = (
            Defaults.UncertaintySettings.AVAILABLE_EXPORT_FORMATS
        )

        if file_format not in allowed_formats:
            raise ValueError(
                f"Output format '{file_format}' is not supported. "
                f"Available formats: {allowed_formats}."
            )

        if not save_samples:
            logger.warning(
                "Uncertainty sampling settings | Samples will not be saved."
            )

        if not save_measures:
            logger.warning(
                "Uncertainty sampling settings | Measures will not be saved."
            )

        if temp_save and not save_measures:
            raise ValueError(
                "Uncertainty sampling settings | "
                "'temp_save=True' requires 'save_measures=True'."
            )
        if not save_samples and file_format is not None:
            logger.warning(
                "Uncertainty analysis | 'file_format' specified but "
                "'save_samples=False'. Samples will not be saved."
            )

        if save_samples and file_format is None:
            file_format = "xlsx"
            logger.warning(
                "file format not specified, set to default xlsx."
            )
        if not save_measures and file_format is not None:
            logger.warning(
                "Uncertainty analysis | 'file_format' specified but "
                "'save_measures=False'. Measures will not be saved."
            )
        self.method = method
        self.method_kwargs = method_kwargs
        self.groups = groups
        self.save_samples = save_samples
        self.save_measures = save_measures
        self.temp_save = temp_save
        self.file_format = file_format

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"method='{self.method}', "
            f"groups={self.groups}, "
            f"save_samples={self.save_samples}, "
            f"save_measures={self.save_measures}, "
            f"temp_save={self.temp_save}, "
            f"file_format='{self.file_format}')"
        )


class GSASettings:
    """Validated container for global sensitivity analysis settings.

    Normalizes user selections, validates the selected SALib analyzer and its
    keyword arguments, and checks compatibility with the configured sampling
    method.

    Raises:
        ValueError: If uncertainty analysis is disabled, the selected analyzer
            is unsupported, or the sampling and analysis methods are
            incompatible.
        TypeError: If measures, scenarios, or analyzer keyword arguments have
            invalid types.
    """

    def __init__(
        self,
        *,
        logger: Logger,
        uncertainty_enabled: bool,
        method: str,
        method_kwargs: dict[str, Any] | None = None,
        measures: list[str] | None = None,
        scenarios: list[str] | None = None,
        save_analysis: bool = True,
        file_format: Defaults.LiteralTypes.DataFileType | None = "xlsx",
    ) -> None:
        """Validate and store GSA settings.

        Args:
            logger: Logger instance used during validation.
            uncertainty_enabled: Whether uncertainty analysis is enabled for
                the model.
            sampling_method: Sampling method previously configured through
                ``Model.sampling_settings()``.
            method: SALib analysis method.
            analyzers: Mapping between supported method names and SALib
                analyzer functions.
            analyzer_required_inputs: Analyzer arguments supplied internally
                by CVXLab and therefore unavailable as user-defined keyword
                arguments.
            method_kwargs: Additional keyword arguments passed to the selected
                SALib analyzer.
            measures: Uncertainty measures to analyze. A single measure can be
                passed as a string.
            scenarios: Scenarios to analyze. A single scenario can be passed
                as a string.
            save_analysis: Whether analysis results should be saved.
            file_format: Output format used when saving analysis results.
        """
        if not uncertainty_enabled:
            raise ValueError(
                "Uncertainty analysis is not enabled. "
                "Create the model with "
                f"{Defaults.Labels.UNCERTAINTY_SETTING_KEY}=True."
            )

        if not isinstance(method, str):
            raise TypeError(
                "'method' must be a string."
            )

        method_kwargs = (
            {}
            if method_kwargs is None
            else method_kwargs.copy()
        )

        if not isinstance(method_kwargs, dict):
            raise TypeError(
                "'method_kwargs' must be a dictionary or None."
            )

        if measures is not None and not isinstance(measures, list):
            raise TypeError(
                "'measures' must be a string, a list of strings, or None."
            )

        if scenarios is not None and not isinstance(scenarios, list):
            raise TypeError(
                "'scenarios' must be a string, a list of strings, or None."
            )

        if not isinstance(save_analysis, bool):
            raise TypeError(
                "'save_analysis' must be a boolean."
            )

        if not save_analysis and file_format is not None:
            logger.warning(
                "GSA settings | 'file_format' was specified while "
                "'save_analysis=False'. Analysis results will not be saved."
            )

        if file_format is not None:
            valid_file_formats = (
                Defaults.UncertaintySettings.AVAILABLE_EXPORT_FORMATS
            )

            if file_format not in valid_file_formats:
                raise ValueError(
                    f"Unsupported GSA results file format '{file_format}'. "
                    f"Available formats: {sorted(valid_file_formats)}."
                )

        self.method = method
        self.method_kwargs = method_kwargs
        self.measures = measures
        self.scenarios = scenarios
        self.save_analysis = save_analysis
        self.file_format = file_format

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"method='{self.method}', "
            f"measures={self.measures}, "
            f"scenarios={self.scenarios}, "
            f"save_analysis={self.save_analysis}, "
            f"file_format={self.file_format!r})"
        )
