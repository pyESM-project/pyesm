.. _user_guide:

User Guide
==========

This section provides a comprehensive guide to using CVXlab for conceptualizing,
generating and solving optimization problems. This includes all the necessary 
steps to :ref:`generate a model from scratch <model_generation_from_scratch>`, 
or to :ref:`generate it from existing settings/data <model_generation_from_existing>`. 
At the end of the section, a set of :ref:`utilities <utilities>` is provided
to generate/handle model directory, facilitate model properties and data inspections, 
saving and loading of model instances, refreshing model database.

Before diving into each single step, it is suggested to read all this page, which 
provides a synthetic but comprehensive overview about the CVXlab modeling workflow.

The :ref:`tutorials` section provides different examples across the same workflow 
steps used in the current page, from conceptual definition to results export. 
While the user guide aims at providing general concepts, tutorials are recommended 
to see how those concepts are instantiated in a concrete models. 
For CVXlab newbies, it is recommended to start with the :ref:`resource-constrained 
production planning problem <tutorial-production-planning>` 
tutorial.


Guided interface
----------------

Users who prefer a menu-driven workflow can configure and run a model through
the :ref:`guided_interface`. That page explains interactive prompts,
preconfiguration with :py:class:`cvxlab.FrontendConfig`, the available actions,
and how each action maps to the modeling steps and public APIs documented below.


.. _model_generation_from_scratch:

Model generation from scratch
-----------------------------

The CVXlab modeling workflow for generating a model from scratch is summarized
in the table below. Each **workflow step** is described in the **description** 
column, and it links to the corresponding detailed page.


..  list-table:: CVXlab full modeling workflow
    :header-rows: 1
    :widths: 40 58

    * - Workflow step
      - Description
    * - :ref:`Conceptual model definition <conceptual-model-definition>`
      - Mathematical model conceptualization. *User* defines the mathematical 
        structure of the model (*pen on paper!*).
    * - :ref:`Generation of model directory <generation-of-model-directory>`
      - Model directory and setup template file(s) are generated. 
        API: :py:func:`cvxlab.create_model_dir`
    * - :ref:`Fill model setup file(s) <fill-model-setup-files>`
      - *User* fills the setup files.
    * - :ref:`Generate Model class instance <generate-model-class-instance>`
      - CVXlab Model instance is created, and conceptual model validated. 
        Blank ``sets.xlsx`` input file is generated. API: :py:class:`cvxlab.Model`
    * - :ref:`Fill sets data <fill-sets-data>`
      - *User* fills ``sets.xlsx`` input file with the model coordinates.
    * - :ref:`Initialization of data structures <data-structures-init>`
      - Blank SQLite database and Excel input data file(s) are generated. 
        API: :py:meth:`~cvxlab.Model.initialize_model_environment`
    * - :ref:`Fill exogenous model data <fill-exogenous-data>`
      - *User* fills the exogenous Excel input data file(s).
    * - :ref:`Initialization of numerical problem(s) <numerical-problem-init>`
      - Symbolic problem is validated, and numerical problem initialized. 
        API: :py:meth:`~cvxlab.Model.refresh_database_and_initialize_problem`
    * - :ref:`Run numerical problem(s) <numerical-problem-run>`
      - Numerical problem is solved. API: :py:meth:`~cvxlab.Model.run_model`
    * - :ref:`Export model results <export-model-results>`
      - Results are exported from CVXlab Model to the SQLite database. 
        API: :py:meth:`~cvxlab.Model.load_results_to_database`


.. rubric:: Step by step description of the CVXlab modeling workflow

- :ref:`conceptual-model-definition`: the whole CVXlab modeling process must be 
  grounded on a solid conceptualization and mathematical definition of the problem 
  to be solved. This step consists in defining the fundamental model 
  structure pen-on-paper. The following items must be defined:

  .. list-table::
    :header-rows: 1
    :widths: 35 65

    * - Conceptual component
      - Description
    * - :ref:`defining-sets`
      - The dimensions of the model, defining its scope.
    * - :ref:`definig-data-tables-variables`
      - *Data tables* are collections of model data identified by one or more
        sets. *Variables* are symbolic items pointing to all or a subset of
        the data entries in those tables.
    * - :ref:`definig-expressions-and-problems`
      - *Problems* are collections of *expressions*, which are symbolic items
        constructed from defined *variables* and *symbolic operators*. More
        than one problem can be stated, each defined as a system of linear
        equalities or as a convex optimization problem.

  Once the problem is well defined, the CVXlab modeling process can start.

