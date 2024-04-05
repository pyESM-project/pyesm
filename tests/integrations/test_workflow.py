from unittest.mock import patch
import pytest

from esm import Model


cases = [
    '0_constants',
    '0_expressions',
    '0_test_problem',
    '0_test_structure',
    '1_sut_multi_year',
    '2_sut_multi_year_rcot',
    '4_sut_multi_year_rcot_cap_new',
]


@pytest.fixture(params=cases, scope='module')
def model_env(request):
    """
    A fixture that provides environment setup for Model instances based on 
    different test cases. It yields a dictionary containing the model directory
    name, the main directory path, and the log level for each test case defined
    in the 'cases' list.

    Parameters:
        request: The request object for accessing the current test context.

    Yields:
        A dictionary essential Model settings.
    """
    model_dir_name = request.param
    fixtures_dir = 'D:/git_repos/pyesm/default'
    # fixtures_dir = 'D:/git_repos/pyesm/tests/fixtures'
    log_level = 'debug'

    return {
        'model_dir_name': model_dir_name,
        'main_dir_path': fixtures_dir,
        'log_level': log_level,
    }


@pytest.fixture(scope='module')
def model_instance_existing_data(model_env):
    """
    A module-scoped fixture that initializes and returns a Model instance 
    using existing data. It utilizes the 'model_env' fixture to retrieve the 
    necessary environment setup.

    Parameters:
        model_env: The environment setup returned by the 'model_env' fixture.

    Returns:
        An instance of the Model class initialized with the provided 
            environment setup.
    """
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


def test_update_database_and_problem(model_instance_existing_data: Model):
    """
    Tests the 'update_database_and_problem' method of the Model instance.
    Verifies that the method can be called without throwing an exception.

    Parameters:
        model_instance_existing_data: A Model instance initialized with 
            existing data.
    """
    try:
        model_instance_existing_data.update_database_and_problem(
            force_overwrite=True
        )
    except Exception as e:
        pytest.fail(
            f'An error occurring during database and problem update: {e}')


def test_problem_initialization(model_instance_existing_data: Model):
    """
    Tests the problem initialization process of the Model instance.
    Ensures that 'initialize_problems' can be executed without errors.

    Parameters:
        model_instance_existing_data: A Model instance initialized with 
            existing data for testing.
    """
    try:
        model_instance_existing_data.initialize_problems(
            force_overwrite=True
        )
    except Exception as e:
        pytest.fail(
            f'An error occurring during problem initialization: {e}')


def test_model_run(model_instance_existing_data: Model):
    """
    Tests the model run functionality.
    Asserts that calling 'run_model' on the Model instance does not 
    result in errors.
    NOTICE THAT the test only checks for the correct execution of the method,
    but not if the data resulting from model run are as expected.

    Parameters:
        model_instance_existing_data: A Model instance to be tested for the 
            model run process.
    """
    try:
        model_instance_existing_data.run_model(verbose=False)
    except Exception as e:
        pytest.fail(f'An error occurring during model run: {e}')


def test_results_export(model_instance_existing_data: Model):
    """
    Tests the export of results to the database by the Model instance.
    Confirms that 'load_results_to_database' can be executed without 
    encountering errors.

    Parameters:
        model_instance_existing_data: A Model instance from which results 
            are to be exported.
    """
    try:
        model_instance_existing_data.load_results_to_database()
    except Exception as e:
        pytest.fail(
            f'An error occurring during results export to database: {e}')
