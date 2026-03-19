.. _generate-model-class-instance:

Generation of Model class instance
----------------------------------

This step creates a Model instance, which is the main object for handling all 
CVXlab model operations, including data management, problem generation, and solution.


**Overview**

- The *Model instance* is initialized with paths, settings, and logging configuration.
- It loads *model structure* and *coordinates*, validates model directory content, 
  and sets up the core components for handling data and numerical problems.
- Existing data structures can be loaded if available, or new files and 
  directories are generated as needed, depending on the initialization flags.

API: :py:class:`cvxlab.Model`


**Typical Usage**

The Model class instance is typically created after the model directory and setup files
have been generated (see :ref:`generation of model directory <generation-of-model-directory>`), 
and it serves as the main interface for subsequent modeling steps, such as data 
loading, problem generation, and optimization.

.. code-block:: python

    import cvxlab

    model_instance = cvxlab.Model(
        model_dir_name="my_model",
        main_dir_path="path/to/parent",
        model_settings_from="yml",  # or "xlsx"
        detailed_validation=False,
        use_existing_data=False,
        log_level="info",
        log_format='standard',
        multiple_input_files=False,
        input_data_files_type='xlsx',
    )

**Parameter descriptions:**

In principle, the constructor has designed to be used without specifying arguments,
relying on default values. However, the following parameters can be passed to customize 
the initialization process:

- ``model_dir_name``: Name of the model directory, where model files are stored. If
  not provided, it defaults to '*model*'.

- ``main_dir_path``: Path to the parent directory where the model directory is located.
  If not provided, it defaults to the *current working directory*.

- ``model_settings_from``: Format of the model settings file, either *yml* or *xlsx*.
  'xlsx' format assumed as default.

- ``detailed_validation``: Whether to return detailed error messages during validation.
  If *False*, only a summary of validation errors is returned. If *True*, errors in the 
  definition of model sets/data tables/variables/expressions are detailed. 

- ``use_existing_data``: Whether to rely on existing data structures (*True*) or generate 
  new database and input files (*False*).

- ``log_level``: Logging level (*debug*, *info*, *warning*, *error*).

- ``log_format``: Logging format (*standard*, *minimal*, *detailed*).

- ``multiple_input_files``: Whether to use multiple or single input file(s) for data.

- ``input_data_files_type``: File type for input data files (*xlsx* or *csv*). In 
  case of single input file, only *xlsx* format is allowed (each data table input 
  is stored in a separate sheet of the same file).


**Class constructor workflow**

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

- The ``Core`` class is initialized, which in turn initializes inner classes with 
  different responsibilies:

  - ``Index``: it consists in a *centralized registry* for managing sets, data tables 
    and variables. Once initialized, it fetches and validates data structures from 
    the model settings file/s, eventually highlighting errors and inconsistencies in 
    the definition of sets, data tables, and variables. All information about the 
    latter objects are stored and accessed in this class.

  - ``Database``: it embeds subclasses and methods for interacting and operating 
    on the SQLite database and the Excel/CSV input data files.
  
  - ``Problem``: it embeds tools for reading symbolic problem defined by the user, 
    and to generate and to solve the related **CVXPY** optimization problem based 
    on the defined sets, variables and expressions. 

- Finally, the two following cases may occur:

  - If ``use_existing_data`` is set to *False*: the *sets.xlsx* file is generated 
    based on the model settings, in order to be subsequently filled by the user (
    see :ref:`Fill sets data <fill-sets-data>` section). The process ends here, 
    and the model instance is ready to used for subsequent steps through its own 
    :ref:`Model class APIs <api_model>`.

  - If ``use_existing_data`` is set to *True*: it is assumed that the fundamental data 
    structures (namely the *sets excel file* and the model *SQLite database*) are 
    already present in the model directory and filled with data. In this case, 
    the model *coordinates* (i.e. the sets, data tables and related variables) 
    are loaded in the ``Index``, and the *numerical problem* is initialized in 
    the ``Problem`` class, ready to be solved. 


In case of errors or inconsitencies in the definition of model settings of model 
data structures, error messages are logged and returned, with different levels of detail
depending on the value of the ``detailed_validation`` argument, in order to ease 
the debugging process.