- :ref:`generation-of-model-directory`: a model directory is generated based on 
  a predefined template, and it contains all the necessary files to transpose 
  the conceptual model into a CVXlab model instance. Setup files can be generated 
  as *YAML* or *Excel* formats, depending on user's preference. 
  Eventually, *Python template modules* can be included in the model directory to
  extend CVXlab functionalities with user-defined symbolic operators and user-defined 
  constants data types (``user_defined_operators.py`` and ``user_defined_constants.py``).

  API: :py:func:`cvxlab.create_model_dir`
   
- :ref:`fill-model-setup-files`: the user translates the conceptual model into 
  the setup files available in the model directory. The setup information can be
  provided either in *YAML* format (as three separate files) or in *Excel*
  format (default ``model_settings.xlsx`` workbook with three tabs), as 
  summarized below:

  .. list-table::
    :header-rows: 1
    :widths: 30 35 35

    * - Setup component
      - YAML file
      - ``model_settings.xlsx`` tab
    * - Structure of sets
      - ``structure_sets.yml``
      - ``structure_sets``
    * - Structure of data tables and variables
      - ``structure_variables.yml``
      - ``structure_variables``
    * - Mathematical problem
      - ``problem.yml``
      - ``problem``

  Optionally, user-defined symbolic operators and constant data types can be
  implemented in dedicated Python template modules included in the model
  directory.

- :ref:`generate-model-class-instance`: the instance of the Model class is 
  generated through the *Model class constructor*, which translates the 
  information provided by setup file/s into a Python object. The model instance 
  includes all the necessary information and the APIs to generate and to solve 
  numerical problems, and to handle exogenous/endogeous model data.
  The model instance generation automatically triggers the generation of the 
  Excel file ``sets.xlsx`` to be filled with the *sets coordinates* (see 
  :ref:`Fill sets data (model coordinates) <fill-sets-data>`).
  During the Model class instantiation, a comprehensive validation of model
  structure is performed to ensure that all model components are correctly and 
  consistently defined.

  API (class constructor): :py:class:`cvxlab.Model`
 
- :ref:`fill-sets-data`: the user fills the sets Excel file with the elements 
  belonging to each set, defined as *coordinates*. The Excel file includes one 
  tab per each set, where user can eventually specify other set methibutes, such
  as set *filters* and *aggregation* categories.
  Once this step is completed, all the necessary information defining the model 
  structure is available, and the data structures can be generated.

- :ref:`data-structures-init`: this step imports the set coordinates into the
  model instance, checks that variables are defined consistently, and generates
  the initial model data structures.

  .. list-table::
    :header-rows: 1
    :widths: 32 68

    * - Output
      - Description
    * - Blank *SQLite* database
      - Relational database containing *set tables* and *data tables*,
        linked by unique relationships.
    * - Blank *Excel/CSV* input data file(s)
      - One or more Excel or CSV files, depending on user preference, containing
        the *exogenous data tables* in normalized form to be filled by the
        user (see :ref:`Fill exogenous model data <fill-exogenous-data>`).

  API: :py:meth:`~cvxlab.Model.initialize_model_environment`

- :ref:`fill-exogenous-data`: user fills the Excel/CSV input data file/s with the 
  exogenous data tables values. In case of models with large amount of data, this
  step can be critical, time consuming and highly prone to errors. To facilitate
  this task, CVXlab provides features to limit the amount of data entries to be
  filled (as example: in settings, a default value can be defined for data table 
  entries in case of missing data).
  Once this step is completed, the numerical model can be generated and solved.

- :ref:`numerical-problem-init`: this step includes fetching exogenous data from
  excel input data file/s to the model SQLite database, loading symbolic problem/s 
  from model settings, and generating the numerical problem/s (as *CVXPY* problem 
  object).
  During the problem generation step, a comprehensive validation of symbolic problem 
  and model data is performed to ensure that the symbolic problem is consistently 
  defined, and that all necessary data entries are correctly provided.

  API: :py:meth:`~cvxlab.Model.refresh_database_and_initialize_problem`

