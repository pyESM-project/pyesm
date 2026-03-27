.. _data-structures-init:

Initialization of data structures
=================================

This step prepares the fundamental data structures required for a CVXlab model, 
including loading sets and variable coordinates in the Model instance ``Index``, 
and generating *blank input files* and *SQLite database*. 
These actions are typically performed after the model directory and setup files 
have been created, the model Sets structure has already been defined in the 
``sets.xlsx`` file, and before numerical problem generation and solution.


Overview
--------

- Loads sets structure and related data from ``sets.xlsx`` file, then loads data 
  tables and variables properties, defining related coordianates and dimensions 
  in the Model instance ``Index``. During this process, various checks are performed 
  to ensure consistency of the model structure and data.
- Initializes blank data structures: creates a new blank *SQLite database* and 
  *input data* file/s, both with filled with sets coordinates, and provided as 
  normalized tables. Input data files are ready to be filled with exogenous data 
  by the user.

API: :py:meth:`~cvxlab.Model.initialize_model_environment`


Typical Usage
-------------

.. code-block:: python

    import cvxlab

    # Previous steps: 
    # - Create model directory and setup files
    # - Create Model instance
    # - Fill sets data (coordinates)
    
    # [CURRENT STEP] Initialization of data structures
    model.initialize_model_environment()


Workflow
--------

When :py:meth:`~cvxlab.Model.initialize_model_environment` is called on a Model 
instance:

- Loads sets data (i.e., the coordinates) from the ``sets.xlsx`` file into the 
  model's ``Index``.
- Assigns coordinates to all data tables.
- Defines coordinates for variables, filtering coordinates of data tables and 
  assigning them to variable dimensions (*inter-problem* and *dimension sets*).
- By default, fetches foreign keys for data tables (enables SQLite constraints).
- Validates variable definitions, performing various dimensionality checks.
- Generates a *blank SQLite database* with set tables and data tables, filling 
  set tables with related coordinates.
- Creates *blank input-data Excel file(s)* for exogenous data tables. 
  See the section below on "Generated files" for details on file structure and 
  the effect of the ``multiple_input_files`` attribute.
- If existing database or input files are found, the user is given the option 
  to erase and recreate, or to use existing files. This is controlled by the 
  ``use_existing_data`` attribute of the model instance: if set to ``False``, 
  existing files are erased and recreated; if set to ``True``, existing files 
  are used and not overwritten.


Generated files
---------------

- A *blank SQLite database* is generated in the model directory, with tables for 
  sets and data tables. Set tables are filled with coordinates, while data tables 
  are created empty, ready to be filled with exogenous data by the user. 
- *Blank input data file(s)* are generated in the model directory, with one file 
  per data table if the ``multiple_input_files`` attribute of the model instance is
  set to ``True``, or a single file containing all data tables if ``multiple_input_files``
  is set to ``False``. In both cases, the file(s) are filled with sets coordinates
  and provided as normalized tables ready to be filled with exogenous data by the 
  user.

