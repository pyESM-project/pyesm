from pathlib import Path
from typing import Dict
import pytest
import yaml

from esm import Model

root_path = Path(__file__).parents[1]
tests_settings = root_path / 'settings.yml'

if not tests_settings.exists():
    raise FileNotFoundError(
        f"Expected settings file does not exist: '{tests_settings}'")

with open(tests_settings, 'r') as file:
    settings = yaml.safe_load(file)

log_level = settings['log_level']

units_dir_path = root_path / settings['paths']['units']
models_dir_path = root_path / settings['paths']['models']

unit_models = settings['fixtures']['units']
default_models = settings['fixtures']['models']

test_methods = settings['test_methods']


def create_test_function(
        models: Dict,
        models_dir_path: Path | str,
        methods: Dict
):
    @pytest.mark.parametrize("model_name", models)
    def test_model(model_name):
        model = Model(
            model_dir_name=model_name,
            main_dir_path=models_dir_path,
            log_level=log_level,
            use_existing_data=True,
        )

        for method, kwargs in methods.items():
            try:
                getattr(model, method)(**kwargs)
            except Exception as e:
                pytest.fail(
                    f"Method '{method}' failed for "
                    f"'{model.settings['model_name']}': {str(e)}"
                )
    return test_model


test_units = create_test_function(
    models=unit_models,
    models_dir_path=units_dir_path,
    methods=test_methods,
)

test_models = create_test_function(
    models=default_models,
    models_dir_path=models_dir_path,
    methods=test_methods,
)