- :ref:`numerical-problem-run`: in this step, the numerical problem/s are solved
  based on user settings, including selection of the adopted solver, the related 
  verbosity level, and other numerical settings. Solver settings can be specified 
  for each problem, or be the same for all problems. In case of multiple numerical 
  problems, the user can define the *solution mode* to be adopted:

  .. list-table::
    :header-rows: 1
    :widths: 30 70

    * - Solution mode
      - Description
    * - ``parallel``
      - All numerical problems defined withing the Model instance are solved 
        without exchanging information between them (no problems dependancies). 
        This is the *default* solution mode.
    * - ``sequential``
      - Numerical problems are solved sequentially: results from one problem 
        *may be used* as inputs for the next in a user-defined problem solution 
        chain. Useful in case data need to be processed sequentially.
    * - ``integrated``
      - Numerical problems are solved based on a *block Gauss-Seidel* (alternating 
        optimization) algorithm: for each iteration, input data for variables 
        shared among problems are updated based on the latest results from 
        previous iteration, until convergence is reached. Useful for decomposing 
        nonlinear problems into smaller convex sub-problems.

  API: :py:meth:`~cvxlab.Model.run_model`

- :ref:`export-model-results`: in case numerical problem/s have successfully
  solved, numerical results are exported to endogenous data tables of the 
  SQLite database.

  API: :py:meth:`~cvxlab.Model.load_results_to_database`


.. _model_generation_from_existing:

Model generation from existing settings/data
--------------------------------------------

The CVXlab modeling workflow for generating a model from existing settings/data 
is summarized in the table below. Each **workflow step** is described in 
the **description** column, and it links to the corresponding detailed page.

.. list-table:: CVXlab modeling workflow from existing settings/data
  :header-rows: 1
  :widths: 40 58

  * - Workflow step
    - Description
  * - :ref:`Generate Model class instance <generate-model-class-instance>`
    - CVXlab Model instance is created, and conceptual model validated. 
      ``sets.xlsx`` file is assumed to be already filled by the user. 
      API: :py:class:`cvxlab.Model`
  * - :ref:`Fill exogenous model data <fill-exogenous-data>`
    - (**OPTIONAL**) *User* updates/fills the exogenous Excel input data file(s).
  * - :ref:`Initialization of numerical problem(s) <numerical-problem-init>`
    - (**OPTIONAL**) SQLite database is refreshed, symbolic problem is validated, 
      and numerical problem initialized. 
      API: :py:meth:`~cvxlab.Model.refresh_database_and_initialize_problem`
  * - :ref:`Run numerical problem(s) <numerical-problem-run>`
    - Numerical problem is solved. API: :py:meth:`~cvxlab.Model.run_model`
  * - :ref:`Export model results <export-model-results>`
    - Results are exported from CVXlab Model to the SQLite database. 
      API: :py:meth:`~cvxlab.Model.load_results_to_database`


.. rubric:: Step by step description of the CVXlab modeling workflow

- :ref:`generate-model-class-instance`: the instance of the Model class is 
  generated through the *Model class constructor* as the first step, specifying
  that the model relies on existing data (i.e. by passing ``use_existing_data=True`` 
  to the constructor). 
  Beside setup file/s (see :ref:`Fill model setup file/s <fill-model-setup-files>`), 
  other data structures must be present in the model directory, including the 
  sets Excel file filled with the related coordinates (see :ref:`Fill sets data 
  (model coordinates) <fill-sets-data>`), the blank SQLite database (with set 
  tables and data tables, see :ref:`Initialization of data structures 
  <data-structures-init>`), and the Excel input data directory (see :ref:`Fill 
  exogenous model data <fill-exogenous-data>`). 
  
  The Model constructor checks and validate the model directory structure and 
  the presence of all necessary files. Then, it loads the structures of sets,
  data tables and variables in the index, and fetches problems from the setup 
  file/s. Then it loads coordinates from the sets Excel file to the model instance. 
  Finally, it initializes numerical problem/s and fetches exogenous data from the 
  SQLite database. The model instance includes all the necessary information and 
  the APIs to generate and to solve numerical problems, and to handle model data.

  API (class constructor): :py:class:`cvxlab.Model`

