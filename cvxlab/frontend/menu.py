"""Menu definition: Action dataclass and the MAIN_MENU registry.

Keys are assigned automatically based on list order, so adding a new
action is just appending one ``Action(...)`` entry (no explicit key needed).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from cvxlab.frontend import actions


@dataclass
class Action:
    """A single menu entry.

    Attributes:
        label: Text shown to the user.
        handler: Function ``(config, state) -> None`` executed on selection.
        children: Optional nested actions rendered as a sub-menu.
    """
    label: str
    handler: Callable
    children: Optional[List['Action']] = field(default=None)


# ------------------------------------------------------------------
# Main menu — order determines the numeric key shown to the user.
# ------------------------------------------------------------------
MAIN_MENU: List[Action] = [
    Action(
        label="Initialize model and generate data structures.",
        handler=actions.init_model,
    ),
    Action(
        label="Run model based on existing data structures.",
        handler=actions.run_model,
    ),
    Action(
        label="Refresh exogenous data and run model.",
        handler=actions.refresh_and_run,
    ),
    Action(
        label="Refresh and update sets in database.",
        handler=actions.update_sets,
    ),
    Action(
        label="Update model structure from Excel file (no model run).",
        handler=actions.update_structure,
    ),
    Action(
        label="Generate model directory structure and template files.",
        handler=actions.gen_directory,
    ),
]
