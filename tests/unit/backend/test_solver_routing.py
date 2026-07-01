"""Unit tests for solver normalization and routing."""
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call

import pandas as pd
import pytest

from cvxlab.backend.core import Core
from cvxlab.defaults import Defaults
from cvxlab.log_exc import exceptions as exc


def _build_stub_core(problem_keys: list[str]) -> Core:
    core = Core.__new__(Core)
    core.logger = SimpleNamespace(error=lambda *args, **kwargs: None)
    core.problem = SimpleNamespace(
        number_of_sub_problems=len(problem_keys),
        problems_keys=problem_keys,
    )
    core.index = SimpleNamespace(
        scenarios_info=pd.DataFrame(index=[0, 1]),
    )
    return core


def test_define_solution_strategy_supports_per_problem_solver_settings():
    core = _build_stub_core(['problem_a', 'problem_b'])
    available_solvers = Defaults.NumericalSettings.ALLOWED_SOLVERS
    solver_a = available_solvers[0]
    solver_b = available_solvers[-1]

    strategy = core._define_solution_strategy(
        integrated_problems=False,
        solver={
            'problem_a': solver_a,
            'problem_b': solver_b,
        },
        solver_verbose=True,
        solver_settings={
            'problem_a': {'max_iters': 10},
            'problem_b': {'eps_abs': 1e-6},
        },
        solver_kwargs={'warm_start': True},
    )

    assert strategy['selected_solver'] == \
        f"problem_a={solver_a}, problem_b={solver_b}"
    assert strategy['solver_verbose'] is True
    assert strategy['solver_settings']['problem_a']['solver'] == solver_a
    assert strategy['solver_settings']['problem_b']['solver'] == solver_b
    assert strategy['solver_settings']['problem_a']['verbose'] is True
    assert strategy['solver_settings']['problem_b']['verbose'] is True
    assert strategy['solver_settings']['problem_a']['warm_start'] is True
    assert strategy['solver_settings']['problem_b']['warm_start'] is True
    assert strategy['solver_settings']['problem_a']['max_iters'] == 10
    assert strategy['solver_settings']['problem_b']['eps_abs'] == 1e-6


def test_define_solution_strategy_rejects_invalid_problem_keys():
    core = _build_stub_core(['problem_a', 'problem_b'])

    with pytest.raises(exc.SettingsError):
        core._define_solution_strategy(
            integrated_problems=False,
            solver={'problem_x': 'SCIPY'},
            solver_verbose=False,
            solver_settings=None,
            solver_kwargs={},
        )


def test_solve_independent_problems_routes_per_problem_solver_settings():
    core = Core.__new__(Core)
    core.problem = SimpleNamespace(
        numerical_problems={
            'problem_a': 'df_a',
            'problem_b': 'df_b',
        },
        solve_problem_dataframe=Mock(),
    )

    core._solve_independent_problems(
        scenario_idx=[0],
        problem_a={'solver': 'SCIPY', 'verbose': False},
        problem_b={'solver': 'SCIPY', 'verbose': True},
    )

    assert core.problem.solve_problem_dataframe.mock_calls == [
        call(
            problem_dataframe='df_a',
            problem_name='problem_a',
            scenarios_idx=[0],
            solver='SCIPY',
            verbose=False,
        ),
        call(
            problem_dataframe='df_b',
            problem_name='problem_b',
            scenarios_idx=[0],
            solver='SCIPY',
            verbose=True,
        ),
    ]


def test_solve_integrated_problems_routes_per_problem_solver_settings():
    core = Core.__new__(Core)
    scenario_header = Defaults.Labels.SCENARIO_COORDINATES
    status_header = Defaults.Labels.PROBLEM_STATUS

    @contextmanager
    def _convergence_monitor(**kwargs):
        yield {'log': lambda message: None}

    def _solve_problem_dataframe(
        problem_dataframe,
        problem_name,
        scenarios_idx,
        **solver_settings,
    ):
        problem_dataframe.at[scenarios_idx, status_header] = 'infeasible'

    problem_a_df = pd.DataFrame(
        {scenario_header: [[]], status_header: [None]},
        index=[0],
    )
    problem_b_df = pd.DataFrame(
        {scenario_header: [[]], status_header: [None]},
        index=[0],
    )

    core.logger = SimpleNamespace(
        info=lambda *args, **kwargs: None,
        warning=lambda *args, **kwargs: None,
        convergence_monitor=_convergence_monitor,
    )
    core.files = SimpleNamespace(
        copy_file_to_destination=Mock(),
        erase_file=Mock(),
        rename_file=Mock(),
    )
    core.paths = {'model_dir': Path('.')}
    core.index = SimpleNamespace(
        scenarios_info=pd.DataFrame({scenario_header: [[]]}, index=[0]),
    )
    core.problem = SimpleNamespace(
        numerical_problems={
            'problem_a': problem_a_df,
            'problem_b': problem_b_df,
        },
        solve_problem_dataframe=Mock(side_effect=_solve_problem_dataframe),
    )
    core._validate_and_filter_tables_to_check = Mock(return_value=['table_a'])

    core._solve_integrated_problems(
        scenario_idx=0,
        problem_a={'solver': 'SCIPY', 'verbose': False},
        problem_b={'solver': 'SCIPY', 'verbose': True},
    )

    assert core.problem.solve_problem_dataframe.mock_calls == [
        call(
            problem_name='problem_a',
            problem_dataframe=problem_a_df,
            scenarios_idx=0,
            solver='SCIPY',
            verbose=False,
        ),
        call(
            problem_name='problem_b',
            problem_dataframe=problem_b_df,
            scenarios_idx=0,
            solver='SCIPY',
            verbose=True,
        ),
    ]
