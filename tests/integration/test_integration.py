"""Integration tests for different model types.

This module contains integrations tests for different types of models, defined as
fixtures in the 'fixtures' directory.
The tests are parameterized based on settings loaded from a YAML file. The 
settings specify the log level, the test methods to call on each model, and 
the paths and names of the models to test.
"""
import os
import shutil
import atexit

from pathlib import Path

from cvxlab.defaults import Defaults
from tests.integration.conftest import (
    load_test_settings,
    sanitize_fixture_name,
    create_model_fixture,
    create_test_function,
)


# Defaults and paths
tests_settings_file = 'tests_settings.yml'

# Previously tests used a `fixtures` folder. Now scan the tutorials
# for model folders at `docs/source/tutorials/*/materials/model`.
db_name = Defaults.ConfigFiles.SQLITE_DATABASE_FILE
root_path = Path(__file__).parent
test_settings_path = Path(root_path, tests_settings_file)

# Path to tutorials directory (repo root / docs / source / tutorials)
tutorials_root = Path(root_path.parent.parent, 'docs', 'source', 'tutorials')

# Create an isolated working directory for test runs
work_dir_path = root_path / ".work"
if work_dir_path.exists():
    shutil.rmtree(work_dir_path, ignore_errors=True)
work_dir_path.mkdir(parents=True, exist_ok=True)


@atexit.register
def _cleanup_work_dir():
    shutil.rmtree(work_dir_path, ignore_errors=True)


# Load test settings and list of models
settings = load_test_settings(test_settings_path)

# Build a list of (model_name, model_src_path) pairs from tutorials.
models_info = []
if tutorials_root.exists():
    for tutorial_dir in sorted(tutorials_root.iterdir()):
        model_src = tutorial_dir / 'materials' / 'model'
        if model_src.exists() and model_src.is_dir():
            models_info.append((tutorial_dir.name, model_src))

# Fallback: if no tutorials found, fall back to legacy `fixtures` folder
if not models_info:
    fixtures_dir_path = Path(root_path, 'fixtures')
    if fixtures_dir_path.exists():
        for name in sorted(os.listdir(fixtures_dir_path)):
            models_info.append((name, fixtures_dir_path / name))

# Generating testing functions and fixtures dynamically
for model_name, model_src_path in models_info:

    # Prepare a per-model working copy of the model folder
    model_work_path = work_dir_path / model_name
    shutil.copytree(model_src_path, model_work_path)

    # Create a valid test function name
    sanitized_model_name = sanitize_fixture_name(model_name)
    test_func_name = f"test_{sanitized_model_name}"
    fixture_name = f"fixture_{sanitized_model_name}"

    # Create and register model fixture (pointing to the working dir)
    model_fixture = create_model_fixture(
        model_name=model_name,
        models_dir_path=work_dir_path,
        log_level=settings['log_level'],
    )
    model_fixture.__name__ = fixture_name
    globals()[fixture_name] = model_fixture

    # Create the test functions for this specific model
    _test_func = create_test_function(
        model_name=model_name,
        test_func_name=test_func_name,
        fixture_name=fixture_name,
        methods=settings['methods'],
        overrides=settings.get('model_overrides', {}),
    )

    # Add the test function to the module's global namespace
    globals()[test_func_name] = _test_func

# Cleanup temporary variable
del _test_func
