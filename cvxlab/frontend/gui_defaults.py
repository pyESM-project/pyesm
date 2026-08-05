"""Default structures and messages for the guided user interface."""
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class Parameter:
    """Interactive information associated with one callable parameter."""
    label: str
    parser: str = 'string'
    choices: Optional[tuple[Any, ...]] = None
    when_parameter: Optional[str] = None
    when_values: Optional[tuple[Any, ...]] = None
    model_attribute: Optional[str] = None
    default_from: Optional[str] = None


@dataclass(frozen=True)
class Action:
    """Definition of one menu action or menu group."""
    name: str
    label: str
    target: str = 'model'
    arguments: dict[str, Parameter] = field(default_factory=dict)
    children: tuple['Action', ...] = ()
    fixed_arguments: dict[str, Any] = field(default_factory=dict)
    model_arguments: tuple[str, ...] = ()
    print_result: bool = False
    assign_model: bool = False
    require_model: bool = False


class GuiDefaults:
    """Central definitions used to configure and render the GUI."""

    SEPARATOR = "-" * 49
    HEADER = "             CVXlab User Interface              "
    MENU_TITLE = "Available actions:\n"
    BACK_OPTION = "B. Back"
    QUIT_OPTION = "Q. Quit CVXlab"
    SELECT_ACTION = "\nSelect action ({alternatives}): "
    REQUIRED_VALUE = "A value is required."
    INVALID_VALUE = "Invalid value: {error}"
    INVALID_CHOICE = "Invalid value. Available choices: {choices}"
    INVALID_SELECTION = "\nERROR. Valid selections: {alternatives}.\n"
    INVALID_CONFIGURATION = "Invalid GUI configuration key(s): {names}."
    USE_EXISTING_DATA_CONFIGURATION = (
        "'use_existing_data' is selected through the Model session menu: "
        "choose 'Create new Model instance' for False or "
        "'Open existing Model environment' for True."
    )
    INVALID_ACTION_NAMES = "Invalid GUI action name(s): {names}."
    INVALID_ACTION_SETTINGS = "Invalid GUI action setting(s): {settings}."
    INVALID_ACTION_SETTINGS_TYPE = (
        "'action_settings' must map action names to settings dictionaries."
    )
    UNKNOWN_ACTION_TARGET = "Unknown GUI action target: {target}."
    BOOLEAN_REQUIRED = "Enter 'true' or 'false'."
    EXIT_MESSAGE = "\nExiting CVXlab. Goodbye!\n"
    INTERRUPTED_MESSAGE = "\nOperation interrupted by user.\n"
    FAILED_MESSAGE = "\nOperation failed: {error}\n"
    UNEXPECTED_ERROR = "\nUnexpected error: {error}\n"
    NO_ACTIVE_MODEL = "No active Model instance. Create or open a model first."
    LOG_START = f"{'CVXLAB logs below ' :─<49}"
    LOG_END = f"{'CVXLAB logs above ' :─<49}"

    MODEL_PARAMETERS = {
        'model_dir_name': Parameter("Model directory name"),
        'main_dir_path': Parameter("Main directory path"),
        'model_settings_from': Parameter(
            "Model settings format", choices=('yml', 'xlsx')),
        'detailed_validation': Parameter(
            "Detailed validation", parser='bool'),
        'multiple_input_files': Parameter(
            "Use one input file per data table", parser='bool'),
        'input_data_files_type': Parameter(
            "Input data file type", choices=('xlsx', 'csv')),
        'log_level': Parameter(
            "Log level", choices=('debug', 'info', 'warning', 'error')),
        'log_format': Parameter(
            "Log format", choices=('standard', 'detailed')),
    }

    MENU = (
        Action(
            'model_session',
            "Model session",
            children=(
                Action(
                    'create_model_instance',
                    "Create new Model instance",
                    target='model_constructor',
                    fixed_arguments={'use_existing_data': False},
                    assign_model=True,
                ),
                Action(
                    'open_model_environment',
                    "Open existing Model environment",
                    target='model_constructor',
                    fixed_arguments={'use_existing_data': True},
                    assign_model=True,
                ),
                Action(
                    'save_model_instance',
                    "Save active Model instance",
                    target='model_instance',
                    arguments={
                        'file_name': Parameter(
                            "Model instance file name",
                            default_from='instance_file_name'),
                    },
                    fixed_arguments={'action': 'save'},
                    require_model=True,
                ),
                Action(
                    'load_model_instance',
                    "Load saved Model instance",
                    target='model_instance',
                    arguments={
                        'file_name': Parameter(
                            "Model instance file name",
                            default_from='instance_file_name'),
                        'source_dir_path': Parameter(
                            "Model instance directory",
                            default_from='main_dir_path'),
                    },
                    fixed_arguments={'action': 'load'},
                    assign_model=True,
                ),
            ),
        ),
        Action(
            'model_operations',
            "Model operations",
            children=(
                Action(
                    'initialize_model_environment',
                    "Initialize model environment",
                ),
                Action(
                    'generate_input_data_files',
                    "Generate input data files",
                    arguments={
                        'table_key_list': Parameter(
                            "Data table keys", parser='literal',
                            model_attribute='data_tables'),
                        'values_cleanup': Parameter(
                            "Clear values when exporting", parser='bool'),
                        'force_overwrite': Parameter(
                            "Overwrite existing files or sheets", parser='bool'),
                    },
                ),
                Action(
                    'refresh_database_and_initialize_problem',
                    "Refresh database and initialize problem",
                    arguments={
                        'table_key_list': Parameter(
                            "Data table keys", parser='literal',
                            model_attribute='data_tables'),
                        'force_overwrite': Parameter(
                            "Overwrite existing data and problems", parser='bool'),
                    },
                ),
                Action(
                    'run_model',
                    "Run model",
                    arguments={
                        'solution_mode': Parameter(
                            "Solution mode",
                            choices=('parallel', 'sequential', 'integrated')),
                        'force_overwrite': Parameter(
                            "Overwrite existing solutions", parser='bool'),
                        'scenarios_idx': Parameter(
                            "Scenario index or list of indices", parser='literal'),
                        'solver': Parameter(
                            "Solver name or per-problem dictionary",
                            parser='string_or_literal'),
                        'solver_verbose': Parameter(
                            "Solver verbosity (boolean or dictionary)",
                            parser='bool_or_literal'),
                        'solver_settings': Parameter(
                            "Solver settings dictionary", parser='literal'),
                        'sequential_solution_chain': Parameter(
                            "Sequential problem-key chain", parser='literal',
                            when_parameter='solution_mode',
                            when_values=('sequential',)),
                        'convergence_monitoring': Parameter(
                            "Enable convergence monitoring", parser='bool',
                            when_parameter='solution_mode',
                            when_values=('integrated',)),
                        'convergence_norm': Parameter(
                            "Convergence norm",
                            choices=(
                                'max_relative', 'max_absolute',
                                'l1', 'l2', 'linf',
                            ),
                            when_parameter='solution_mode',
                            when_values=('integrated',)),
                        'convergence_tables_to_check': Parameter(
                            "Tables to check", parser='string_or_literal',
                            when_parameter='solution_mode',
                            when_values=('integrated',)),
                        'convergence_tables_to_skip': Parameter(
                            "Tables to skip", parser='literal',
                            when_parameter='solution_mode',
                            when_values=('integrated',)),
                        'relative_tolerance': Parameter(
                            "Relative tolerance", parser='float',
                            when_parameter='solution_mode',
                            when_values=('integrated',)),
                        'maximum_iterations': Parameter(
                            "Maximum iterations", parser='int',
                            when_parameter='solution_mode',
                            when_values=('integrated',)),
                        'keep_previous_iteration_db': Parameter(
                            "Keep previous-iteration database", parser='bool',
                            when_parameter='solution_mode',
                            when_values=('integrated',)),
                    },
                ),
                Action(
                    'load_results_to_database',
                    "Load results to database",
                    arguments={
                        'scenarios_idx': Parameter(
                            "Scenario index or list of indices", parser='literal'),
                        'force_overwrite': Parameter(
                            "Overwrite existing results", parser='bool'),
                        'suppress_warnings': Parameter(
                            "Suppress export warnings", parser='bool'),
                    },
                ),
            ),
        ),
        Action(
            'model_maintenance',
            "Model maintenance",
            children=(
                Action(
                    'reinitialize_sqlite_database',
                    "Reinitialize SQLite database",
                    arguments={
                        'force_overwrite': Parameter(
                            "Overwrite existing database data", parser='bool'),
                    },
                ),
                Action(
                    'update_sets_tables',
                    "Update set tables",
                    arguments={
                        'set_keys_list': Parameter(
                            "Set keys", parser='literal',
                            model_attribute='sets'),
                        'update_mode': Parameter(
                            "Update mode",
                            choices=('all', 'filters', 'aggregations')),
                    },
                ),
                Action(
                    'check_model_results',
                    "Check model results",
                    arguments={
                        'other_db_dir_path': Parameter(
                            "Reference database directory"),
                        'other_db_name': Parameter(
                            "Reference database file name"),
                        'numerical_tolerance': Parameter(
                            "Numerical tolerance", parser='float'),
                    },
                ),
            ),
        ),
        Action(
            'inspect_model',
            "Inspect model",
            children=(
                Action(
                    'set',
                    "Inspect set data",
                    arguments={
                        'name': Parameter(
                            "Set name", model_attribute='sets'),
                    },
                    print_result=True,
                ),
                Action(
                    'variable',
                    "Inspect variable data",
                    arguments={
                        'name': Parameter(
                            "Variable name", model_attribute='variables'),
                        'scenario_key': Parameter(
                            "Scenario key", parser='int'),
                        'intra_problem_key': Parameter(
                            "Intra-problem key", parser='int'),
                        'if_hybrid_var': Parameter(
                            "Hybrid variable type",
                            choices=('endogenous', 'exogenous')),
                    },
                    print_result=True,
                ),
                Action(
                    'show_model_summary',
                    "Show active Model summary",
                ),
            ),
        ),
        Action(
            'utilities',
            "Utilities",
            children=(
                Action(
                    'create_model_dir',
                    "Create model directory",
                    target='package',
                    model_arguments=('model_dir_name', 'main_dir_path'),
                    arguments={
                        'force_overwrite': Parameter(
                            "Overwrite existing model directory", parser='bool'),
                        'settings_file_type': Parameter(
                            "Template settings format", choices=('yml', 'xlsx'),
                            default_from='settings_file_type'),
                        'include_user_defined_templates': Parameter(
                            "Include user-defined templates", parser='bool'),
                    },
                ),
                Action(
                    'transfer_setup_info_xlsx',
                    "Transfer setup information from Excel",
                    target='package',
                    arguments={
                        'source_file_name': Parameter(
                            "Source Excel file name"),
                        'source_dir_path': Parameter(
                            "Source directory", default_from='main_dir_path'),
                        'destination_dir_path': Parameter(
                            "Destination model directory",
                            default_from='model_dir_path'),
                        'update': Parameter(
                            "Information to transfer",
                            choices=('settings', 'sets', 'all')),
                    },
                ),
                Action(
                    'copy_user_defined_templates',
                    "Copy user-defined templates",
                    target='package',
                    arguments={
                        'path_destination': Parameter(
                            "Destination directory",
                            default_from='model_dir_path'),
                    },
                ),
                Action(
                    'installed_solvers',
                    "Show installed solvers",
                    target='package',
                    print_result=True,
                ),
            ),
        ),
    )
