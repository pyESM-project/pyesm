.. _numerical-problem-run:


Solution of numerical problem(s)
================================

This step solves the *numerical optimization problem(s)* defined for a *CVXlab 
model*, specifying configuration arguments. It supports both independent and 
integrated (iterative) solution modes. In the latter case, it also provides 
detailed logging and convergence monitoring.


Overview
--------

- Checks solver compatibility and problem definitions.
- Solves all numerical problems, either *independently* or as *integrated problems* 
  (solved with *block Gauss-Seidel* algorithm) if requested, with custom solver 
  settings.
- For integrated problems, supports *convergence monitoring* and custom 
  convergence criteria.
- Logs a summary of the solution status for all problems and scenarios.

API: :py:meth:`~cvxlab.Model.run_model`


Typical Usage
-------------

.. code-block:: python

    import cvxlab

    # Previous steps: 
    # - Create model directory and setup files
    # - Create Model instance
    # - Fill sets data (coordinates)
    # - Initialization of data structures
    # - Fill input data Excel file(s)
    # - Initialization of numerical problem(s) 

    # [CURRENT STEP] Solve the numerical problem(s)
    model.run_model(
            force_overwrite=False,
            integrated_problems=False, # Set True for integrated (iterative) solution
            solver="ECOS", # Or another supported solver
            solver_verbose=False,
            solver_settings={...}, # Optional: additional solver options
            scenario_idx=None, # Optional: specify scenario indices to solve
            # Arguments below only applies if integrated_problems=True
            convergence_monitoring=True, 
            convergence_norm="l2",
            convergence_tables_to_check="all_endogenous",
            convergence_tables_to_skip=None,
            relative_tolerance=None,
            maximum_iterations=None,
            keep_previous_iteration_db=False,
    )


Parameters description
----------------------

.. rubric:: General parameters

.. list-table::
   :header-rows: 1
   :widths: 24 56 20

   * - Parameter
     - Description
     - Default
   * - ``force_overwrite``
     - If ``True``, overwrites existing problem status and variable numerical
       values in the ``Problem`` object.
     - ``False``
   * - ``integrated_problems``
     - If ``True``, solves problems iteratively using a block Gauss-Seidel
       scheme. If ``False``, solves each problem independently.
     - ``False``
   * - ``solver``
     - Solver to use, for example ``"ECOS"`` or ``"SCS"``. If ``None``, the
       default solver from ``Defaults`` is used.
     - ``None``
   * - ``solver_verbose``
     - If ``True``, enables verbose output from the solver.
     - ``False``
   * - ``solver_settings``
     - Dictionary of additional solver options passed as key-value pairs.
     - ``None``
   * - ``scenario_idx``
     - An optional index or list of indices specifying which scenarios to solve. If
       ``None``, all scenarios in the DataFrame will be solved. If an integer
       is provided, it will be treated as a single scenario index.
     - ``None``
   * - ``**kwargs``
     - Additional keyword arguments for solver-specific options.
     - None

The parameters below are only relevant when ``integrated_problems=True``.

.. rubric:: Integrated-solution parameters

.. list-table::
   :header-rows: 1
   :widths: 24 56 20

   * - Parameter
     - Description
     - Default
   * - ``convergence_monitoring``
     - Enables convergence monitoring during integrated solving.
     - ``True``
   * - ``convergence_norm``
     - Norm used for convergence monitoring, for example ``"l2"``.
     - ``"l2"``
   * - ``convergence_tables_to_check``
     - Data tables to check for convergence: ``"all_endogenous"``,
       ``"hybrid_only"``, or a list of table keys.
     - ``"all_endogenous"``
   * - ``convergence_tables_to_skip``
     - List of data table keys to skip during convergence checking.
     - ``None``
   * - ``relative_tolerance``
     - Numerical tolerance for convergence. If provided, it overrides the
       default model-coupling setting.
     - ``None``
   * - ``maximum_iterations``
     - Maximum number of iterations for integrated solving. If provided, it
       overrides the default model-coupling setting.
     - ``None``
   * - ``keep_previous_iteration_db``
     - If ``True``, keeps the database from the previous iteration for
       debugging.
     - ``False``


Workflow
--------

When :py:meth:`~cvxlab.Model.run_model` is called on a Model instance:

- Checks that the selected solver is supported and that numerical problems are defined.
- Applies solver settings and logs solver output if requested.
- After solving, logs a summary of the solution status for each problem and scenario.
- Raises explicit errors if the solver is unsupported, no problems are defined, 
  or integrated solving is requested with only one problem.

The solution process then proceeds as follows based on the value of ``integrated_problems``.

In case of ``integrated_problems=False``, each problem is solved independently.

In case of ``integrated_problems=True`` and in case of coupled sub-problems (e.g., 
for decomposed nonlinear or hybrid systems), the integrated solution mode applies 
a *block Gauss-Seidel* (alternating optimization) algorithm. This approach is 
useful in case of expressions that present multiplication of endogenous variables,
which cannot be solved in a single step as they are non-convex, but can be solved
by defining different sub-problems where variables are selectively defined as 
endogenous or exogenous in order to avoid multiplication of endogenous variables. 
This approach enables the solution of nonlinear models by decomposing them into 
smaller, tractable convex sub-problems, with automatic coordination and convergence 
checking:

- Each sub-problem is formulated as a convex optimization problem by the user, 
  and all are solved in parallel within each iteration. 
- At every iteration, the endogenous variables are updated and exchanged between 
  sub-problems via the shared SQLite database.
- The process begins with an initial independent solve for all sub-problems, 
  using the current exogenous data as a first guess.
- After each iteration, the method computes the change in variable values (using 
  *norms* such as maximum relative/absolute, l1, l2, linf) to monitor convergence. 
  Available norms include: *Maximum relative/absolute changes* (absolute or relative),
  *Manhattan Norm* (l1), *Euclidean Norm* (l2), *Maximum Norm* (linf).
- Iterations continue until the maximum change across all monitored tables falls 
  below the specified tolerance (``relative_tolerance``), or until the maximum 
  number of iterations (``maximum_iterations``) is reached.
- For each scenario, a *backup of the original database* is created before iterations 
  begin, and restored at the end if needed. If ``keep_previous_iteration_db=True``, 
  the database from the previous iteration can be kept for debugging purposes.
- Detailed logging is provided for each iteration, including convergence metrics 
  and solver status.
