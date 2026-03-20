.. _data-structures-init:

Initialization of data structures
---------------------------------

This step prepares the fundamental data structures required for a CVXlab model, 
including loading sets and variable coordinates in the Model instance Index, and 
generating blank input files and database tables. 
These actions are typically performed after the model directory and setup files 
have been created, the model Sets structure has already been defined in the 
``sets.xlsx`` file, and before numerical problem generation and solution.

**Overview**

- Loads sets structure and related coordinates for data tables and variables 
  from ``sets.xlsx`` files into the model Index.
- Initializes blank data structures: creates a new *SQLite database* and *input 
  data* files, ready to be filled with exogenous data.
- Ensures that the model is ready for subsequent steps such as data input, 
  problem generation, and optimization.

APIs:
- :py:meth:`model.load_model_coordinates`
- :py:meth:`model.initialize_blank_data_structure`

**Typical Usage**

.. code-block:: python

	import cvxlab
	model = cvxlab.Model(...)

	# After filling sets Excel file and setup files:
	model.load_model_coordinates()

	# To generate blank database and input files:
	model.initialize_blank_data_structure()

**Parameter descriptions:**

Both methods are called on a Model instance. No arguments are required for typical 
usage, but see below for optional flags.

---

**Loading sets and variable coordinates**

:py:meth:`model.load_model_coordinates(fetch_foreign_keys=True)`

- Loads sets data from the sets Excel file into the model's Index.
- Loads coordinates (i.e., the elements belonging to each set) for all data tables.
- Define coordinates for variables, filtering coordinates of data tables and assigning 
  them to variables dimensions (inter-problem and dimensions sets).
- By default, fetches foreign keys for data tables (enables SQLite constraints).
- Validates variables definitions, performing various dimensionality checks.

**Workflow:**

1. Reads sets data from Excel and loads into Index.
2. Loads coordinates for data tables and variables.
3. Filters and checks variable coordinates.
4. Optionally fetches foreign keys for data tables.

---

**Initializing blank data structures**

:py:meth:`model.initialize_blank_data_structure()`

- Generates a blank SQLite database with set tables and data tables.
- Fills data tables with sets information.
- Creates blank Excel input data files for exogenous variables.
- If existing database or input files are found, gives the option to erase and recreate, or to use existing files.
- If ``use_existing_data`` is set to True, relies on existing files and does not overwrite.

**Workflow:**

1. Checks for existing SQLite database and input data directory.
2. Erases and recreates them if requested, or uses existing files.
3. Creates blank database tables and input files, ready for user data entry.

---

These steps ensure that the model has a consistent and ready-to-use data structure for subsequent modeling and optimization tasks.
