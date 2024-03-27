import esm
import pytest


model_dir_name = 'constants_generation'
main_dir_path = 'D:/git_repos/pyesm/tests/tests_integration'

model = esm.Model(
    model_dir_name=model_dir_name,
    main_dir_path=main_dir_path,
    use_existing_data=True,
    log_level='info',
)

model.load_model_coordinates()
model.initialize_blank_database()

model.initialize_problems()
