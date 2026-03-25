.. _fill-model-setup-files:

Fill model setup file(s)
========================

This page provides a guide on the structure and meaning of CVXlab Model settings.


Introduction
------------

Model setup file(s) represent the essential settings required to translate the 
conceptual model (see :ref:`conceptual-model-definition` step) from a mathematical 
formulation into a *CVXlab Model class instance*. 

The setup files define the structure of fundamental CVXlab objects, including 
*sets*, *data tables (with related variables)*, and *mathematical problem (with 
related expressions)*. 

The structure of these files is defined in the 
:py:attr:`default module <cvxlab.defaults.Defaults.DefaultStructures>`

Once the model directory has been generated (see :ref:`generation-of-model-directory` 
step), the setup files available in the model directory, provided in either 
*YAML* format (as three separate files) or *Excel* format (one file with three tabs).

- **Structure of sets**: defined in ``structure_sets.yml`` or ``structure_sets`` tab. 
  Sets define the model's dimensions and subproblem structure.
- **Structure of data tables and variables**: defined in ``structure_variables.yml``
  or ``structure_variables`` tab. Data tables represent collections of data 
  that shares the same structure (i.e., same coordinates and variable types). 
  Multiple variables can be defined within the same data table, and each variable 
  can represent a portion of the related data table and can be arrange in 
  different shapes.
- **Mathematical problem**: defined in ``problem.yml`` or ``problem`` tab. 
  One or multiple mathematical problems can be defined for a same Model isnstance,
  each with its own expressions list (equalities, inequalities, and objective). 
  Different mathematical problems refers to the same sets, data tables and 
  variables.


Optionally, template files for user-defined symbolic operators and constants can be
included in the model directory if requested during the directory generation step:

- :ref:`user_defined_operators.py <api_user_defined_operators>`: Template for 
  custom symbolic operators.
- :ref:`user_defined_constants.py <api_user_defined_constants>`: Template for 
  custom constants types.


.. _sets_definition:

Sets
----

*Sets* define the *dimensions* of the model according to the following structure 
(here reported in *YAML format*, but the same structure applies to the Excel file):

..  code-block:: yaml

    set_key: <str>                      
        description: <str>              # optional
        split_problem: <bool>           # optional
        copy_from: <str>                # optional
        filters:                        # optional
            <filter_name>: [<values>]
            ...
        aggregations: [<int|str>]    # optional


Fields description:

- **set_key**: Name of the set, used as the name in the SQLite data table. 
  Case-insensitive (e.g., 'e' and 'E' are the same set). This is the only 
  required field. Multiple sets can be defined within the same settings file.
- **description**: (Optional) Sets metadata provided by the modeler.
- **split_problem**: (Optional) If *true*, the set items define independent 
  numerical sub-problems (i.e. the set is classified as inter-problem set). 
  If more sets are defined, the number of sub-problems is the product of the 
  items of the sets.
- **copy_from**: (Optional) Key of another set to copy the data from. If defined, 
  the set copies data from the referenced set, and related data need not be 
  provided in the sets Excel file generated in following phase.
- **filters**: (Optional) Dictionary with keys as filter names and values as 
  lists of filter values. Used to identify sub-sets of data tables for generating 
  variables.
- **aggregations**: (Optional) List of set aggregations keys for data visualization. 
  Not used in numerical problem operations, but useful for reporting and visualization
  when the database is explored (e.g. with Business Intelligence tools).

Notice that at this stage the modeler only defines the structure of the sets, 
while the actual set items (i.e., the elements belonging to each set, here defined 
as *coordinates*) are defined in the sets Excel file generated after Model class 
instance is generated (see :ref:`fill-sets-data` step).

With reference to the example of the energy system model provided in the 
:ref:`conceptual-model-definition` section, sets are defined as follows 
(still assuming YAML format):

..  code-block:: yaml

    Demand_scenarios:
        description: "demand levels corresponding to different scenarios"
        split_problem: true

    Technologies:
        description: "technologies available in the system"
    
    Time_periods:
        description: "time periods considered in the model"

As it can be inferred from the example above, this simple energy system model 
includes three sets: *Demand_scenarios*, *Technologies*, and *Time_periods*. 
The *Demand_scenarios* set is defined as an inter-problem set, meaning that the 
numerical model will be run and solved for the number of demand scenarios
defined in the sets Excel file. The other two sets are defined as *dimensions set*, 
defining how variables will be arranged into rows and columns and indexed across 
intra-problem coordinates.

Note that other fields are not defined in the example above, due to the simplicity 
of the model. For instance, no *filters* are defined, meaning that all variables 
will be generated with the same structure (i.e., with sets all defined by the same 
coordinates, without filtering them).


.. _data_tables_variables_definition:

Data Tables and Variables
-------------------------

