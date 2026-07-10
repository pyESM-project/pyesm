"""Module defining RunSettings: validated container for model run configuration.

All normalization and validation logic for solver/scenario/mode arguments is
consolidated here into a single ``RunSettings`` class whose ``__init__`` accepts
raw user inputs, validates them, and stores only normalized values.
"""
from __future__ import annotations

from typing import Any, List, Optional

from cvxlab.defaults import Defaults
from cvxlab.log_exc import exceptions as exc
from cvxlab.log_exc.logger import Logger


class RunSettings:
    """Validated, normalized settings for a single model run.

    Constructed directly from raw user inputs together with context primitives
    extracted from the model (``problems_keys``, ``number_of_sub_problems``,
    ``all_scenarios_idx``).  The constructor validates every argument and stores
    only normalized values, so all attributes are guaranteed to be clean:

    - ``scenario_idx`` is always a ``list[int]``.
    - ``sequential_solution_chain`` is a ``list`` when *solution_mode* is
      'sequential', otherwise ``None``.
    - ``solver_settings`` is always a per-problem mapping
      ``{problem_key: {setting: value, ...}}``.

    Context arguments (``problems_keys``, ``number_of_sub_problems``,
    ``all_scenarios_idx``) carry the model state needed for validation but are
    not stored as attributes — they are used only during construction.

    Raises:
        exc.SettingsError: If any validation rule is violated.
    """

    def __init__(
        self,
        *,
        logger: Logger,
        # Context: primitive values from Problem/Index (not the objects)
        problems_keys: List[Optional[str]],
        number_of_sub_problems: int,
        all_scenarios_idx: List[int],
        # User-provided arguments (mirror Model.run_model signature)
        solution_mode: str,
        scenario_idx: Optional[List[int] | int],
        solver: Optional[str | dict[str, str]],
        solver_verbose: bool | dict[str, bool],
        solver_settings: Optional[dict[str, Any] | dict[str, dict[str, Any]]],
        sequential_solution_chain: Optional[List[str | int]],
        convergence_monitoring: bool,
        convergence_norm: Defaults.LiteralTypes.NormType,
        convergence_tables_to_check: Defaults.LiteralTypes.ConvergenceTables | List[str],
        convergence_tables_to_skip: Optional[List[str]],
        relative_tolerance: Optional[float],
        maximum_iterations: Optional[int],
        keep_previous_iteration_db: bool,
    ) -> None:
        """Validate and normalize all run arguments.

        Args:
            problems_keys: Sub-problem keys from ``Problem.problems_keys``.
            number_of_sub_problems: Total number of defined sub-problems.
            all_scenarios_idx: All valid scenario indices from the index.
            solution_mode: Requested solution mode ('parallel', 'sequential',
                'integrated').
            scenario_idx: Scenarios to solve. ``None`` → all scenarios.
            solver: Solver name or per-problem dict of solver names.
            solver_verbose: Verbosity flag or per-problem dict of flags.
            solver_settings: Common or per-problem solver keyword settings.
            sequential_solution_chain: Ordered list of problem keys for
                'sequential' mode.
            convergence_monitoring: Enable convergence logging (integrated mode).
            convergence_norm: Norm type used for convergence checking.
            convergence_tables_to_check: Tables to monitor for convergence.
            convergence_tables_to_skip: Tables to exclude from convergence check.
            relative_tolerance: Per-table relative convergence tolerance.
            maximum_iterations: Maximum iterations for integrated solving.
            keep_previous_iteration_db: Retain previous-iteration DB (debug).
            logger: Optional logger for per-error messages before raising.

        Raises:
            exc.SettingsError: If any validation rule is violated.
        """

        self.logger = logger.get_child(__name__)
        self.logger.debug(
            "Define and validate model run settings and solution strategy.")

        err_msg: list[str] = []

        if number_of_sub_problems == 0:
            err_msg.append(
                "Numerical problem/s not found. Initialize problem/s first."
            )

        self._validate_solution_mode(
            solution_mode, number_of_sub_problems, err_msg)

        normalized_scenario_idx = self._normalize_scenario_idx(
            scenario_idx, all_scenarios_idx, err_msg
        )

        normalized_chain = self._normalize_sequential_chain(
            solution_mode, sequential_solution_chain, problems_keys, err_msg
        )

        normalized_solver_settings = self._normalize_solver_settings(
            solver=solver,
            solver_verbose=solver_verbose,
            solver_settings=solver_settings,
            problems_keys=problems_keys,
            number_of_sub_problems=number_of_sub_problems,
            err_msg=err_msg,
        )

        if err_msg:
            for msg in err_msg:
                logger.error(f"Run settings validation | {msg}")
            raise exc.SettingsError("Run settings validation | Failed.")

        self.solution_mode = solution_mode
        self.scenario_idx = normalized_scenario_idx
        self.sequential_solution_chain = normalized_chain
        self.convergence_monitoring = convergence_monitoring
        self.convergence_norm = convergence_norm
        self.convergence_tables_to_check = convergence_tables_to_check
        self.convergence_tables_to_skip = convergence_tables_to_skip
        self.relative_tolerance = relative_tolerance
        self.maximum_iterations = maximum_iterations
        self.keep_previous_iteration_db = keep_previous_iteration_db
        self.solver_settings = normalized_solver_settings

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            f"solution_mode='{self.solution_mode}', "
            f"scenarios={self.scenario_idx}, "
            f"problems={list(self.solver_settings)})"
        )

    @staticmethod
    def _validate_solution_mode(
        solution_mode: str,
        number_of_sub_problems: int,
        err_msg: list[str],
    ) -> None:
        """Append errors if *solution_mode* is invalid or incompatible."""
        available = Defaults.LiteralTypes.SolutionMode.__args__
        if solution_mode not in available:
            err_msg.append(
                f"Solution mode '{solution_mode}' not allowed. "
                f"Available modes: {available}"
            )
            return  # no point running mode-specific checks after this
        if number_of_sub_problems < 2 and solution_mode in ('sequential', 'integrated'):
            err_msg.append(
                f"Solution mode '{solution_mode}' requires multiple sub-problems. "
                f"Current sub-problems: {number_of_sub_problems}."
            )

    @staticmethod
    def _normalize_scenario_idx(
        scenario_idx: Optional[List[int] | int],
        all_scenarios_idx: List[int],
        err_msg: list[str],
    ) -> List[int]:
        """Return a normalized list of scenario indices.

        Falls back to *all_scenarios_idx* when validation fails so that the
        caller can still collect further errors before raising.
        """
        if scenario_idx is None:
            return list(all_scenarios_idx)

        if not isinstance(scenario_idx, (list, int)):
            err_msg.append(
                f"Invalid type for 'scenario_idx': {type(scenario_idx).__name__}. "
                "Expected: list or int."
            )
            return list(all_scenarios_idx)

        if isinstance(scenario_idx, list) and not all(
                isinstance(idx, int) for idx in scenario_idx):
            err_msg.append(
                "Invalid type in 'scenario_idx' list: all elements must be int."
            )
            return list(all_scenarios_idx)

        normalized: List[int] = (
            [scenario_idx] if isinstance(
                scenario_idx, int) else list(scenario_idx)
        )
        invalid = set(normalized) - set(all_scenarios_idx)
        if invalid:
            err_msg.append(
                f"Invalid scenario indices passed to 'scenario_idx': "
                f"{sorted(invalid)}. Available scenarios: {all_scenarios_idx}"
            )
        return normalized

    @staticmethod
    def _normalize_sequential_chain(
        solution_mode: str,
        sequential_solution_chain: Optional[List[str | int]],
        problems_keys: List[Optional[str]],
        err_msg: list[str],
    ) -> Optional[List[Optional[str]]]:
        """Return a validated, normalized sequential solution chain.

        Returns ``None`` when *solution_mode* is not 'sequential'.
        Defaults to the full *problems_keys* list when the chain is not given.
        """
        if solution_mode != 'sequential':
            if sequential_solution_chain is not None:
                err_msg.append(
                    "Argument 'sequential_solution_chain' is only valid for "
                    "solution mode 'sequential'."
                )
            return None

        if sequential_solution_chain is None:
            return list(problems_keys)

        if not isinstance(sequential_solution_chain, (list, tuple)):
            err_msg.append(
                "'sequential_solution_chain' must be a list of problem keys."
            )
            return None

        chain = list(sequential_solution_chain)
        invalid_keys = set(chain) - set(problems_keys)
        if invalid_keys:
            err_msg.append(
                "Invalid problem keys in 'sequential_solution_chain': "
                f"{invalid_keys}. Available problem keys: {problems_keys}"
            )
        return chain

    @staticmethod
    def _normalize_solver_settings(
        solver: Optional[str | dict[str, str]],
        solver_verbose: bool | dict[str, bool],
        solver_settings: Optional[dict[str, Any] | dict[str, dict[str, Any]]],
        problems_keys: List[Optional[str]],
        number_of_sub_problems: int,
        err_msg: list[str],
    ) -> dict[Optional[str], dict[str, Any]]:
        """Build a complete per-problem solver-settings mapping.

        Each value is a settings dict that starts from CVXPY defaults, then is
        overlaid (in order) with: common/per-problem *solver_settings*, the
        *solver* selection, and the *solver_verbose* flag.

        Returns a dict keyed by every entry in *problems_keys*.
        """
        cvxpy_defaults: dict[str,
                             Any] = Defaults.NumericalSettings.CVXPY_DEFAULT_SETTINGS
        allowed_solvers: list[str] = Defaults.NumericalSettings.ALLOWED_SOLVERS

        # Determine whether solver_settings are common or per-problem
        per_problem_settings: Optional[dict[Optional[str],
                                            dict[str, Any]]] = None
        common_settings: dict[str, Any] = {}

        if solver_settings:
            keys_are_problem_keys = set(
                solver_settings).issubset(set(problems_keys))
            values_are_dicts_or_none = all(
                v is None or isinstance(v, dict)
                for v in solver_settings.values()
            )
            if keys_are_problem_keys and values_are_dicts_or_none:
                if number_of_sub_problems == 1:
                    err_msg.append(
                        "Per-problem 'solver_settings' requires multiple sub-problems."
                    )
                per_problem_settings = {
                    k: dict(v) if v else {} for k, v in solver_settings.items()
                }
            else:
                common_settings = dict(solver_settings)

        # Expand common settings to per-problem map
        if common_settings:
            per_problem_settings = {k: common_settings.copy()
                                    for k in problems_keys}

        # Validate dict keys for solver / solver_verbose
        if isinstance(solver, dict):
            if number_of_sub_problems == 1:
                err_msg.append(
                    "Per-problem 'solver' dict requires multiple sub-problems."
                )
            invalid = set(solver) - set(problems_keys)
            if invalid:
                err_msg.append(
                    f"Invalid problem keys in 'solver' dict: {invalid}. "
                    f"Available problem keys: {problems_keys}"
                )

        if isinstance(solver_verbose, dict):
            if number_of_sub_problems == 1:
                err_msg.append(
                    "Per-problem 'solver_verbose' dict requires multiple sub-problems."
                )
            invalid = set(solver_verbose) - set(problems_keys)
            if invalid:
                err_msg.append(
                    f"Invalid problem keys in 'solver_verbose' dict: {invalid}. "
                    f"Available problem keys: {problems_keys}"
                )

        # Build final per-problem mapping
        normalized: dict[Optional[str], dict[str, Any]] = {}
        for problem_key in problems_keys:
            ps: dict[str, Any] = {**cvxpy_defaults}

            # Overlay per-problem (or expanded-common) settings
            if per_problem_settings is not None:
                ps.update(per_problem_settings.get(problem_key) or {})

            # Overlay explicit solver selection
            if isinstance(solver, dict):
                if problem_key in solver:
                    ps['solver'] = solver[problem_key]
            elif solver is not None:
                ps['solver'] = solver

            # Validate solver name
            selected_solver: str = ps.get('solver', cvxpy_defaults['solver'])
            if selected_solver not in allowed_solvers:
                err_msg.append(
                    f"Problem '{problem_key}' | Solver '{selected_solver}' is not "
                    "supported by the installed CVXPY version. "
                    f"Available solvers: {allowed_solvers}"
                )
            ps['solver'] = selected_solver

            # Verbosity
            if isinstance(solver_verbose, dict):
                ps['verbose'] = bool(solver_verbose.get(problem_key, False))
            else:
                ps['verbose'] = bool(solver_verbose)

            normalized[problem_key] = ps

        return normalized
