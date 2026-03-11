import os
import sys
import cvxlab as cl

from pathlib import Path
from typing import Literal, cast

root_path = os.getcwd()
model_dir_name = 'model'
model_structure = 'model_structure.xlsx'
log_level = 'debug'

modes_mapping = {
    '1': 'init',
    '2': 'run',
    '3': 'refresh',
    '4': 'update-sets',
    '5': 'update-structure',
    '6': 'gen-directory',
}

solver_args = {
    # 'solver': 'GUROBI',
    # 'solver_verbose': True,
    # 'solver_settings': {'DualReductions': 0, 'reoptimize': True},
    # 'integrated_problems': True,
    # 'convergence_monitoring': True,
    # 'convergence_tables': 'all_endogenous',
    # 'convergence_norm': 'l2',
    # 'relative_tolerance': 0.1,
    # 'maximum_iterations': 5,
    # 'keep_previous_iteration_db': False,
}

os.system('cls' if os.name == 'nt' else 'clear')
print(
    "\n-------------------------------------------------"
    "\n          CVXlab Guided User Interface           "
    "\n-------------------------------------------------\n"
)

def select_operational_mode() -> str:
    print(
        "Operational modes: (type 'exit' or enter to quit)\n"
        "\n1. Initialize model and generate data structures."
        "\n2. Run model based on existing data structures."
        "\n3. Refresh exogenous data and run model."
        "\n4. Refresh and update sets in database."
        "\n5. Update model structure from Excel file (no model run)."
        "\n6. Generate model directory structure and template files."
           
    )
    mode_input = input(
        "\nSelect operational mode (Enter values between 1 " \
        f"and {len(modes_mapping)}): "
    ).strip()

    if mode_input.lower() == 'exit' or mode_input == '':
        print("\nExiting CVXlab. Goodbye!\n")
        sys.exit(0)

    return mode_input


while True:

    mode_input = select_operational_mode()

    if str(mode_input) not in modes_mapping.keys():
        print(f"\nERROR. Valid selections: 1 to {len(modes_mapping)}.\n")
        continue

    mode = modes_mapping[mode_input]

    if mode == 'init':
        model = cl.Model(
            model_dir_name=model_dir_name,
            main_dir_path=root_path,
            log_level=log_level,
            model_settings_from='xlsx',
            multiple_input_files=True,
            use_existing_data=False,
            detailed_validation=True,
        )

        move_forward = input(
            "\nRefresh sets from Excel before initialization? ([y]/n): "
        ).strip().lower()

        if move_forward != 'n':
            cl.transfer_setup_info_xlsx(
                source_file_name=model_structure,
                source_dir_path=root_path,
                destination_dir_path=Path(root_path, model_dir_name),
                update='sets',
            )

        model.load_model_coordinates()
        model.initialize_blank_data_structure()

    elif mode == 'run':
        
        if not model:
            model = cl.Model(
                model_dir_name=model_dir_name,
                main_dir_path=root_path,
                log_level='debug',
                model_settings_from='xlsx',
                multiple_input_files=True,
                use_existing_data=True,
                detailed_validation=True,
            )

        model.run_model(**solver_args)
        model.load_results_to_database()

    elif mode == 'refresh':

        if not model:
            model = cl.Model(
                model_dir_name=model_dir_name,
                main_dir_path=root_path,
                log_level='debug',
                model_settings_from='xlsx',
                multiple_input_files=True,
                use_existing_data=False,
                detailed_validation=True,
            )

        model.load_model_coordinates()
        model.load_exogenous_data_to_sqlite_database(force_overwrite=True)
        model.initialize_problems()
        model.run_model()
        model.load_results_to_database()

    elif mode == 'update-sets':
        cl.transfer_setup_info_xlsx(
            source_file_name=model_structure,
            source_dir_path=root_path,
            destination_dir_path=Path(root_path, model_dir_name),
            update='sets',
        )
        if not model:
            model = cl.Model(
                model_dir_name=model_dir_name,
                main_dir_path=root_path,
                log_level='debug',
                model_settings_from='xlsx',
                multiple_input_files=True,
                use_existing_data=False,
                detailed_validation=True,
            )

        model.load_model_coordinates()
        model.update_sets_tables()

    elif mode == 'update-structure':
        update = input(
            "\nObjects to update (1: 'settings', 2: 'sets', " \
            "3: 'all', default 'all'): "
        ).strip()

        if update not in [str(n) for n in range(1, 4)]:
            print("\nInvalid selection. Defaulting to 'all'.\n")
            update = 'all'
        else:
            update = {'1': 'settings', '2': 'sets', '3': 'all'}[update]
        
        cl.transfer_setup_info_xlsx(
            source_file_name=model_structure,
            source_dir_path=root_path,
            destination_dir_path=Path(root_path, model_dir_name),
            update=cast(Literal['settings', 'sets', 'all'], update),
        )

    elif mode == 'gen-directory':
        cl.create_model_dir(
            main_dir_path=root_path,
            model_dir_name=model_dir_name,
            template_file_type='xlsx',
        )

    print("\n-------------------------------------------------")