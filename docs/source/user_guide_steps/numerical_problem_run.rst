.. _numerical-problem-run:


Solution of numerical problem(s)
================================

This step solves the *numerical optimization problem(s)* defined for a *CVXlab 
model*, specifying solution modes and solver(s) configuration arguments. 


Overview
--------

- Checks solver compatibility and problem definitions.
- Solves all numerical problems, either as *parallel*, *sequential* or *integrated* 
  numerical problems, with custom solver settings for multiple inter-problem sets 
  cardinality (i.e. for multiple scenarios).
- At the end, logs a summary of the solution status for all problems and scenarios.

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
          solution_mode='integrated',  
          solver="ECOS", 
          solver_verbose=True,
          solver_settings={...}, 
  )


Parameters description
----------------------

General arguments and and solver settings are described below. 

.. list-table::
  :header-rows: 1
  :widths: 20 80

  * - Parameter
    - Description
  * - ``force_overwrite``
    - If ``True``, overwrites existing problem status and variable numerical
      values in the ``Problem`` object without prompting for confirmation. Default 
      to ``False``.
  * - ``solution_mode``
    - Available solution modes: ``parallel`` (default), ``sequential``, ``integrated``.
  * - ``scenarios_idx``
    - optional list of indices specifying which scenarios to solve. Indices must 
      correspond to the values of the :attr:`scenarios` DataFrame (inspect it to 
      identify valid values). If None, all scenarios are solved. If an integer 
      is provided, it will be treated as a single scenario index. If ``None``, 
      all scenarios are solved.
  * - ``solver``
    - Solver to use, for example ``"ECOS"`` or ``"SCS"``. Available solvers can 
      be inspected with the :py:func:`cvxlab.installed_solvers()` function. When 
      multiple numerical problems are defined, a dictionary keyed by problem key 
      can be used to define a different solver per sub-problem. If ``None``, the 
      ``SCIPY`` solver is used by default.
  * - ``solver_verbose``
    - If ``True``, enables verbose output from the solver/s. When multiple 
      sub-problems are available, a dictionary keyed by problem key can be used 
      to define verbosity for each sub-problem. Default to ``False``.
  * - ``solver_settings``
    - Dictionary of additional solver options passed as key-value pairs. When multiple 
      sub-problems are available, a dictionary keyed by problem key can be used 
      to define solver settings for each sub-problem as sub-dictionaries. Default 
      to ``None`` (no additional settings).

.. note::
  In case only specific scenarios are to be solved, the user can run them selectively 
  by specifying the ``scenarios_idx`` argument. This would reduce the solution time in 
  case of large number of scenarios or complex problems.

The parameters below are only relevant in case of ``solution_mode="sequential"``.

.. list-table::
  :header-rows: 1
  :widths: 20 80

  * - Parameter
    - Description
  * - ``sequential_solution_chain``
    - An optional list of problem keys specifying the order in which to solve 
      the problems. Works only when ``solution_mode="sequential"``. If ``None``, 
      problems are solved in the order as they appears in model settings.


The parameters below are only relevant in case of ``solution_mode="integrated"``.

.. list-table::
  :header-rows: 1
  :widths: 20 80

  * - Parameter
    - Description
  * - ``convergence_monitoring``
    - Enables convergence monitoring in a separate prompt window during integrated 
      solving. Default to ``True``.
  * - ``convergence_norm``
    - Numeric Norm type used for convergence monitoring. Default to ``"l2"`` 
      (Euclidean norm).
  * - ``convergence_tables_to_check``
    - Data tables to check for convergence: ``"all_endogenous"``, ``"hybrid_only"``, 
      or a list of table keys. Default to ``"all_endogenous"``.
  * - ``convergence_tables_to_skip``
    - List of data table keys to skip during convergence checking. Default to 
      ``None``.
  * - ``relative_tolerance``
    - Numerical tolerance for verifying maximum relative change between iterations 
      in integrated problems for each data table. If provided, it overrides the
      default model-coupling setting. Default to ``None``.
  * - ``maximum_iterations``
    - Maximum number of iterations for integrated solving. If provided, it
      overrides the default model-coupling setting. Default to ``None``.
  * - ``keep_previous_iteration_db``
    - If ``True``, keeps the database from the previous iteration for
      debugging. Default to ``False``.


Workflow
--------

When :py:meth:`~cvxlab.Model.run_model` is called on a Model instance, the passed 
arguments are validated (e.g. verify that specified solvers are installed, ...). 
Then, the method attempts to solve the numerical problem(s) according to the specified 
solution mode and solver settings. After solving, the method logs a summary of 
the solution status for each problem and scenario.

