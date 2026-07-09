"""Unit tests for Core._define_solution_strategy.

These tests exercise literal and legacy-boolean handling of the
``solution_mode`` parameter, validation of solution chains, and error
conditions when insufficient sub-problems are available.
"""
from types import SimpleNamespace
from pathlib import Path

import pandas as pd
import pytest

from cvxlab.backend.core import Core
from cvxlab.defaults import Defaults
from cvxlab.log_exc import exceptions as exc


def _build_stub_core(problem_keys: list[str], scenarios: int = 2) -> Core:
    core = Core.__new__(Core)
    # minimal logger with required methods used by the helper
    core.logger = SimpleNamespace(error=lambda *a, **k: None,
                                  warning=lambda *a, **k: None)
    core.problem = SimpleNamespace(
        number_of_sub_problems=len(problem_keys),
        problems_keys=problem_keys,
    )
    core.index = SimpleNamespace(
        scenarios_info=pd.DataFrame(index=list(range(scenarios)))
    )
    return core


def test_define_solution_strategy_accepts_sequential_literal():
    core = _build_stub_core(['p1', 'p2'], scenarios=3)

    strategy = core._define_and_validate_run_settings(
        solution_mode='sequential',
        solution_chain=['p1', 'p2'],
        solver=None,
        solver_verbose=False,
        solver_settings=None,
        solver_kwargs={},
    )

    assert strategy['solution_mode'] == 'sequential'
    assert strategy['solution_chain'] == ['p1', 'p2']
    assert strategy['problem_count'] == '2'
    assert strategy['problem_scenarios'] == 3


def test_define_solution_strategy_maps_boolean_true_to_integrated():
    core = _build_stub_core(['p1', 'p2'], scenarios=1)

    strategy = core._define_and_validate_run_settings(
        solution_mode=True,  # legacy boolean
        solution_chain=None,
        solver=None,
        solver_verbose=False,
        solver_settings=None,
        solver_kwargs={},
    )

    assert strategy['solution_mode'] == 'integrated'
    assert strategy['solution_chain'] is None


def test_define_solution_strategy_rejects_invalid_mode():
    core = _build_stub_core(['p1', 'p2'])

    with pytest.raises(exc.SettingsError):
        core._define_and_validate_run_settings(
            solution_mode='invalid_mode',
            solution_chain=None,
            solver=None,
            solver_verbose=False,
            solver_settings=None,
            solver_kwargs={},
        )


def test_define_solution_strategy_requires_multiple_problems_for_integrated():
    core = _build_stub_core(['only_problem'], scenarios=1)

    with pytest.raises(exc.SettingsError):
        core._define_and_validate_run_settings(
            solution_mode='integrated',
            solution_chain=None,
            solver=None,
            solver_verbose=False,
            solver_settings=None,
            solver_kwargs={},
        )
