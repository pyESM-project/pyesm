import cvxlab

model = cvxlab.Model(
    log_level='debug',
    model_settings_from='yml',  # or 'xlsx'
    use_existing_data=True,
    multiple_input_files=False,
    input_data_files_type="xlsx",  # or "csv"
    detailed_validation=True,
)

# model.initialize_model_environment()

# model.refresh_database_and_initialize_problem()

# model.reinitialize_sqlite_database(force_overwrite=True)

# model.run_model(
#     solution_mode='sequential',
#     sequential_solution_chain=['process_1', 'process_2', 'process_3'],
#     # scenarios_idx=[2, 1, 0],
#     # solver={'process_1': 'CLARABEL', 'process_3': 'SCIPY'},
#     # solver_verbose=True,
# )

# model.load_results_to_database(
#     # scenarios_idx=[2, 1, 0],
# )
