.. _fill-model-setup-files:

Fill model setup file(s)
========================

This page provides a guide to the structure and meaning of CVXlab model
settings.


Introduction
------------

Model setup file(s) represent the essential settings required to translate the
conceptual model (see :ref:`conceptual-model-definition`) from a mathematical
formulation into a *CVXlab Model class instance*.

The setup files define the structure of the fundamental CVXlab objects,
including *sets*, *data tables (with related variables)*, and *mathematical
problems (with related expressions)*. The structure of these files is defined in 
the :py:attr:`default module <cvxlab.defaults.Defaults.DefaultStructures>`, and 
automatically reflected in the generated template settings files.

Once the model directory has been generated (see :ref:`generation-of-model-directory`), 
the setup information is provided in *YAML* format (as three separate files) or 
*Excel* format (as one workbook with three tabs). The setup files are:

- **Structure of sets**: defined in ``structure_sets.yml`` or the
  ``structure_sets`` Excel tab.
- **Structure of data tables and variables**: defined in
  ``structure_variables.yml`` or the ``structure_variables`` Excel tab.
- **Mathematical problem**: defined in ``problem.yml`` or the ``problem`` Excel tab.

Optionally, template files for user-defined symbolic operators and constants can
be included in the model directory if requested during the directory generation
step:

- :ref:`user_defined_operators.py <api_user_defined_operators>`: template for
  custom symbolic operators.
- :ref:`user_defined_constants.py <api_user_defined_constants>`: template for
  custom constant types.


.. _sets_definition:

Sets
----

*Sets* define the dimensions of the model according to the following structure
(here reported in YAML format, but the same logic applies to the Excel file):


.. rubric:: Notation

Names written in ``<...>`` are placeholders to be replaced by user-defined
keys or values. Names written literally, such as ``description`` or
``split_problem``, are field keys and should be kept unchanged.


.. tabs::

  .. group-tab:: YAML

    File: ``structure_sets.yml``

    .. code-block:: yaml

        <set_key_1>:                        # user-defined set key
            description: <str>              # optional
            split_problem: <bool>           # optional
            copy_from: <str>                # optional
            filters: <dict>                 # optional
                <filter_key_1>: [<str>, <str>, ...]
                <filter_key_2>: [<str>, <str>, ...]
                ...
            aggregations: [<int | str>, ...] # optional

        <set_key_2>:
            ...
        ...

  .. group-tab:: XLSX

    File: ``settings.xlsx`` | tab ``structure_sets``
    
    .. list-table::
      :header-rows: 1
      :align: center

      * - set_key
        - description
        - split_problem
        - copy_from
        - filters
        - aggregations
      * - <set_key_1>
        - <str>
        - <bool>
        - <str>
        - <filter_key_1>: [<str>, <str>, ...], <filter_key_2>: [<str>, <str>, ...], ...
        - <int | str>, ...
      * - ...
        - ...
        - ...
        - ...
        - ...
        - ...


.. rubric:: Fields description

``<set_key_#>``: (required) user-defined key of the set. This placeholder must
be replaced with the actual set key used as the key in the SQLite data
table. Case-insensitive. This is the only required field.

- ``description``: (optional) metadata provided by the modeler.
- ``split_problem``: (optional) if *true*, set items define independent numerical
  sub-problems. Such a set is classified as an inter-problem set.
- ``copy_from``: (optional) key of another set to copy data from. If defined, 
  related data need not be provided again in the sets workbook generated in a 
  following step.
- ``filters``: (optional) dictionary used to identify sub-sets of data tables for
  generating variables. Each key is a filter key, and the corresponding value is 
  a list of values defining the filters categories. For example, the *technology 
  type* filter can be used to indentify the following subsets of technologies: 
  *[renewable, non-renewable]*.
- ``aggregations``: (optional) list of aggregation keys used for reporting and
  visualization. These are not used in numerical problem operations, but useful 
  to identify how to aggregate results for reporting and visualization. 

