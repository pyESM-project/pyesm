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
problems (with related expressions)*.

The structure of these files is defined in the
:py:attr:`default module <cvxlab.defaults.Defaults.DefaultStructures>`.

Once the model directory has been generated
(see :ref:`generation-of-model-directory`), the setup information is provided in
either:

- *YAML* format, as three separate files.
- *Excel* format, as one workbook with three tabs.

The setup files are:

- **Structure of sets**: defined in ``structure_sets.yml`` or the
  ``structure_sets`` tab.
- **Structure of data tables and variables**: defined in
  ``structure_variables.yml`` or the ``structure_variables`` tab.
- **Mathematical problem**: defined in ``problem.yml`` or the ``problem`` tab.

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

.. code-block:: yaml

    set_key: <str>
        description: <str>              # optional
        split_problem: <bool>           # optional
        copy_from: <str>                # optional
        filters:                        # optional
            <filter_name>: [<values>]
            ...
        aggregations: [<int|str>]       # optional


**Fields description**

- **set_key**: name of the set, used as the name in the SQLite data table.
  Case-insensitive. This is the only required field.
- **description**: optional metadata provided by the modeler.
- **split_problem**: if *true*, set items define independent numerical
  sub-problems. Such a set is classified as an inter-problem set.
- **copy_from**: key of another set to copy data from. If defined, related data
  need not be provided again in the sets workbook generated in a following step.
- **filters**: dictionary used to identify sub-sets of data tables for
  generating variables.
- **aggregations**: list of aggregation keys used for reporting and
  visualization. These are not used in numerical problem operations.

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

*Data Tables* and *Variables* are defined according to the following structure (here
reported in YAML format, but the same logic applies to the Excel file):

.. code-block:: yaml

    table_key: <str>
        description: <str>                  # optional
        type: <str|dict>
            problem_key: <str>              # optional, for hybrid tables
            ...
        integer: <bool>                     # optional
        coordinates: <str|list>
        variables_info:
            variable_key:
                value: <str>                # optional
                blank_fill: <int|float>     # optional
                nonneg: <bool>              # optional
                set_key:                     # optional
                    dim: <str>
                    filters:
                        filter_key: [<values>]
                        ...
                ...
            ...


**Fields description**

- **table_key**: required field, with name of the Data Table. This is used as the 
  table name in the SQLite database. Since SQLite data tables are case-insensitive, 
  this field is *case-insensitive* too. 
- **description**: optional information about the data table.
- **type**: type of the data table. It can be *endogenous*, *exogenous*,
  *constant*, or a dictionary mapping problem keys to types for integrated
  problems (in this case, variables are defined as *hybrid* type).
- **integer**: if *true*, variables in the table are integer-valued.
- **coordinates**: list of set keys defining the dimensions of the data table.
- **variables_info**: dictionary of variable definitions. Each key is a variable
  name, and the corresponding value can include:

  - **value**: for constants only, the constant value assigned to the variable.
  - **blank_fill**: for exogenous variables only, the value used to fill blanks
    or NaNs.
  - **nonneg**: for endogenous variables only, whether the variable is
    constrained to be non-negative.
  - **set_key**: optional set-specific configuration defining how that set is
    assigned to rows, columns, or intra-problem indexing, and how it is filtered.


Problem and Expressions
-----------------------

Problems are defined in ``problem.yml`` or in the ``problem`` sheet of
``model_settings.xlsx``. Each problem key can include an objective and a list of
symbolic expressions, for example:

.. code-block:: yaml

    problem_key:
        objective:
            - Minimize(<expression>)
        expressions:
            - <constraint_1>
            - <constraint_2>

The exact symbolic syntax depends on the variables and operators defined in the
model. Built-in operators are documented in :ref:`api_symbolic_operators`.



Field Reference and Best Practices
----------------------------------

- Use field names as defined in ``Defaults.Labels`` for consistency.
- Keys are case-insensitive for sets and tables.
- For hybrid variables and data tables, use explicit mapping by problem.
- Required fields must be present; optional fields can be omitted.
- See ``cvxlab/defaults.py`` for authoritative field definitions.


Where to Find Examples
----------------------

Worked examples of this structure are provided in the :ref:`tutorials` section
and in the ``tests/integration/fixtures`` directory.


Further Reading
---------------

- :ref:`API Reference <api-reference>`
- :ref:`Tutorials <tutorials>`
- :ref:`Templates <templates>`
- ``cvxlab/defaults.py`` for code-level details
