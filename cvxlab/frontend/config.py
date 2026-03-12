"""Session configuration for the guided user interface."""
from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Optional


@dataclass
class SessionConfig:
    """All settings needed for a guided session, collected in one place.

    Attributes mirror the Model constructor and solver arguments so that
    every action can pull what it needs from a single object.
    """
    # paths & naming
    model_dir_name: str = 'model'
    main_dir_path: str = ''
    model_structure_file: str = 'model_structure.xlsx'

    # Model constructor settings
    log_level: Literal['info', 'debug', 'warning', 'error'] = 'info'
    model_settings_from: Literal['yml', 'xlsx'] = 'xlsx'
    multiple_input_files: bool = True
    detailed_validation: bool = True
    template_file_type: Literal['yml', 'xlsx'] = 'xlsx'

    # solver / run settings
    solver: Optional[str] = None
    solver_verbose: bool = False
    solver_settings: Dict[str, Any] = field(default_factory=dict)
    integrated_problems: bool = False
    convergence_monitoring: bool = True
    convergence_norm: str = 'l2'
    convergence_tables: str = 'all_endogenous'
    relative_tolerance: Optional[float] = None
    maximum_iterations: Optional[int] = None
    keep_previous_iteration_db: bool = False

    @property
    def solver_args(self) -> Dict[str, Any]:
        """Build the kwargs dict to pass to ``Model.run_model()``."""
        args: Dict[str, Any] = {}
        if self.solver is not None:
            args['solver'] = self.solver
        if self.solver_verbose:
            args['solver_verbose'] = self.solver_verbose
        if self.solver_settings:
            args['solver_settings'] = self.solver_settings
        if self.integrated_problems:
            args['integrated_problems'] = self.integrated_problems
            args['convergence_monitoring'] = self.convergence_monitoring
            args['convergence_norm'] = self.convergence_norm
            args['convergence_tables_to_check'] = self.convergence_tables
            if self.relative_tolerance is not None:
                args['relative_tolerance'] = self.relative_tolerance
            if self.maximum_iterations is not None:
                args['maximum_iterations'] = self.maximum_iterations
            args['keep_previous_iteration_db'] = self.keep_previous_iteration_db
        return args
