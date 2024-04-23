import pytest
from unittest.mock import patch

from esm import Model

log_level = 'info'

unit_cases_dir_path = 'D:/git_repos/pyesm/tests/fixtures'
dft_cases_dir_path = 'D:/git_repos/pyesm/default'

unit_cases = [
    'constants',
    'expressions',
    'test_structure',
    'variables',
]
dft_cases = [
    '1_sut_multi_year',
    '2_sut_multi_year_rcot',
    '3_sut_multi_year_rcot_cap',
]

params_unit_cases = [
    (name, unit_cases_dir_path, log_level)
    for name in unit_cases
]
params_dft_cases = [
    (name, dft_cases_dir_path, log_level)
    for name in dft_cases
]

ids_unit_cases = ["unit_" + name for name in unit_cases]
ids_dft_cases = ["default_" + name for name in dft_cases]

test_methods = {
    'update_database_and_problem': {'force_overwrite': True},
    'initialize_problems': {'force_overwrite': True},
    'run_model': {'force_overwrite': True},
    'load_results_to_database': {},
}


# testing unit cases

@pytest.fixture(scope='module', params=params_unit_cases, ids=ids_unit_cases)
def unit_model_instance(request):
    model_name, path, log_level = request.param
    model = Model(
        model_dir_name=model_name,
        main_dir_path=path,
        log_level=log_level,
        use_existing_data=True,
    )
    return model


@pytest.mark.parametrize('method, kwargs', test_methods.items())
def test_unit_model_methods(
    unit_model_instance: Model,
    method: str,
    kwargs: dict
):
    try:
        getattr(unit_model_instance, method)(**kwargs)
    except Exception as e:
        pytest.fail(
            f"Method '{method}' failed for "
            f"'{unit_model_instance.settings['model_name']}': {str(e)}"
        )


# testing default models

@pytest.fixture(scope='module', params=params_dft_cases, ids=ids_dft_cases)
def default_model_instance(request):
    model_name, path, log_level = request.param
    model = Model(
        model_dir_name=model_name,
        main_dir_path=path,
        log_level=log_level,
        use_existing_data=True,
    )
    return model


@pytest.mark.parametrize('method, kwargs', test_methods.items())
def test_default_model_methods(
    default_model_instance: Model,
    method: str,
    kwargs: dict
):
    try:
        getattr(default_model_instance, method)(**kwargs)
    except Exception as e:
        pytest.fail(
            f"Method '{method}' failed for "
            f"'{default_model_instance.settings['model_name']}': {str(e)}"
        )
