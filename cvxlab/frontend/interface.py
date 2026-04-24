"""Interface loop engine and public entry-point function."""
import inspect
from typing import Any, Dict, List, Optional

from cvxlab.defaults import Defaults
from cvxlab.frontend import actions, display, session
from cvxlab.log_exc.exceptions import CVXLabError


# Parameter groups — each name must match a run() parameter.
# Import-time validation ensures these stay in sync with the
# function signature; a mismatch causes an immediate RuntimeError.

_MODEL_PARAM_NAMES = {
    'model_dir_name', 'main_dir_path', 'Uncertainty', 'model_settings_from',
    'detailed_validation', 'multiple_input_files', 'input_data_files_type',
    'log_level', 'log_format',
}

_SOLVER_PARAM_NAMES = {
    'solver', 'solver_verbose', 'solver_settings',
    'integrated_problems', 'convergence_monitoring', 'convergence_norm',
    'convergence_tables_to_check', 'convergence_tables_to_skip',
    'relative_tolerance', 'maximum_iterations', 'keep_previous_iteration_db',
}

_SESSION_PARAM_NAMES = {'model_structure_file', 'template_file_type'}


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
    Uncertainty: Optional[bool] = None,
    model_settings_from: Optional[Defaults.LiteralTypes.SettingsSource] = None,
    detailed_validation: Optional[bool] = None,
    multiple_input_files: Optional[bool] = None,
    input_data_files_type: Optional[Defaults.LiteralTypes.DataFileType] = None,
    log_level: Optional[Defaults.LiteralTypes.LogLevel] = None,
    log_format: Optional[Defaults.LiteralTypes.LogFormat] = None,
    # Model.run_model parameters
    solver: Optional[str] = None,
    solver_verbose: Optional[bool] = None,
    solver_settings: Optional[Dict[str, Any]] = None,
    integrated_problems: Optional[bool] = None,
    convergence_monitoring: Optional[bool] = None,
    convergence_norm: Optional[Defaults.LiteralTypes.NormType] = None,
    convergence_tables_to_check: Optional[
        Defaults.LiteralTypes.ConvergenceTables | List[str]] = None,
    convergence_tables_to_skip: Optional[List[str]] = None,
    relative_tolerance: Optional[float] = None,
    maximum_iterations: Optional[int] = None,
    keep_previous_iteration_db: Optional[bool] = None,
    # Frontend-only parameters
    model_structure_file: Optional[str] = None,
    template_file_type: Optional[Defaults.LiteralTypes.SettingsSource] = None,
) -> None:
    """Launch the CVXlab guided user interface.

    All parameters are optional. When provided, they override the
    corresponding defaults in ``Model.__init__`` or ``Model.run_model()``.
    Parameters left as ``None`` are omitted, letting the backend apply
    its own defaults (or let the user specify them at runtime).

    Args:
        model_dir_name (str, optional): The name of the model directory.
        main_dir_path (str, optional): The main directory path where the model 
            directory is located. If None, the current working directory is used.
        Uncertainty (bool, optional): If True, include uncertainty-related
            columns in the generated model settings template.
        model_settings_from (Literal['yml', 'xlsx'], optional): The format of 
            the model settings file. Can be either 'yml' or 'xlsx'.
        detailed_validation (bool, optional): If True, performs detailed 
            validation logging of data and model settings during initialization.
        multiple_input_files (bool, optional): If True, input data Excel files 
            are generated as one file per data table. If False, all data tables 
            are generated in a single Excel file with multiple tabs.
        input_data_files_type (Literal['xlsx', 'csv'], optional): The format
            of the input data files.
        log_level (Literal['info', 'debug', 'warning', 'error'], optional):
            The logging level for the logger.
        log_format (Literal['standard', 'detailed'], optional): The logging
            format for the logger.
        solver (str, optional): The solver to use for solving numerical
            problems. If None, the default solver specified in
            'Defaults.NumericalSettings.CVXPY_DEFAULT_SETTINGS' is used.
        solver_verbose (bool, optional): If True, logs verbose output related
            to numerical solver operation during the model run.
        solver_settings (dict[str, Any], optional): Additional settings
            for the solver passed as key-value pairs.
        integrated_problems (bool, optional): If True, solve problems
            iteratively using a block Gauss-Seidel (alternating optimization)
            scheme, where updated endogenous variables are exchanged until
            convergence.
        convergence_monitoring (bool, optional): If True, enables convergence
            monitoring during the solving of integrated problems.
        convergence_norm (Literal['max_relative', 'max_absolute', 'l1', 'l2', 'linf'], optional): 
            The norm type to use for convergence monitoring in integrated problems.
        convergence_tables_to_check (Literal['all_endogenous', 'hybrid_only'] | List[str], optional): 
            The data tables to consider for convergence monitoring in integrated problems. 
            Can be 'all_endogenous', 'hybrid_only', or a list of specific data table keys.
        convergence_tables_to_skip (List[str], optional): List of data table
            keys to skip for convergence checking in integrated problems.
        relative_tolerance (float, optional): Numerical tolerance for verifying
            maximum relative change between iterations in integrated problems
            for each data table. Overrides 'Defaults.NumericalSettings.MODEL_COUPLING_SETTINGS'.
        maximum_iterations (int, optional): The maximum number of iterations
            for solving integrated problems. Overrides 'Defaults.NumericalSettings.MODEL_COUPLING_SETTINGS'.
        keep_previous_iteration_db (bool, optional): Whether to keep the database 
            generated during the last-1 iteration. For debugging purpose. 
        model_structure_file (str, optional): Name of the Excel file used to
            transfer model structure information.
        template_file_type (Literal['yml', 'xlsx'], optional): The type of
            template configuration file to generate when creating a model
            directory. Defaults to 'xlsx'.


    Example::

        import cvxlab
        cvxlab.run(
            model_dir_name='my_model',
            main_dir_path='/path/to/models',
            log_level='debug',
            solver='ECOS',
        )
    """
    all_args = locals()

    def _collect_group(names: set[str]) -> dict[str, Any]:
        return {k: all_args[k] for k in names if all_args[k] is not None}

    model_kw = _collect_group(_MODEL_PARAM_NAMES)
    solver_kw = _collect_group(_SOLVER_PARAM_NAMES)
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
    sig_params = set(inspect.signature(run).parameters)
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
