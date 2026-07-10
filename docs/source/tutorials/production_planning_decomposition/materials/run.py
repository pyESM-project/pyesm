import cvxlab

model = cvxlab.Model(
    log_level="debug",
    use_existing_data=True,
)

model.run_model(
    solution_mode='integrated',
    # solver='CLARABEL',
    # solver_verbose=True,
)