The solution process proceeds as follows based on the value of ``solution_mode``.

.. rubric:: ``solution_mode="parallel"``

In this case, the method solves all numerical problems as if they were independent,
without any exchange of information between them (even if hybrid Data Tables are
present). This is the default solution mode, and it is useful when problems are
truly independent, or when the user wants to solve them in parallel without any
coordination.

.. rubric:: ``solution_mode="sequential"``

In this case, there must be at least two numerical problems defined in the model, 
and these problems can share hybrid type variables, defined as variables that are 
endogenous in one problem and exogenous in the other. 
This method solve the problems sequentially, based on the ``sequential_solution_chain`` 
argument as a list of problem keys, which defines the order of solution. Each time 
a problem is solved, the method updates the hybrid type Data Tables with the 
endogenous output, then the next problem in the chain is solved using the updated 
data. Because of this approach, the solution routes is performed one scenario at 
a time, and the method iterates over all scenarios.
This method is useful in case some data provided to a problem needs to be 
pre-processed by another problem, or when the solution of a problem is used 
as input for another problem.
Refer to this :ref:`tutorial <tutorial-products-footprints>` for a practical example.

.. rubric:: ``solution_mode="integrated"``

In this case, there must be at least two numerical problems defined in the model, 
and these problems must share at least one hybrid type variable, defined as a variable 
that is endogenous in one problem and exogenous the other. In this case, the integrated 
solution mode applies a *block Gauss-Seidel* (alternating optimization) algorithm, 
working as follows:

- The process begins with an initial independent solve for all sub-problems, 
  using the current exogenous data as a first guess. First, all sub-problems fetch 
  exogenous data from the shared SQLite database. 
- All problems are solved in parallel within each iteration. After all problems 
  are solved, the endogenous variables are updated and exchanged between sub-problems 
  via the shared SQLite database.
- After each iteration, the method computes the Norms changes in Data Tables to 
  monitor convergence. Available Norms include: 
  
.. list-table::
  :header-rows: 1
  :widths: 10 60 30

  * - Norm
    - Description
    - Formulation
  * - ``max_relative``
    - *Maximum relative change* Measures the largest component-wise variation relative 
      to the previous iteration value. It is scale-aware and useful when table values 
      differ by orders of magnitude.
    - .. math:: \max_i \frac{|x_i - y_i|}{|y_i|}
  * - ``max_absolute``
    - *Maximum absolute change* Measures the largest absolute component-wise variation 
      between consecutive iterations, regardless of the magnitude of the reference value.
    - .. math:: \max_i |x_i - y_i|
  * - ``l1``
    - *Manhattan Norm* Aggregates absolute changes across all components. It captures 
      the overall total variation accumulated over the full table/vector.
    - .. math:: \|x - y\|_1 = \sum_i |x_i - y_i|
  * - ``l2``
    - *Euclidean Norm* Computes the geometric magnitude of the change vector. Larger 
      deviations are emphasized because differences are squared before aggregation.
    - .. math:: \|x - y\|_2 = \sqrt{\sum_i (x_i - y_i)^2}
  * - ``linf``
    - *Maximum Norm* Tracks only the single worst component-wise absolute change. 
      It is useful when convergence must be guaranteed for every individual component.
    - .. math:: \|x - y\|_\infty = \max_i |x_i - y_i|

- Iterations continue until the maximum change across all monitored tables falls 
  below the specified tolerance (``relative_tolerance``), or until the maximum 
  number of iterations (``maximum_iterations``) is reached.
- For each scenario, a *backup of the original database* is created before iterations 
  begin, and restored at the end if needed. If ``keep_previous_iteration_db=True``, 
  the database from the previous iteration can be kept for debugging purposes.
- Detailed logging is provided for each iteration, including convergence metrics 
  and solver status.
  
This approach enables the solution of nonlinear models by decomposing them into 
smaller, tractable convex sub-problems, with automatic coordination and convergence 
checking. Specifically, in case of expressions that present multiplication of endogenous 
variables, which cannot be solved in a single step as they are non-convex, but can 
be solved by defining different sub-problems where variables are selectively defined 
as endogenous or exogenous in order to avoid multiplication of endogenous variables. 
Refer to this :ref:`tutorial <tutorial-production-planning-decomposition>` for a 
practical example of this approach.

.. note::
  For all solution modes, the original database is restored at the end of the process. 
  Results are contained in Model instace, and they can be inspected with the method 
  :py:meth:`~cvxlab.Model.variable`. Once the user is satisfied with the results, 
  they can be exported to the database with :ref:`export-model-results`. If the 
  model instance is deleted, the results are lost unless they have been exported to 
  the database.