*Data Tables* represent collections of data that shares the same structure 
(i.e., same coordinates and variable types). Each Data Table coincides with a 
table in the SQLite database. One or more *Variables* can be defined from each 
Data Table, representing symbolic objects defined according to different shapes 
used in defining mathematical expressions. 

Data tables and variables are defined according to the following structure (here 
reported in *YAML format*, but the same structure applies to the Excel file):

..  code-block:: yaml

    table_key: <str>
        description: <str>                  # optional
        type: <str|dict>
            problem_key: <str>              # optional, for hybrid tables
            ...
        integer: <bool>                     # optional
        coordinates: <str|list>
        variable_info: <str>
            variable_key: <str>
                value: <str>                # optional
                blank_fill: <int|float>     # optional
                nonneg: <bool>              # optional
                set_key: <str>              # optional
                    dim: <str>
                    filters: 
                        filter_key: [<values>]
                        ...
                ...
            ...
        ...

Fields description:

- **table_key**: Name of the Data Table, used as the table name in the SQLite 
  database. Attention: since SQLite table naming is case-insensitive, this field 
  is also *case-insensitive*. Required.
- **description**: (Optional) Information about the Data Table.
- **type**: Type of the Data Table. Can be one of *endogenous*, *exogenous*, 
  *constant*, or a dictionary mapping problem keys to types (for integrated 
  problems). Required.
- **integer**: (Optional) If *true*, variables in the table are integer-valued 
  (default: False).
- **coordinates**: List of set_key symbols defining the dimensions of the Data 
  Table. Required.
- **variables_info**: Dictionary of variable definitions. Each key is a variable 
  name (case-insensitive), and the value is a dictionary with the following optional 
  fields:
  
  - **value**: (Optional, *for constants only*) The constant value assigned to 
    the variable. See :ref:`api_constants_types` for supported constant types.
  - **blank_fill**: (Optional, *for exogenous variables only*) Value used to 
    fill blanks or NaNs in the SQLite database.
  - **nonneg**: (Optional, *for endogenous variables only*) If *true*, the variable 
    is constrained to be non-negative (more on this in 
    :py:attr:`default module <cvxlab.defaults.Defaults.DefaultStructures>`)
  - **set_key**: (Optional) Set key (included in *coordinates* field) defining 
    variable shape and eventual filtering. Defined as a dictionary with the 
    following optional fields:
    
    - **dim**: (Optional) Dimension key on which the variable is assigned: *rows*, 
      *cols* or *intra* are allowed.
    - **filters**: (Optional) Dictionary with filter names as keys and lists of 
      filter values as values (both defined in :ref:`sets_definition`). This is 
      used to define sub-domains for the coordinate defined by the set key.


With reference to the example of the energy system model provided in the 
:ref:`conceptual-model-definition` section, Data Tables and related Variables are 
defined as follows (still assuming YAML format):

.. code-block:: yaml

    cost:
        description: Specific costs of generation by cost scenario and technology (in €/MWh)
        type: exogenous
        coordinates: [Technologies]
        variables_info:            
            c:
                technology:
                    dim: cols
    capacity:
        description: Installed capacity by technology and time period (in MW)
        type: exogenous
        coordinates: [Technologies, Time_periods]
        variables_info:            
            cap:
                technology:
                    dim: cols
                time_period:
                    dim: intra
    availability:
        description: Availability factors by technology (in MWh/MW)
        type: exogenous
        coordinates: [Technologies]
        variables_info:            
            av:
                technology:
                    dim: cols
    demand:
        description: Energy demand defined by demand scenarios and time periods (in MWh)
        type: exogenous
        coordinates: [Demand_scenarios, Time_periods]
        variables_info:            
            E_d:
                time_period:
                    dim: intra
    Supply:
        description: Energy supply (in MWh)
        type: endogenous
        coordinates: [Demand_scenarios, Technologies, Time_periods]
        variables_info:            
            E_s:
                technology:
                    dim: cols
                time_period:
                    dim: intra
    Constant:
        description: Model constants
        type: constant
        coordinates: [Technologies]
        variables_info:            
            i_t:
                value: sum_vector
                technology:
                    dim: rows

# CONTINUARE QUI

Problem and Expressions
-----------------------
The problem section defines objectives and constraints. Each problem includes:



Field Reference and Best Practices
----------------------------------
- Use field names as defined in ``Defaults.Labels`` for consistency.
- Keys are case-insensitive for sets and tables.
- For hybrid variables/data tables, use explicit mapping by problem.
- Required fields must be present; optional fields can be omitted.
- See ``cvxlab/defaults.py`` for authoritative field definitions.

Where to Find Examples
----------------------
Full examples of setup files in both YAML and Excel formats are provided in the Tutorials section and in the ``tests/integration/fixtures`` directory.

Further Reading
---------------
- :ref:`API Reference <api-reference>`
- :ref:`Tutorials <tutorials>`
- :ref:`Templates <templates>`
- ``cvxlab/defaults.py`` for code-level details


