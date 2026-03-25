.. _numerical-problem-init:

Initialization of numerical problem/s
=====================================

This step prepares the *numerical optimization problem(s)* for a *CVXlab model*, 
transforming symbolic definitions and data structures into a form ready for 
solution by a numerical solver.


Overview
--------

- Fetches data from the *input data Excel file(s)* to the exogenous data tables of 
  the *SQLite database*, verifying the consistency of the data provided.
- Loads and validates *symbolic problem(s) expressions* from the model settings, 
  ensuring that all referenced variables and data tables are properly defined.
- Initializes *CVXPY problem(s) variables* and assigns data to exogenous ones.
- Constructs the *CVXPY numerical problem(s)* for each scenario, based on the 
  symbolic expressions and defined variables.

API: :py:meth:`cvxlab.Model.refresh_database_and_initialize_problem`


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
    
    # [CURRENT STEP] Initialization of numerical problem(s)
    model.refresh_database_and_initialize_problem(
        table_key_list=[...],
        force_overwrite=False,
    )


Parameter descriptions
----------------------

All arguments are optional and have sensible defaults. You can customize the 
directory creation as follows:

- ``table_key_list``: List of specific tables keys for which data will be 
  refreshed from the input files. This should be empty in case a model is initialized 
  for the first time. Specific table(s) can be listed in case of data updates. 
  Defaults empty list (all tables are refreshed).
- ``force_overwrite``: Whether to overwrite existing data in SQLite database or 
  numerical problem definitions without confirmation. Defaults to *False*.


Workflow
--------

When :py:meth:`cvxlab.Model.refresh_database_and_initialize_problem` is called 
on a Model instance:

- Loads exogenous data from the *input data Excel file(s)*, assigning values to 
  exogenous data tables in the *SQLite database*. 
- Parses exogenous variables, and fills the empty entries in the related data 
  tables with value provided by the ``blank_fill`` variable attribute. This 
  facilitates the user in filling repetitive data entries in data tables.
- Loads and parses *symbolic problem expressions* from model settings, *validating 
  problem structure* against a validation schema and raising explicit errors if 
  any issues are found.
- Checks if all variables numeric data are present in the SQLite database: in 
  case NULL entries are found, the method logs the table name and the corresponding 
  row IDs, and raises an error.
- Initializes model variables structures, including all variables information such 
  as the *type* (endogenous, exogenous, constants, hybrid), *shape* (rows and 
  columns), *cardinality* (inter- and intra-problem dimensions) and the associated
  *CVXPY variable* object, according to the model settings.
- Fetches *exogenous variable data* from SQLite database and assigns it to the 
  corresponding CVXPY variable objects.
- Constructs the numerical optimization problem(s) for each scenario, generating and 
  assembling the expressions using the symbolic definitions and loaded data.
- If ``force_overwrite=True``, any existing numerical value in exogenous data tables
  (or a selection of them, in case ``table_key_list`` is specified) and all variables 
  and problems objects are overwritten without confirmation.
