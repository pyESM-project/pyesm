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
                pytest.fail(f"Test failed: {model_name}")

    return test_model


log_level = settings['log_level']
test_methods = settings['test_methods']

# testing units
units_dir_path = root_path / settings['paths']['units']
unit_models = settings['fixtures']['units']

test_units = create_test_function(
    models=unit_models,
    models_dir_path=units_dir_path,
    methods=test_methods,
)

# testing models
models_dir_path = root_path / settings['paths']['models']
default_models = settings['fixtures']['models']

test_models = create_test_function(
    models=default_models,
    models_dir_path=models_dir_path,
    methods=test_methods,
)

# testing integrated models
integrated_models_dir_path = root_path / settings['paths']['integrated_models']
integrated_models = settings['fixtures']['integrated_models']
test_methods_integrated = settings['test_methods_integrated']

test_integrated_models = create_test_function(
    models=integrated_models,
    models_dir_path=integrated_models_dir_path,
    methods=test_methods_integrated,
)
