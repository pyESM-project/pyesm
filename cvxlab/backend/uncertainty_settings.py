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
        file_format: str = "xlsx",
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
