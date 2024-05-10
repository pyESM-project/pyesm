import pytest
import tests.tests_settings as settings

from esm import Model

log_level = settings.log_level
unit_models_dir_path = settings.unit_models_dir_path
default_models_dir_path = settings.default_models_dir_path
unit_models = settings.unit_models
default_models = settings.default_models

params_unit_cases = [
    (name, unit_models_dir_path, log_level)
    for name in unit_models
]
params_dft_cases = [
    (name, default_models_dir_path, log_level)
    for name in default_models
]

ids_unit_cases = ["unit_" + name for name in unit_models]
ids_dft_cases = ["default_" + name for name in default_models]

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
