.. _export-model-results:


Export endogenous model data
============================

This step exports the results (endogenous variable values) of the solved 
numerical problem(s) to the model's SQLite database. This enables further 
analysis, reporting, or comparison of results across scenarios.


Overview
--------

- Exports solved endogenous variable data from the in-memory model to the SQLite database.
- Can export results for all scenarios or for a specified subset.
- Supports overwriting existing results and suppressing warnings as needed.
- Ensures that results are only exported if the model has been successfully solved.

API: :py:meth:`cvxlab.Model.load_results_to_database`


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
    # - Solve the numerical problem(s)
    
    # [CURRENT STEP] Export all results to the database
    model.load_results_to_database(...)


Parameter descriptions
----------------------

- ``scenarios_idx``: A list of scenario indices or a single scenario index for 
  which to export results. If None, results for all scenarios are exported. 
  Defaults to *None*.
- ``force_overwrite``: If True, overwrites existing results in the database 
  without confirmation. Defaults to *False*.
- ``suppress_warnings``: If True, suppresses warnings during the export process. 
  These are usually raised in case exported data and existing data have same numerical 
  values, which is expected in case of re-exports without changes. Defaults to *False*.


Workflow
--------

When :py:meth:`cvxlab.Model.load_results_to_database` is called on a Model instance:

- Checks if the model has been solved (i.e., results are available). If not, 
  logs a warning and aborts export.
- For each scenario (or the specified subset), exports the solved endogenous 
  variable values to the SQLite database.
- If ``force_overwrite`` is True, existing results in the database are replaced.
- If ``suppress_warnings`` is True, any warnings during the export are suppressed.
