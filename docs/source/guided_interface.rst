.. _guided_interface:

Guided Interface
================

CVXlab provides a menu-driven interface for users who want to follow the
modeling workflow without writing calls to every API. The interface guides the
user through model creation, data initialization, problem solution, results
export, and common maintenance and inspection operations.

Each menu action corresponds to one public CVXlab API. Actions are deliberately
kept separate: for example, *Run model* calls :py:meth:`~cvxlab.Model.run_model` 
but does not refresh the database or initialize the numerical problem first. 
If a required earlier step has not been completed, the interface reports the 
resulting error and returns to the menu.

It is highly recommended to read the :ref:`user_guide` main page for an overview 
of the fundamental concepts and the modeling workflow before using the interface. 


Starting the interface
----------------------

The interface can be started without arguments:

.. code-block:: python

  import cvxlab

  cvxlab.gui()

After an action is selected, the interface asks for the settings required by
that action. Pressing :kbd:`Enter` accepts the displayed default. Boolean values
can be entered as ``true`` or ``false``; lists and dictionaries use normal
Python syntax, for example ``["demand", "cost"]`` or
``{"problem": "CLARABEL"}``.

Answers are retained for the remainder of the session. Consequently, a setting
is requested only when it is missing and is first needed.

Every menu includes *Quit CVXlab*, which closes the interface from any level.
Nested menus also include *Back*, which returns to the previous menu without
closing the interface.

API: :py:func:`cvxlab.gui`


Preconfiguring the session
--------------------------

Basic settings can be passed directly to :py:func:`cvxlab.gui`:

.. code-block:: python

  cvxlab.gui(
      model_dir_name="my_model",
      main_dir_path="/path/to/models",
      model_settings_from="yml",
      log_level="info",
  )

For a reusable configuration, the same arguments can be collected in a dictionary 
following :py:class:`cvxlab.FrontendConfig` and expanded when calling 
:py:func:`cvxlab.gui`. Settings used to construct a :py:class:`cvxlab.Model` are 
placed at the top level. Arguments belonging to a specific action are placed under 
``action_settings``, using the public API method name as the key. This also applies 
to utility-specific settings, such as the source file used by 
:py:func:`cvxlab.transfer_setup_info_xlsx`.

.. code-block:: python

  import cvxlab

  config = {
      "model_dir_name": "my_model",
      "main_dir_path": "/path/to/models",
      "model_settings_from": "yml",
      "multiple_input_files": False,
      "input_data_files_type": "xlsx",
      "action_settings": {
          "generate_input_data_files": {
              "table_key_list": ["demand", "cost"],
              "force_overwrite": False,
          },
          "refresh_database_and_initialize_problem": {
              "table_key_list": ["demand", "cost"],
              "force_overwrite": False,
          },
          "run_model": {
              "solution_mode": "parallel",
              "solver": "CLARABEL",
              "solver_verbose": False,
          },
          "load_results_to_database": {
              "force_overwrite": True,
          },
      },
  }

  cvxlab.gui(**config)

Only settings omitted from this dictionary are requested interactively. Action
names and their arguments are validated before the menu is opened, so spelling
errors are reported immediately.

The interface does not accept an existing :py:class:`cvxlab.Model` instance.
Models are created, opened, or loaded explicitly from the *Model session* menu.

API: :py:class:`cvxlab.FrontendConfig`, :py:func:`cvxlab.gui`


Guided modeling workflow
------------------------

For a model generated from scratch, use the interface actions in the following
order. Steps that require editing model files remain user operations outside
the interface.

