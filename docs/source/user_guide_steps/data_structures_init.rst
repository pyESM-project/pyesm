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
- Creates *blank input-data file(s)* for exogenous data tables. The output can be
  a single Excel workbook or multiple Excel/CSV files, depending on the
  ``multiple_input_files`` and ``input_data_files_type`` attributes. See the
  section below on "Generated files" for the supported combinations.
- If existing database or input files are found, the user is given the option 
  to erase and recreate, or to use existing files. This is controlled by the 
  ``use_existing_data`` attribute of the model instance: if set to ``False``, 
  existing files are erased and recreated; if set to ``True``, existing files 
  are used and not overwritten.


Generated files
---------------

This step creates two connected outputs in the model directory:

- A *blank SQLite database*, which stores the model structure in relational form.
- *Blank input data file(s)*, which expose the exogenous SQLite data tables in a
  user-editable format (Excel/CSV).


.. rubric:: SQLite database structure

The generated **SQLite database** contains the following tables:

- A table is defined for each model *Set*, and populated with the coordinates 
  provided in ``sets.xlsx``. These tables are named as ``_set_<SET_NAME>``, where 
  ``<SET_NAME>`` is the capitalized name of the set, as defined in the model 
  settings. This naming convention allows to easily identify the Set tables in 
  the SQLite database (refer to label naming conventions in 
  :class:`cvxlab.defaults.Defaults.Labels`).
- A table is defined for each model *Data Table*, named as ``<data_table_#>``, 
  and generated with columns derived from the related sets, plus ``id`` and 
  ``values`` columns. Notably, **SQLite tables are generated only for exogenous 
  and endogenous Data Tables:** constants are only stored as attributes of the 
  Data Table objects in Python, since they are not supposed to be inspected or 
  displayed by the user.

The key point is that tables generated for model Data Tables are relational tables 
linked to the Set tables through *foreign-key constraints*. Each coordinate column 
in a data table points to the corresponding set table, so only valid set coordinates 
can be stored. The simplified schema below illustrates the idea:

.. mermaid::

   erDiagram
      "_set_SET_NAME_1" {
         int id PK
         text set_name_1_Name
        }
      
      "_set_SET_NAME_2" {
         int id PK
         text set_name_2_Name
        }

      "data_table_1" {
         int id PK
         text set_name_1_Name 
         real values
      }

      "data_table_2" {
         int id PK
         text set_name_1_Name 
         text set_name_2_Name
         real values
      }

      "_set_SET_NAME_1" ||--o{ "data_table_1" : referenced_by
      "_set_SET_NAME_1" ||--o{ "data_table_2" : referenced_by
      "_set_SET_NAME_2" ||--o{ "data_table_2" : referenced_by


In practice, this means that:

- set coordinates are stored once in the set tables;
- data tables reference those coordinates instead of redefining an independent
  structure;
- SQLite can enforce *referential consistency* between sets and data tables.
- The SQLite database can be easily imported by other tools (e.g. PowerBI), which 
  can leverage the relational structure to easily navigate the model data.


.. rubric:: Input data file(s)

After the SQLite database is created, CVXlab exports the **exogenous data tables**
only to *Excel/CSV* input files so that the user can fill the numerical values 
outside the database. Input data file(s) are stored in the ``<model_dir_name>/input_data`` 
directory by default.

The generated files mirror the normalized layout of the exogenous tables in SQLite:
each row corresponds to one valid combination of set coordinates, and the
``values`` column is left blank for user input, as shown in the generalized example 
below.


.. list-table:: Example of exogenous Data Table layout
   :header-rows: 1
   :widths: 10 35 35 20

   * - id
     - <set_name_1>_Name
     - <set_name_#>_Name
     - values
   * - <int>
     - <str>
     - <str>
     - <int | float>
   * - ...
     - ...
     - ...
     - ...

The practical meaning of these fields, and guidance on which columns should or
should not be edited by the user, are provided in
:ref:`Fill exogenous model data <fill-exogenous-data>`.

The two settings controlling the export layout are: ``multiple_input_files``, 
defining whether exogenous data tables are exported to one file or to one file 
per table; and ``input_data_files_type``, selecting the file format of the exported 
input data. The supported combinations and related behavior are summarized below:

.. list-table:: Input data export behavior
   :header-rows: 1
   :widths: 20 20 60

   * - ``multiple_input_files``
     - ``input_data_files_type``
     - Output
   * - ``False``
     - ``"xlsx"``
     - One Excel workbook named ``input_data.xlsx``, with one sheet per
       exogenous data table.
   * - ``True``
     - ``"xlsx"``
     - One Excel file per exogenous data table. Each file name (and its inner tab 
       name) are set as the Data Table name.
   * - ``True``
     - ``"csv"``
     - One CSV file per exogenous data table, named as the Data Table name.
   * - ``False``
     - ``"csv"``
     - Single CSV export is not available. Error is returned.