At this stage, the modeler only defines the structure of the sets, while the
actual set items (that is, the *coordinates*) are defined later in the sets 
Excel file generated after the Model class instance is created
(see :ref:`fill-sets-data`).


.. _data_tables_variables_definition:

Data Tables and Variables
-------------------------

*Data Tables* represent collections of data that share the same structure, that
is, the same coordinates and variable types. Each data table coincides with a
table in the SQLite database. One or more *Variables* can be defined from each
data table, representing symbolic objects arranged according to different shapes
used in mathematical expressions.

*Data Tables* and *Variables* are defined according to the structure below (here
reported in YAML format, but the same logic applies to the Excel file).


.. rubric:: Notation

Names written in ``<...>`` are placeholders to be replaced by user-defined
keys or values. Names written literally, such as ``description``, ``type``,
``coordinates`` or ``variables_info``, are field keys and should be kept
unchanged.


.. tabs::

  .. group-tab:: YAML

    File: ``structure_variables.yml``

    .. code-block:: yaml

        <table_key_#>:                         # user-defined table key
            description: <str>                 # optional
            type: <str | dict[str, str]>
                <problem_key_#>: <str>, ...    # optional, for hybrid Data Tables only

            integer: <bool>                    # optional
            coordinates: <str | list[str]>
            variables_info:

                <variable_key_#>:              # user-defined variable key
                    value: <str>               # optional
                    blank_fill: <int|float>    # optional
                    nonneg: <bool>             # optional
                    <set_key_#>:               # optional, user-defined set key
                        dim: <str>
                        filters:
                            <filter_key_#>: [<str>, <str>, ...]
                            ...
                    ...
                ...
        ...

  .. group-tab:: XLSX

    File: ``settings.xlsx`` | tab ``structure_variables``

    .. list-table::
        :header-rows: 1
        :align: center

        * - table_key
          - description
          - type
          - integer
          - coordinates
          - variables_info
          - value
          - blank_fill
          - nonneg
          - <set_key_#>
          - ...
        * - <table_key_#>
          - <str>
          - <str> | <problem_key_#>: <str>, ...
          - <bool>
          - <str>, <str>, ...
          - <str>
          - <str>
          - <int | float>
          - <bool>
          - dim: <str>, filters: {<filter_key_#>: [<str>, <str>, ...], ...}
          - ...
        * - ...
          - ...
          - ...
          - ...
          - ...
          - ...
          - ...
          - ...
          - ...
          - ...
          - ...


.. rubric:: Fields description

``<table_key_#>``: (required) user-defined key of the Data Table. This
placeholder must be replaced with the actual table key used as the table key
in the SQLite database. Since SQLite data tables are case-insensitive, this
key is *case-insensitive* too.

- ``description``: (optional) information about the data table.
- ``type``: (required) type of the data table. It can be *endogenous*, *exogenous*,
  *constant*, or a dictionary mapping problem keys to types for integrated
  problems (in this case, variables are defined as *hybrid* type).
- ``integer``: (optional) if *true*, variables in the table are integer-valued.
- ``coordinates``: (required) list of Set keys defining the dimensions of the 
  Data Table.
- ``variables_info``: dictionary defining Variables keys and related properties. 
  Each key is a user-defined variable key, and the corresponding value is a dictionary 
  including the following properties:

  - ``<variable_key_#>``: (required) user-defined variable key. This is the only 
    required field for each variable, and it is used as the variable key in 
    mathematical expressions.
    
    - ``value``: (optional) for *constants* types only, identifies the constant 
      value assigned to the variable. Full list of built-in constants and instructions 
      on how to define custom constants are documented in :ref:`api_constants_types`.
    - ``blank_fill``: (optional) for *exogenous* variables only, the value used to 
      fill blanks in SQLite Data Tables in case of missing values. 
    - ``nonneg``: (optional) for *endogenous* variables only, indicates whether the 
      variable is constrained to be non-negative.
    - ``<set_key_#>``: (optional) key of a Set included within the Data Table 
      coordinates, for which the following information are provided to define how 
      that set is shaping the variable, and if and how it is filtered. 
      In case a Set belonging to the Data Table coordinates is not included in the 
      variable definition below, if these is is not an inter-problem sets, it is 
      assigned as an intra-problem dimension by default.
      
      - ``dim``: (required) dimension assigned to the set. It can be *row* for rows, 
        *col* for columns, or *intra* for intra-problem indexing (implying that the 
        variable will be defined as many times as the cardinality of intra-problem Sets).
      - ``filters``: (optional) dictionary used to filter Data Tables for generating 
        variables. Each key is a filter key (defined in the ``filters`` fields of 
        the :ref:`sets_definition` section), and the corresponding value is 
        a list of values defining the filters categories to be filtered.


.. admonition:: About ``nonneg`` field

  The ``nonneg`` field is used to indicate whether an endogenous variable is 
  expected to be non-negative. This will result in an implicit non-negativity 
  constraint defined in the model. 
  In case of a *single numerical problem*, if ``nonneg=True`` an implicit 
  non-negativity expression is added to the problem.
  In case of *integrated numerical problems*:

  - For *hybrid variables* type, the non negativity constraints are added to 
    the problem where the variable is defined as endogenous. This is also useful 
    to ensure that the variable is used with the correct sign in the problem where 
    it is defined as endogenous, avoiding numerical inconsistencies during model 
    solving.
  - For *pure endogenous variables*, the non negativity constraints are added 
    only if the variable is used in any other problem expressions. In case the 
    variable is not used in any expression, an error is raised (constraints must 
    be explicitly defined in symbolic problem).  


Problem and Expressions
-----------------------

Problems are defined in ``problem.yml`` or in the ``problem`` tab of
``model_settings.xlsx``. Each problem key can include an objective and a list of
symbolic expressions, hence representing both a system of equations or a system of 
inequalities with a related objective function.


.. rubric:: Notation

Names written in ``<...>`` are placeholders to be replaced by user-defined
keys or values. Names written literally, such as ``objective``, are field keys 
and should be kept unchanged.


.. tabs::

  .. group-tab:: YAML

    File: ``problem.yml``

    .. code-block:: yaml

        <problem_key_#>:              # optional, user-defined problem key
            objective: <str>          # optional
            expressions: [<str>, <str>, ...]
        
        ...

  .. group-tab:: XLSX

    File: ``settings.xlsx`` | tab ``problem``

    .. list-table::
        :header-rows: 1
        :align: center

        * - problem_key
          - objective
          - expressions
        * - <problem_key_#>
          - <str>
          - <str>
        * - ...
          - ...
          - ...


.. rubric:: Fields description

``<problem_key_#>``: (optional) user-defined problem key. This can be omitted 
in case of one single problem.

- ``objective``: (optional) symbolic expression defining the problem objective. 
  If omitted, the problem is considered a system of equations or inequalities 
  without an objective function. Each problem can have up to one Objective. 
- ``expressions``: (required) list of symbolic expressions defining the problem
  constraints. 
    
Both objective and expressions are strings that can include variable keys and 
built-in or user-defined operators (see :ref:`api_symbolic_operators`).

Objective and Expressions are defined as literal strings, calling variables by 
their *variable keys*, and allowed or user-defined :ref:`operators 
<api_symbolic_operators>`.

In case the objective includes variables defined over *multiple intra-problem sets*, 
the objective is automatically aggregated over the dimensions of the intra-problem 
sets. For example, if variable *cost* is defined over time, defined as intra-problem 
sets *t*, the generated CVXPY expressions will be a number equal to to the number 
of time steps. CVXlab handle this automatically by defining the objective as 
the *summation of the objective over the intra-problem dimensions*. 


Final notes
-----------

- The *unused fields* in the setup file(s) can be either left blank or omitted.
  For example, in case of *Inter-problem sets*, only two fields are needed: 
  ``<set_name>_Name``, ``<set_name>_split_problem``.
  
