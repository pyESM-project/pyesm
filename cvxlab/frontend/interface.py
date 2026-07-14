"""Interface loop engine and public entry-point function."""
import inspect
from typing import Any, List, Optional

from cvxlab.backend.model_settings import ModelSettings
from cvxlab.backend.run_settings import RunSettings
from cvxlab.defaults import Defaults
from cvxlab.frontend import actions, display, session
from cvxlab.log_exc.exceptions import CVXLabError
from cvxlab.backward_compat import BackwardCompat


# Parameter groups — each name must match a run() parameter.
# Import-time validation ensures these stay in sync with the
# function signature; a mismatch causes an immediate RuntimeError.

_MODEL_PARAM_NAMES = set(ModelSettings.model_init_param_names())

_SOLVER_PARAM_NAMES = set(RunSettings.run_model_param_names())

_SESSION_PARAM_NAMES = {
    'model_structure_file',
    'template_file_type',
    'force_overwrite',
    'table_key_list',
    'scenarios_idx',
}


def _run_menu(
    menu_actions: List[actions.Action],
    configuration: session.SessionConfig,
    model_state: session.ModelState,
) -> None:
    """Generic menu loop that works for any list of ``Action`` objects.

    Actions whose ``visible`` predicate returns False for the current
    configuration are excluded from the menu.
    Handles sub-menus via recursion when ``action.children`` is set.
    Backend exceptions (``CVXLabError`` and subclasses) are caught so that
    only the package logger output is visible — no raw tracebacks.
    """
    visible = [a for a in menu_actions if a.visible(configuration)]
    labels = [a.label for a in visible]
    n = len(visible)

    while True:
        display.print_menu(labels)
        choice = display.prompt_choice(n)

        if choice.lower() == 'exit':
            display.exit_msg()
            break

        if not choice.isdigit() or not (1 <= int(choice) <= n):
            print(f"\nERROR. Valid selections: 1 to {n}.\n")
            continue

        action = visible[int(choice) - 1]

        display.print_log_start()
        try:
            if action.children:
                _run_menu(action.children, configuration, model_state)
            else:
                action.handler(configuration, model_state)
        except KeyboardInterrupt:
            display.print_log_end()
            print("\nOperation interrupted by user.\n")
        except CVXLabError:
            display.print_log_end()
        except Exception as exc:
            display.print_log_end()
            print(f"\nUnexpected error: {exc}\n")
        else:
            display.print_log_end()

        display.print_separator()


