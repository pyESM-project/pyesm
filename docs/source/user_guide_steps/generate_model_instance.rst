.. _generate-model-class-instance:

Model class instance generation
===============================

This step creates a Model instance, which is the main object for handling all 
CVXlab model operations, including data management, problem generation, and solution.


Overview
--------

- The *Model instance* is initialized with paths, settings, and logging configuration.
- It loads *model structure* and *coordinates*, validates model directory content, 
  and sets up the core components for handling data and numerical problems.
- Existing data structures can be loaded if available, or new files and 
  directories are generated as needed, depending on the initialization flags.

API (class constructor): :py:class:`cvxlab.Model`


Typical Usage
-------------

The Model class instance is the main CVXlab object: once initialized, it provides 
access to all the APIs for subsequent modeling steps, including data management, 
problem generation, and solution. The constructor can be called with default arguments,
and it serves as the main interface for subsequent modeling steps, such as data 
loading, problem generation, and optimization.

.. code-block:: python

  import cvxlab

  # Previous steps: 
  # - Create model directory and setup files
  
  # [CURRENT STEP] Create Model instance
  model = cvxlab.Model(
      model_dir_name="my_model",
      main_dir_path="path/to/parent",
      model_settings_from="yml",  # or "xlsx"
      detailed_validation=False,
      use_existing_data=False,
      log_level="info",
      log_format="standard",
      multiple_input_files=False,
      input_data_files_type="xlsx", # or "csv"
  )


Parameters description
----------------------

.. list-table::
  :header-rows: 1
  :widths: 24 56 20

  * - Parameter
    - Description
    - Default
  * - ``model_dir_name``
    - Name of the model directory where model files are stored.
    - ``"model"``
  * - ``main_dir_path``
    - Parent directory where the model directory is located.
    - Current working directory
  * - ``model_settings_from``
    - Format of the model settings file, either ``"yml"`` or ``"xlsx"``.
    - ``"xlsx"``
  * - ``detailed_validation``
    - If ``True``, returns detailed validation errors for model sets, data
      tables, variables, and expressions.
    - ``False``
  * - ``use_existing_data``
    - If ``True``, relies on existing data structures instead of generating new
      database and input files.
    - ``False``
  * - ``log_level``
    - Logging level for the model instance.
    - ``"info"``
  * - ``log_format``
    - Logging format used by the model logger.
    - ``"standard"``
  * - ``multiple_input_files``
    - If ``True``, exports one input data file per exogenous data table;
      otherwise, uses a single workbook with multiple sheets.
    - ``False``
  * - ``input_data_files_type``
    - File type for input data files. If ``multiple_input_files=False``, only
      ``"xlsx"`` is allowed. Otherwise, it can be either ``"xlsx"`` or ``"csv"``.
    - ``"xlsx"``


Class constructor workflow
--------------------------

Once a Model instance is generated, the actions below are occurring:

- The model directory is generated in the path ``main_dir_path/model_dir_name``, 
  and populated with the necessary files. If the directory already exists, its 
  content is validated. In case ``model_dir_name`` is not provided, *"model"* is 
  used ad default. In case the parent directory path ``main_dir_path`` is not 
  provided, the *current working directory* is used as default. Format of the 
  model settings file/s is determined by the ``model_settings_from`` argument, 
  with *xlsx* assumed as default format.

- Eventual user-defined :ref:`Symbolic operators <api_symbolic_operators>` or 
  :ref:`Constants <api_constants_types>` are imported and registered.

- The ``Core`` class is initialized within the Model instance, which in turn 
  initializes inner classes with different responsibilies:

  .. list-table::
    :header-rows: 1
    :widths: 20 80

    * - Class
      - Description
    * - ``Index``
      - *centralized registry* for managing sets, data tables and variables. Once 
        initialized, it fetches and validates data structures from the model settings 
        file/s, eventually highlighting errors and inconsistencies in the definition 
        of sets, data tables, and variables. All information about the latter objects 
        are stored and accessed in this class.
    * - ``Database``
      - Embeds subclasses and methods for interacting and operating on the *SQLite
        database* and the Excel/CSV input data files.
    * - ``Problem``
      - Embeds tools for reading symbolic problem defined by the user, and to
        automatically generate and solve the related `CVXPY 
        <https://www.cvxpy.org/tutorial/intro/index.html>`_ optimization problem based
        on the defined sets, variables and expressions.

- Finally, the two following cases may occur:

  .. list-table::
      :header-rows: 1
      :widths: 20 80

      * - Argument 
        - Behavior
      * - ``use_existing_data=False``
        - The *sets.xlsx* file is generated based on the model settings, in order 
          to be subsequently filled by the user (see :ref:`Fill sets data <fill-sets-data>` 
          section). The process ends here, and the model instance is ready to be 
          used for subsequent steps through its own :ref:`Model class APIs <api_model>`.
      * - ``use_existing_data=True``
        - The fundamental data structures (namely the *sets excel file*, the 
          *input data files* and the model *SQLite database*) are already present 
          in the model directory and filled with data. In this case, the model 
          *coordinates* (i.e. the sets data), the information related to data tables, 
          variables and problems expressions are all loaded in the ``Index``, the 
          *numerical problem* is initialized in the ``Problem`` class, and data 
          fetched from the SQLite database through the ``Database`` class. 

In case of errors or inconsitencies in the definition of model settings of model 
data structures, error messages are logged and returned, with different levels of detail
depending on the value of the ``detailed_validation`` argument, in order to ease 
the debugging process.


Generated files
---------------

Only the *sets.xlsx* file is eventually generated, in case ``use_existing_data`` 
is set to *False*.
