"""Menu actions: definitions, handlers, and the MAIN_MENU registry.

Each handler has the signature ``(config, state) -> None`` where
*config* is a ``SessionConfig`` and *state* is a ``ModelState``.

Decorate public handlers with ``@menu_action("label")`` to register
them in :data:`MAIN_MENU` (decoration order = menu order).
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Tuple, cast

import cvxlab as cl

from cvxlab.defaults import Defaults
from cvxlab.frontend import session


@dataclass
class Action:
    """A single menu entry.

    Attributes:
        label: Text shown to the user.
        handler: Function ``(config, state) -> None`` executed on selection.
        children: Optional nested actions rendered as a sub-menu.
        visible: Predicate ``(config) -> bool``; when it returns False the
            action is hidden from the menu.  Defaults to always visible.
    """
    label: str
    handler: Callable
    children: Optional[List['Action']] = field(default=None)
    visible: Callable[['session.SessionConfig'], bool] = field(
        default=lambda _: True)


# Ordered registry populated by the @menu_action decorator.
_MENU_ACTIONS: List[Tuple[str, Callable, Callable]] = []


def menu_action(
    label: str,
    visible: Callable[['session.SessionConfig'], bool] = lambda _: True,
) -> Callable:
    """Decorator that tags a handler with *label* and registers it."""
    def decorator(func: Callable) -> Callable:
        func.label = label
        _MENU_ACTIONS.append((label, func, visible))
        return func
    return decorator


def _structure_file_exists(cfg: session.SessionConfig) -> bool:
    """Return True if the model-structure file exists on disk."""
    path = Path(cfg.main_dir_path, cfg.model_structure_file)
    if not path.exists():
        print(
            f"\nWARNING | Model structure file '{cfg.model_structure_file}' "
            f"not found in '{cfg.main_dir_path}'. "
            f"Skipping update.\n"
        )
        return False
    return True


# ------------------------------------------------------------------
# Generate model directory structure and template files
# ------------------------------------------------------------------
@menu_action("Generate model directory structure and template files.")
def gen_directory(cfg: session.SessionConfig, ms: session.ModelState) -> None:
    cl.create_model_dir(
        main_dir_path=cfg.main_dir_path,
        model_dir_name=cfg.model_dir_name,
        settings_file_type=cfg.model_settings_from,
    )


# ------------------------------------------------------------------
# Update model structure from Excel file
# ------------------------------------------------------------------
@menu_action(
    "Update model structure from a source xlsx file.",
    visible=lambda cfg: cfg.model_structure_file is not None,
)
def update_structure(cfg: session.SessionConfig, ms: session.ModelState) -> None:
    if not _structure_file_exists(cfg):
        return

    choice = input(
        "\nObjects to update (1: 'settings', 2: 'sets', "
        "3: 'all', default 'all'): "
    ).strip()

    mapping = {'1': 'settings', '2': 'sets', '3': 'all'}
    if choice not in mapping:
        print("\nInvalid selection. Defaulting to 'all'.\n")
        update = 'all'
    else:
        update = mapping[choice]

    cl.transfer_setup_info_xlsx(
        source_file_name=cfg.model_structure_file,
        source_dir_path=cfg.main_dir_path,
        destination_dir_path=Path(
            cfg.main_dir_path, cfg.model_dir_name),
        update=cast(Defaults.LiteralTypes.TransferUpdate, update),
    )


# ------------------------------------------------------------------
# Initialize model and generate data structures
# ------------------------------------------------------------------
@menu_action("Initialize model and generate data structures.")
def init_model(cfg: session.SessionConfig, ms: session.ModelState) -> None:
    ms.model = cl.Model(
        **cfg.model_kwargs,
        use_existing_data=False,
    )

    if cfg.model_structure_file is not None:
        answer = input(
            "\nRefresh sets from Excel before initialization? ([y]/n): "
        ).strip().lower()

        if answer != 'n' and _structure_file_exists(cfg):
            cl.transfer_setup_info_xlsx(
                source_file_name=cfg.model_structure_file,
                source_dir_path=cfg.main_dir_path,
                destination_dir_path=Path(
                    cfg.main_dir_path, cfg.model_dir_name),
                update='sets',
            )

    ms.model._load_model_coordinates()
    ms.model._initialize_blank_data_structure()


# ------------------------------------------------------------------
# Initialize and run problems
# ------------------------------------------------------------------
@menu_action("Initialize and solve numerical problems.")
def run_model(cfg: session.SessionConfig, ms: session.ModelState) -> None:
    model = ms.ensure_model(cfg, use_existing_data=True)
    model.run_model(**cfg.solver_kwargs)


# ------------------------------------------------------------------
# Import/Refresh input data to database
# ------------------------------------------------------------------
@menu_action("Import/Refresh input data to database.")
def refresh_input_data(cfg: session.SessionConfig, ms: session.ModelState) -> None:
    model = ms.ensure_model(cfg, use_existing_data=False)
    model._load_exogenous_data_to_sqlite_database(force_overwrite=True)


# ------------------------------------------------------------------
# Export results to SQLite database
# ------------------------------------------------------------------
@menu_action("Export results to SQLite database.")
def export_results(cfg: session.SessionConfig, ms: session.ModelState) -> None:
    model = ms.ensure_model(cfg, use_existing_data=True)

    if not model.is_problem_solved:
        print("\nNo results to export. Please run the model first.\n")
        return

    model.load_results_to_database()


# ------------------------------------------------------------------
# Update sets in database
# ------------------------------------------------------------------
@menu_action(
    "Update sets in SQLite database.",
    visible=lambda cfg: cfg.model_structure_file is not None,
)
def update_sets(cfg: session.SessionConfig, ms: session.ModelState) -> None:
    if not _structure_file_exists(cfg):
        return
    cl.transfer_setup_info_xlsx(
        source_file_name=cfg.model_structure_file,
        source_dir_path=cfg.main_dir_path,
        destination_dir_path=Path(
            cfg.main_dir_path, cfg.model_dir_name),
        update='sets',
    )
    model = ms.ensure_model(cfg, use_existing_data=False)
    model._load_model_coordinates()
    model.update_sets_tables()


# ------------------------------------------------------------------
# Main menu — built automatically from the @menu_action registry.
# Order matches decoration order above.
# ------------------------------------------------------------------
MAIN_MENU: List[Action] = [
    Action(label=label, handler=handler, visible=visible)
    for label, handler, visible in _MENU_ACTIONS
]
