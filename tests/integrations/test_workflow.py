from unittest.mock import patch
import pytest

from esm import Model


cases = [
    '1_constants',
    '2_expressions',
]


@pytest.fixture(params=cases, scope='module')
def model_env(request):
    model_dir_name = request.param
    fixtures_dir = 'D:/git_repos/pyesm/tests/fixtures'
    log_level = 'info'

    return {
        'model_dir_name': model_dir_name,
        'main_dir_path': fixtures_dir,
        'log_level': log_level,
    }


@pytest.fixture(scope='module')
def model_instance_existing_data(model_env):
    try:
        model = Model(
            model_dir_name=model_env['model_dir_name'],
            main_dir_path=model_env['main_dir_path'],
            log_level=model_env['log_level'],
            use_existing_data=True,
        )
    except Exception as e:
        pytest.fail(f'An error occurring during model generation: {e}')

    return model


@patch('builtins.input', return_value='y')
def test_update_database_and_problem(model_instance_existing_data):
    try:
        model_instance_existing_data.update_database_and_problem()
    except Exception as e:
        pytest.fail(
            f'An error occurring during database and problem update: {e}')


@patch('builtins.input', return_value='y')
def test_problem_initialization(model_instance_existing_data):
    try:
        model_instance_existing_data.initialize_problems()
    except Exception as e:
        pytest.fail(
            f'An error occurring during problem initialization: {e}')


def test_model_run(model_instance_existing_data):
    try:
        model_instance_existing_data.run_model(verbose=False)
    except Exception as e:
        pytest.fail(f'An error occurring during model run: {e}')


def test_results_export(model_instance_existing_data):
    try:
        model_instance_existing_data.load_results_to_database()
    except Exception as e:
        pytest.fail(
            f'An error occurring during results export to database: {e}')
