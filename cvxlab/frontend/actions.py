"""Handler functions for each menu action.

Each handler has the signature ``(config, state) -> None`` where
*config* is a ``SessionConfig`` and *state* is a ``ModelState``.
"""
from pathlib import Path
from typing import Literal, cast

import cvxlab as cl

from cvxlab.frontend.config import SessionConfig
from cvxlab.frontend.state import ModelState


# ------------------------------------------------------------------
# 1. Initialize model and generate data structures
# ------------------------------------------------------------------
def init_model(config: SessionConfig, state: ModelState) -> None:
    state.model = cl.Model(
        model_dir_name=config.model_dir_name,
        main_dir_path=config.main_dir_path,
        log_level=config.log_level,
        model_settings_from=config.model_settings_from,
        multiple_input_files=config.multiple_input_files,
        use_existing_data=False,
        detailed_validation=config.detailed_validation,
    )

    answer = input(
        "\nRefresh sets from Excel before initialization? ([y]/n): "
    ).strip().lower()

    if answer != 'n':
        cl.transfer_setup_info_xlsx(
            source_file_name=config.model_structure_file,
            source_dir_path=config.main_dir_path,
            destination_dir_path=Path(
                config.main_dir_path, config.model_dir_name),
            update='sets',
        )

    state.model.load_model_coordinates()
    state.model.initialize_blank_data_structure()


# ------------------------------------------------------------------
# 2. Run model based on existing data structures
# ------------------------------------------------------------------
def run_model(config: SessionConfig, state: ModelState) -> None:
    model = state.ensure_model(config, use_existing_data=True)
    model.run_model(**config.solver_args)
    model.load_results_to_database()


# ------------------------------------------------------------------
# 3. Refresh exogenous data and run model
# ------------------------------------------------------------------
def refresh_and_run(config: SessionConfig, state: ModelState) -> None:
    model = state.ensure_model(config, use_existing_data=False)
    model.load_model_coordinates()
    model.load_exogenous_data_to_sqlite_database(force_overwrite=True)
    model.initialize_problems()
    model.run_model(**config.solver_args)
    model.load_results_to_database()


# ------------------------------------------------------------------
# 4. Refresh and update sets in database
# ------------------------------------------------------------------
def update_sets(config: SessionConfig, state: ModelState) -> None:
    cl.transfer_setup_info_xlsx(
        source_file_name=config.model_structure_file,
        source_dir_path=config.main_dir_path,
        destination_dir_path=Path(
            config.main_dir_path, config.model_dir_name),
        update='sets',
    )
    model = state.ensure_model(config, use_existing_data=False)
    model.load_model_coordinates()
    model.update_sets_tables()


# ------------------------------------------------------------------
# 5. Update model structure from Excel file (sub-menu)
# ------------------------------------------------------------------
def update_structure(config: SessionConfig, state: ModelState) -> None:
    choice = input(
        "\nObjects to update (1: 'settings', 2: 'sets', "
        "3: 'all', default 'all'): "
    ).strip()

    mapping = {'1': 'settings', '2': 'sets', '3': 'all'}
    if choice not in mapping:
        print("\nInvalid selection. Defaulting to 'all'.\n")
        update = 'all'
    else:
        update = mapping[choice]

    cl.transfer_setup_info_xlsx(
        source_file_name=config.model_structure_file,
        source_dir_path=config.main_dir_path,
        destination_dir_path=Path(
            config.main_dir_path, config.model_dir_name),
        update=cast(Literal['settings', 'sets', 'all'], update),
    )


# ------------------------------------------------------------------
# 6. Generate model directory structure and template files
# ------------------------------------------------------------------
def gen_directory(config: SessionConfig, state: ModelState) -> None:
    cl.create_model_dir(
        main_dir_path=config.main_dir_path,
        model_dir_name=config.model_dir_name,
        template_file_type=config.template_file_type,
    )
