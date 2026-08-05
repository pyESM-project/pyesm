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


Menu overview
-------------

The complete menu structure is summarized below. Each leaf pairs the visible
action with the API it calls. The *Back* and *Quit CVXlab* navigation entries
are omitted because they do not call an API.

.. container:: gui-menu-tree

  - **Guided interface** → :py:func:`cvxlab.gui`

    - **Model session**

      - **Create new Model instance** → :py:class:`cvxlab.Model`
        ``(..., use_existing_data=False)``
      - **Open existing Model environment** → :py:class:`cvxlab.Model`
        ``(..., use_existing_data=True)``
      - **Save active Model instance** →
        :py:func:`cvxlab.handle_model_instance` ``(..., action="save")``
      - **Load saved Model instance** →
        :py:func:`cvxlab.handle_model_instance` ``(..., action="load")``

    - **Model operations**

      - **Initialize model environment** →
        :py:meth:`~cvxlab.Model.initialize_model_environment`
      - **Generate input data files** →
        :py:meth:`~cvxlab.Model.generate_input_data_files`
      - **Refresh database and initialize problem** →
        :py:meth:`~cvxlab.Model.refresh_database_and_initialize_problem`
      - **Run model** → :py:meth:`~cvxlab.Model.run_model`
      - **Load results to database** →
        :py:meth:`~cvxlab.Model.load_results_to_database`

    - **Model maintenance**

      - **Reinitialize SQLite database** →
        :py:meth:`~cvxlab.Model.reinitialize_sqlite_database`
      - **Update set tables** →
        :py:meth:`~cvxlab.Model.update_sets_tables`
      - **Check model results** →
        :py:meth:`~cvxlab.Model.check_model_results`

    - **Inspect model**

      - **Inspect set data** → :py:meth:`~cvxlab.Model.set`
      - **Inspect variable data** → :py:meth:`~cvxlab.Model.variable`
      - **Show active Model summary** → :py:meth:`~cvxlab.Model.show_model_summary`

    - **Utilities**

      - **Create model directory** → :py:func:`cvxlab.create_model_dir`
      - **Transfer setup information from Excel** →
        :py:func:`cvxlab.transfer_setup_info_xlsx`
      - **Copy user-defined templates** →
        :py:func:`cvxlab.copy_user_defined_templates`
      - **Show installed solvers** → :py:func:`cvxlab.installed_solvers`


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
and expanded when calling :py:func:`cvxlab.gui`. Settings used to construct a
:py:class:`cvxlab.Model` are placed at the top level. Arguments belonging to a
specific action are placed under ``action_settings``, using the public API method
name as the key. This also applies to utility-specific settings, such as the
source file used by :py:func:`cvxlab.transfer_setup_info_xlsx`.

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

``use_existing_data`` is therefore intentionally not accepted as a top-level
:py:func:`cvxlab.gui` setting. Choose *Create new Model instance* to pass
``use_existing_data=False`` to :py:class:`cvxlab.Model`, or *Open existing Model
environment* to pass ``use_existing_data=True``. Keeping this choice in the menu
prevents a configured boolean from contradicting the selected session action.

API: :py:func:`cvxlab.gui`


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


Behavioral notes and further information
----------------------------------------

Each action invokes only the API shown in the menu tree. Prerequisite operations
are not run automatically, and an action that fails returns control to the menu.
Settings entered interactively are retained for the rest of the GUI session.

See the :doc:`api_reference` for complete argument descriptions. For conceptual
and programmatic explanations of the modeling steps, continue with the
:ref:`user_guide`.
