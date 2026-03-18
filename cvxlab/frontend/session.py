"""Session configuration and mutable state for the guided user interface."""
import os

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

import cvxlab

# Only import the Model type for type checking to avoid circular imports.
if TYPE_CHECKING:
    from cvxlab.backend.model import Model


@dataclass
class SessionConfig:
    """All settings needed for a guided session, collected in one place.

    ``model_kwargs`` and ``solver_kwargs`` carry only values explicitly
    provided by the user.  They are forwarded as-is to ``Model()`` and
    ``Model.run_model()`` respectively, which apply their own defaults
    for anything not supplied.

    ``model_structure_file`` and ``template_file_type`` are frontend-only
    settings (not ``Model`` parameters) and therefore have defaults here.
    ``model_structure_file`` defaults to ``None``; when not provided,
    actions that depend on it are silently skipped.
    """
    model_kwargs: dict[str, Any] = field(default_factory=dict)
    solver_kwargs: dict[str, Any] = field(default_factory=dict)
    model_structure_file: str | None = None
    template_file_type: str = 'xlsx'

    @property
    def model_dir_name(self) -> str:
        return self.model_kwargs.get('model_dir_name', 'model')

    @property
    def main_dir_path(self) -> str:
        return self.model_kwargs.get('main_dir_path', os.getcwd())


class ModelState:
    """Holds the live ``Model`` instance (and any future runtime state).

    Handlers receive this object so they can create, reuse, or replace
    the model without relying on globals.
    """

    def __init__(self) -> None:
        self.model: Model | None = None

    def ensure_model(
            self,
            config: SessionConfig,
            *,
            use_existing_data: bool = False
    ):
        """Return the current model, creating one if needed."""
        if self.model is None:
            self.model = cvxlab.Model(
                **config.model_kwargs,
                use_existing_data=use_existing_data,
            )
        return self.model