- :ref:`fill-exogenous-data`: (**optional**) in this step, user may update exogenous 
  model data in the Excel file/s. This step is especially useful in case of 
  multiple consecutive model runs, where only exogenous data are changed.
  If needed, one or more blank input data file/s can be re-generated from the 
  blank SQLite database. 

  API: :py:meth:`~cvxlab.Model.generate_input_data_files`

- :ref:`numerical-problem-init`: (**optional**) this step needs to be made in case
  of exogenous data have updated (see :ref:`Fill exogenous model data 
  <fill-exogenous-data>`). It fetches exogenous data from the Excel input data 
  files to the SQLite database, updating data in numerical problem/s variables.

  API: :py:meth:`~cvxlab.Model.refresh_database_and_initialize_problem`

- :ref:`numerical-problem-run`: in this step, the numerical problem/s are solved
  based on user settings, including the adopted solver, the related verbosity level, 
  and other settings. Solver settings can be specified for each problem, or be 
  the same for all problems. In case of multiple numerical problems, the user can 
  define the *solution mode* to be adopted (i.e. ``parallel``, ``sequential``, 
  ``integrated``).

  API: :py:meth:`~cvxlab.Model.run_model`

- :ref:`export-model-results`: in case numerical problem(s) have successfully 
  solved, numerical results are exported to the endogenous data tables of the 
  SQLite database. 

  API: :py:meth:`~cvxlab.Model.load_results_to_database`
   

.. _utilities:

Utilities
---------

During the modeling process, or once the model is generated and solved, the user 
may need to inspect model **properties**, or doing some basic operations on the 
database. CVXlab provides a set of **utilities functions** to facilitate these 
tasks, reported in the tables below.

.. list-table:: CVXlab Model instance inspection utilities
  :header-rows: 1
  :widths: 30 68

  * - API
    - Description
  * - :py:attr:`~cvxlab.Model.sets`
    - **Property** reporting the list of model set keys.
  * - :py:attr:`~cvxlab.Model.data_tables`
    - **Property** reporting the list of model data table keys.
  * - :py:attr:`~cvxlab.Model.variables`
    - **Property** reporting the list of model variable keys.
  * - :py:attr:`~cvxlab.Model.is_problem_solved`
    - **Property** indicating the status of the numerical problem.
  * - :py:meth:`~cvxlab.Model.set`
    - **Method** allowing inspection of a specific set, including related
      coordinates and other attributes.
  * - :py:meth:`~cvxlab.Model.variable`
    - **Method** allowing inspection of a specific variable, including related
      data table, shape, filters and other attributes.

  
*Other helper methods* allow to perform basic operations on the model instance 
and on the SQLite database, summarized in the table below.

.. list-table:: CVXlab Model instance helper utilities
  :header-rows: 1
  :widths: 30 68

  * - API
    - Description
  * - :py:meth:`~cvxlab.Model.reinitialize_sqlite_database`
    - **Method** allowing regeneration of a blank SQLite database from the
      current model structure (sets and data tables). Useful to reset the
      database to a clean state.
  * - :py:meth:`~cvxlab.Model.check_model_results`
    - **Method** allowing comparison of the model SQLite database with a
      reference SQLite database, to verify that results are coherent with
      expected values.
  * - :py:meth:`~cvxlab.Model.update_sets_tables`
    - **Method** allowing update of sets tables in the SQLite database based on
      the current model structure and coordinates. Useful after changing set
      coordinates, for example to add aggregation categories.


.. toctree::
  :maxdepth: 1
  :hidden:
  :caption: Modeling workflow steps

  user_guide_steps/conceptual_model_definition
  user_guide_steps/model_directory_generation
  user_guide_steps/fill_model_setup_files
  user_guide_steps/generate_model_instance
  user_guide_steps/fill_sets_data
  user_guide_steps/data_structures_init
  user_guide_steps/fill_exogenous_data
  user_guide_steps/numerical_problem_init
  user_guide_steps/numerical_problem_run
  user_guide_steps/export_model_results





















