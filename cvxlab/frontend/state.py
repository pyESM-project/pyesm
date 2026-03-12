"""Mutable session state shared across menu actions."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cvxlab.backend.model import Model


class ModelState:
    """Holds the live ``Model`` instance (and any future runtime state).

    Handlers receive this object so they can create, reuse, or replace
    the model without relying on globals.
    """

    def __init__(self) -> None:
        self.model: Model | None = None

    def ensure_model(self, config, *, use_existing_data: bool = False):
        """Return the current model, creating one if needed."""
        if self.model is None:
            import cvxlab as cl
            self.model = cl.Model(
                model_dir_name=config.model_dir_name,
                main_dir_path=config.main_dir_path,
                log_level=config.log_level,
                model_settings_from=config.model_settings_from,
                multiple_input_files=config.multiple_input_files,
                use_existing_data=use_existing_data,
                detailed_validation=config.detailed_validation,
            )
        return self.model