.. list-table:: Guided workflow for a new model
  :header-rows: 1
  :widths: 8 36 32 24

  * - Step
    - Interface action or user operation
    - API called
    - Detailed modeling step
  * - 1
    - *Utilities* / *Create model directory*
    - :py:func:`cvxlab.create_model_dir`
    - :ref:`generation-of-model-directory`
  * - 2
    - Fill the generated model setup file(s)
    - User operation
    - :ref:`fill-model-setup-files`
  * - 3
    - *Model session* / *Create new Model instance*
    - :py:class:`cvxlab.Model`
    - :ref:`generate-model-class-instance`
  * - 4
    - Fill ``sets.xlsx`` with the model coordinates
    - User operation
    - :ref:`fill-sets-data`
  * - 5
    - *Model operations* / *Initialize model environment*
    - :py:meth:`~cvxlab.Model.initialize_model_environment`
    - :ref:`data-structures-init`
  * - 6
    - Fill the generated exogenous input data file(s)
    - User operation
    - :ref:`fill-exogenous-data`
  * - 7
    - *Model operations* / *Refresh database and initialize problem*
    - :py:meth:`~cvxlab.Model.refresh_database_and_initialize_problem`
    - :ref:`numerical-problem-init`
  * - 8
    - *Model operations* / *Run model*
    - :py:meth:`~cvxlab.Model.run_model`
    - :ref:`numerical-problem-run`
  * - 9
    - *Model operations* / *Load results to database*
    - :py:meth:`~cvxlab.Model.load_results_to_database`
    - :ref:`export-model-results`

For a model whose settings and data structures already exist, select *Model
session* / *Open existing Model environment*. The action constructs
:py:class:`cvxlab.Model` with ``use_existing_data=True``. Exogenous data can
then be updated, followed by the refresh, run, and results-export actions when
required. See :ref:`model_generation_from_existing` for the corresponding
programmatic workflow.

.. note::

  Creating or opening a model is an explicit session action. Selecting an
  operation without an active model produces an error rather than creating a
  model implicitly.


Model actions and related APIs
------------------------------

The main operations mirror the public :py:class:`cvxlab.Model` API:

.. list-table::
  :header-rows: 1
  :widths: 38 30 32

  * - Interface action
    - API called
    - Purpose
  * - Generate input data files
    - :py:meth:`~cvxlab.Model.generate_input_data_files`
    - Generate blank input files for selected exogenous data tables.
  * - Refresh database and initialize problem
    - :py:meth:`~cvxlab.Model.refresh_database_and_initialize_problem`
    - Import selected input data and rebuild the numerical problem.
  * - Run model
    - :py:meth:`~cvxlab.Model.run_model`
    - Solve the initialized numerical problem or problems.
  * - Load results to database
    - :py:meth:`~cvxlab.Model.load_results_to_database`
    - Export solved endogenous data to SQLite.
  * - Reinitialize SQLite database
    - :py:meth:`~cvxlab.Model.reinitialize_sqlite_database`
    - Restore a blank database from the current model structure.
  * - Update set tables
    - :py:meth:`~cvxlab.Model.update_sets_tables`
    - Update database set tables from the current coordinates.
  * - Check model results
    - :py:meth:`~cvxlab.Model.check_model_results`
    - Compare results against a reference database.
  * - Inspect set data
    - :py:meth:`~cvxlab.Model.set`
    - Display a selected set and its coordinates.
  * - Inspect variable data
    - :py:meth:`~cvxlab.Model.variable`
    - Display data and metadata for a selected variable.

The *Show active Model summary* action reads the model's
:py:attr:`~cvxlab.Model.sets`, :py:attr:`~cvxlab.Model.data_tables`,
:py:attr:`~cvxlab.Model.variables`, :py:attr:`~cvxlab.Model.scenarios`, and
:py:attr:`~cvxlab.Model.is_problem_solved` properties.


Utilities
---------

The interface also exposes utilities that support, but do not replace, the
modeling workflow:

.. list-table::
  :header-rows: 1
  :widths: 38 30 32

  * - Interface action
    - API called
    - Purpose
  * - Create model directory
    - :py:func:`cvxlab.create_model_dir`
    - Create a standard model directory and blank setup templates.
  * - Transfer setup information from Excel
    - :py:func:`cvxlab.transfer_setup_info_xlsx`
    - Transfer setup information from a model-structure workbook.
  * - Copy user-defined templates
    - :py:func:`cvxlab.copy_user_defined_templates`
    - Copy templates into the selected model directory.
  * - Save or load a Model instance
    - :py:func:`cvxlab.handle_model_instance`
    - Persist the active model or restore a saved instance.

For complete argument descriptions, follow the API links above or see the
:doc:`api_reference`. For a conceptual and programmatic explanation of every
step, continue with the :ref:`user_guide`.