def run(
    # Model.__init__ parameters
    model_dir_name: Optional[str] = None,
    main_dir_path: Optional[str] = None,
    model_settings_from: Optional[Defaults.LiteralTypes.SettingsSource] = None,
    detailed_validation: Optional[bool] = None,
    multiple_input_files: Optional[bool] = None,
    input_data_files_type: Optional[Defaults.LiteralTypes.DataFileType] = None,
    log_level: Optional[Defaults.LiteralTypes.LogLevel] = None,
    log_format: Optional[Defaults.LiteralTypes.LogFormat] = None,
    # Other methods parameters
    force_overwrite: Optional[bool] = None,
    table_key_list: Optional[list[str]] = None,
    model_structure_file: Optional[str] = None,
    template_file_type: Optional[Defaults.LiteralTypes.SettingsSource] = None,
    solution_mode: Optional[Defaults.LiteralTypes.SolutionMode] = None,
    scenarios_idx: Optional[List[int] | int] = None,
    solver: Optional[str | dict[str, str]] = None,
    solver_verbose: Optional[bool | dict[str, bool]] = None,
    solver_settings: Optional[
        dict[str, Any] |
        dict[str, dict[str, Any]]
    ] = None,
    sequential_solution_chain: Optional[List[str | int]] = None,
    convergence_monitoring: Optional[bool] = None,
    convergence_norm: Optional[Defaults.LiteralTypes.NormType] = None,
    convergence_tables_to_check: Optional[
        Defaults.LiteralTypes.ConvergenceTables | List[str]] = None,
    convergence_tables_to_skip: Optional[List[str]] = None,
    relative_tolerance: Optional[float] = None,
    maximum_iterations: Optional[int] = None,
    keep_previous_iteration_db: Optional[bool] = None,
    # Catch-all for deprecated arguments (e.g. ``integrated_problems``).
    **kwargs: Any,
) -> None:
    """Launch the CVXlab guided user interface.

    All parameters are optional. When provided, they override the
    corresponding defaults in ``Model.__init__`` or ``Model.run_model()``.
    Parameters left as ``None`` are omitted, letting the backend apply
    its own defaults (or let the user specify them at runtime).

    Args:
        model_dir_name (str, optional): The name of the model directory.
            Defaults to ``'model'``.
        main_dir_path (str, optional): The main directory path where the model
            directory is located. Defaults to the current working directory.
        model_settings_from (Literal['yml', 'xlsx'], optional): The format of
            the model settings file. Can be either ``'yml'`` or ``'xlsx'``.
            Defaults to ``'xlsx'``.
        detailed_validation (bool, optional): If True, performs detailed
            validation logging of data and model settings during initialization.
            Defaults to ``False``.
        multiple_input_files (bool, optional): If True, input data Excel files
            are generated as one file per data table. If False, all data tables
            are generated in a single Excel file with multiple tabs. Defaults
            to ``False``.
        input_data_files_type (Literal['xlsx', 'csv'], optional): The format
            of the input data files. Defaults to ``'xlsx'``.
        log_level (Literal['info', 'debug', 'warning', 'error'], optional):
            The logging level for the logger. Defaults to ``'info'``.
        log_format (Literal['standard', 'detailed'], optional): The logging
            format for the logger. Defaults to ``'standard'``.
        force_overwrite (bool, optional): If True, overwrites existing
            results. Defaults to ``False``.
        solution_mode (Literal['parallel', 'sequential', 'integrated'], optional):
            The solution mode to use. Defaults to ``'parallel'``.
        scenarios_idx (Optional[List[int] | int], optional): An optional list
            of indices specifying which scenarios to solve. Indices must
            correspond to the index of the :attr:`Model.scenarios` DataFrame.
            If ``None``, all scenarios are solved. If an integer is provided,
            it is treated as a single scenario index. Defaults to ``None``.
        solver (str | dict[str, str], optional): The solver to use for solving
            numerical problems. When multiple sub-problems are available,
            a dictionary keyed by problem key can be used to define one solver
            per sub-problem. Defaults to ``None``.
        solver_verbose (bool | dict[str, bool], optional): If True, logs
            verbose output related to numerical solver operation during the
            model run. When multiple sub-problems are available, a dictionary
            keyed by problem key can be used to define verbosity per
            sub-problem. Defaults to ``False``.
        solver_settings (dict[str, Any] | dict[str, dict[str, Any]], optional):
            Additional solver settings. When multiple sub-problems are
            available, a dictionary keyed by problem key can be used to define
            dedicated settings per sub-problem. Defaults to ``None``.
        sequential_solution_chain (Optional[List[str | int]], optional): An
            optional list of problem keys or scenario indices specifying the
            order in which to solve the problems. If ``None``, problems are
            solved in the default order. Defaults to ``None``.
        convergence_monitoring (bool, optional): If True, enables convergence
            monitoring during the solving of integrated problems. Defaults to
            ``True``.
        convergence_norm (Literal['max_relative', 'max_absolute', 'l1', 'l2', 'linf'], optional):
            The norm type to use for convergence monitoring in integrated
            problems. Defaults to ``'l2'`` (Euclidean norm).
        convergence_tables_to_check (Literal['all_endogenous', 'hybrid_only'] | List[str], optional):
            The data tables to consider for convergence monitoring in integrated
            problems. Can be ``'all_endogenous'``, ``'hybrid_only'``, or a list
            of specific data table keys. Defaults to ``'all_endogenous'``.
        convergence_tables_to_skip (List[str], optional): List of data table
            keys to skip for convergence checking in integrated problems.
            Defaults to ``None`` (no tables skipped).
        relative_tolerance (float, optional): Numerical tolerance for verifying
            maximum relative change between iterations in integrated problems
            for each data table. Overrides
            ``Defaults.NumericalSettings.MODEL_COUPLING_SETTINGS``. Defaults to
            ``None``, which applies the coupling setting value of ``0.01``.
        maximum_iterations (int, optional): The maximum number of iterations
            for solving integrated problems. Overrides
            ``Defaults.NumericalSettings.MODEL_COUPLING_SETTINGS``. Defaults to
            ``None``, which applies the coupling setting value of ``20``.
        keep_previous_iteration_db (bool, optional): Whether to keep the
            database generated during the last-1 iteration. For debugging
            purposes. Defaults to ``False``.
        model_structure_file (str, optional): Name of the Excel file used to
            transfer model structure information. Defaults to ``None``, which
            disables actions that depend on a structure file.
        template_file_type (Literal['yml', 'xlsx'], optional): The type of
            template configuration file to generate when creating a model
            directory. If ``None``, the value of ``model_settings_from`` is
            used.
    """
    all_args = locals()

    def _collect_group(names: set[str]) -> dict[str, Any]:
        return {k: all_args[k] for k in names if all_args[k] is not None}

    model_kw = _collect_group(_MODEL_PARAM_NAMES)
    solver_kw = _collect_group(_SOLVER_PARAM_NAMES)

    # Merge any deprecated kwargs passed via **kwargs (e.g. `integrated_problems`)
    # before normalizing so BackwardCompat can translate them.

    solver_kw.update(kwargs)
    solver_kw = BackwardCompat.run_params(solver_kw)

    session_kw = _collect_group(_SESSION_PARAM_NAMES)

    cfg = session.SessionConfig(
        model_kwargs=model_kw,
        solver_kwargs=solver_kw,
        **session_kw,
    )

    display.clear_screen()
    display.print_header()

    _run_menu(
        menu_actions=actions.MAIN_MENU,
        configuration=cfg,
        model_state=session.ModelState()
    )


# Import-time validation: param groups ↔ run() signature
def _validate_param_groups() -> None:
    # Exclude *args / **kwargs — they are not individual named parameters.
    sig_params = {
        name
        for name, param in inspect.signature(run).parameters.items()
        if param.kind not in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )
    }
    grouped = _MODEL_PARAM_NAMES | _SOLVER_PARAM_NAMES | _SESSION_PARAM_NAMES

    missing_from_groups = sig_params - grouped
    extra_in_groups = grouped - sig_params

    if missing_from_groups or extra_in_groups:
        raise RuntimeError(
            f"run() parameter groups out of sync — "
            f"missing from groups: {missing_from_groups or '{}'}, "
            f"extra in groups: {extra_in_groups or '{}'}"
        )


# Run validation at import time so that any mismatch causes an immediate error.
_validate_param_groups()
