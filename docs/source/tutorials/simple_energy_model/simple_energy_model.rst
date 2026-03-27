.. _tutorial-simplified-energy-system:

Simplified energy system model
==============================

This tutorial illustrates, step by step, how to build a simple energy system
planning model with CVXlab. The objective is to determine the least-cost energy
production plan that satisfies demand over multiple time periods under different
demand scenarios.

The tutorial mirrors the workflow described in
:ref:`model generation from scratch <model_generation_from_scratch>`. Each step
applies the same energy system example, so that the transition from conceptual
design to numerical solution stays visible throughout the documentation.

The model includes:

- One inter-problem set for demand scenarios.
- Two dimension sets for technologies and time periods.
- Exogenous data tables for costs, capacities, availabilities, and demand.
- One endogenous data table for energy supply.
- One linear optimization problem solved independently for each scenario.


.. _simple-tutorial-conceptual-model-definition:

Step 1. Conceptual model definition
-----------------------------------

Related user guide step: :ref:`conceptual-model-definition`

This tutorial uses a simple energy system planning model. The first step in the
CVXlab modeling workflow consists in the definition of the
:ref:`conceptual model <conceptual-model-definition>`, consisting in the
identification of model sets, data tables, variables, and mathematical
expressions.


Problem statement
~~~~~~~~~~~~~~~~~

The goal is to determine the least-cost energy production plan for one region
over a finite planning horizon. Demand is assumed to be known and defined for
different scenarios. Energy can be supplied by multiple technologies, each
characterized by specific production costs, installed capacities, and
availability factors. Installed capacity varies over time, while costs and
availabilities are assumed to be fixed.


Main modeling objects
~~~~~~~~~~~~~~~~~~~~~

The example is built around the following conceptual objects.

.. list-table:: Main objects of the tutorial model
  :header-rows: 1

  * - Category
    - Objects
    - Role in the model
  * - Sets
    - :math:`d`, :math:`t`, :math:`y`
    - Define scenarios, technologies, and time periods
  * - Exogenous data tables
    - :math:`cost(t)`, :math:`capacity(t,y)`, :math:`availability(t)`, :math:`demand(d,y)`
    - Provide the input data of the optimization problem
  * - Endogenous data tables
    - :math:`supply(d,y,t)`
    - Store the decision variables solved by the model
  * - Constants
    - :math:`constant(t)`
    - Provide symbolic helper objects such as summation vectors
  * - Variables
    - :math:`c`, :math:`cap`, :math:`av`, :math:`E_d`, :math:`E_s`, :math:`i_t`
    - Define the symbolic representation used in expressions

The detailed definition of set coordinates is reported in
:ref:`simple-tutorial-fill-sets-data`. The translation of these objects into
CVXlab setup files is reported in
:ref:`simple-tutorial-fill-model-setup-files`.


Symbolic problem
~~~~~~~~~~~~~~~~

For this tutorial, the symbolic optimization problem can be written as:

.. math::
  \begin{aligned}
  \min_{E_s} \quad & c \cdot E_s' & \forall \, y\\
  \text{s.t.} \quad & E_s \cdot i_t \geq E_d & \forall \, y \\
  & E_s \leq cap \cdot \widehat{av} & \forall \, y \\
  & E_s \geq 0 & \forall \, y
  \end{aligned}

where:

- :math:`E_s` is the energy supply by technology and time period.
- :math:`E_d` is the scalar demand for each scenario and time period.
- :math:`c` is the vector of specific production costs.
- :math:`cap` is the vector of installed capacities for each time period.
- :math:`av` is the vector of technology availability factors.
- :math:`i_t` is a summation vector used to aggregate supply across
  technologies.

At this conceptual stage, it is enough to understand that the model is linear,
convex, and separable across demand scenarios.


How scenarios and expression instances are generated
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The tutorial distinguishes between:

- **Inter-problem sets**: define how many independent numerical problems are
  created. In this example, the demand-scenario set :math:`d` generates one
  problem instance per scenario.
- **Dimension sets**: define the internal shape of variables. In this example,
  :math:`t` and :math:`y` define technologies and time periods.

As a consequence:

- The full optimization problem is generated once for each demand scenario.
- Each symbolic expression is expanded over the intra-problem set :math:`y`,
  producing one numerical expression per time period.
- Variables not indexed over a specific intra-problem set are automatically
  reused across the generated numerical expressions.


Alternative dimensional formulations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In this tutorial, the matrix-based formulation is used because it offers a
compact representation of the problem while keeping the model easy to map into
CVXlab structures.

The allocation of dimension sets to shapes and intra-problem sets offers
significant modeling flexibility. The same optimization problem can be written
in multiple equivalent ways.


.. _simple-tutorial-model-directory-generation:

Step 2. Generate the model directory
------------------------------------

Related user guide step: :ref:`generation-of-model-directory`

At this stage the conceptual model is already defined. The next step is to
create a model directory that will contain the setup files, the sets workbook,
the input-data files, and the SQLite database of the tutorial model.


Recommended command
~~~~~~~~~~~~~~~~~~~

For this tutorial, a compact Excel-based workflow is convenient because all
setup information can be stored in a single workbook.

.. code-block:: python

    import cvxlab

    cvxlab.create_model_dir(
        model_dir_name="simple_energy_model",
        main_dir_path="path/to/tutorial_workspace",
        settings_file_type="xlsx",
        include_user_defined_templates=False,
    )


What this generates
~~~~~~~~~~~~~~~~~~~

For the simple energy system model, this step typically creates:

- A model directory named ``simple_energy_model``.
- A ``model_settings.xlsx`` workbook with sheets for sets, variables, and
  problems.
- The directory structure expected by the following tutorial steps.

If you prefer YAML files instead of Excel, the same tutorial structure still
applies. Only the format of the setup files changes.


.. _simple-tutorial-fill-model-setup-files:

Step 3. Fill the model setup files
----------------------------------

Related user guide step: :ref:`fill-model-setup-files`

In this step, the conceptual structure of the energy system model is translated
into CVXlab setup files. The same information can be written either in
``model_settings.xlsx`` or in the YAML files generated by
:py:func:`cvxlab.create_model_dir`.


Sets structure
~~~~~~~~~~~~~~

For the tutorial model, the three sets can be represented as follows in YAML:

.. code-block:: yaml

    Demand_scenarios:
        description: demand levels corresponding to different scenarios
        split_problem: true

    Technologies:
        description: technologies available in the system

    Time_periods:
        description: time periods considered in the model

The ``Demand_scenarios`` set is marked with ``split_problem: true`` because the
model must be solved independently for each scenario. The other two sets define
the internal dimensions of variables.


Data tables and variables
~~~~~~~~~~~~~~~~~~~~~~~~~

The structural definition of data tables and variables can be organized as
follows:

.. code-block:: yaml

    cost:
        description: specific generation costs by technology (EUR/MWh)
        type: exogenous
        coordinates: [Technologies]
        variables_info:
            c:
                Technologies:
                    dim: cols

    capacity:
        description: installed capacity by technology and time period (MW)
        type: exogenous
        coordinates: [Technologies, Time_periods]
        variables_info:
            cap:
                Technologies:
                    dim: cols
                Time_periods:
                    dim: intra

    availability:
        description: availability factors by technology (MWh/MW)
        type: exogenous
        coordinates: [Technologies]
        variables_info:
            av:
                Technologies:
                    dim: cols

    demand:
        description: energy demand by scenario and time period (MWh)
        type: exogenous
        coordinates: [Demand_scenarios, Time_periods]
        variables_info:
            E_d:
                Time_periods:
                    dim: intra

    supply:
        description: energy supply by scenario, technology, and time period (MWh)
        type: endogenous
        coordinates: [Demand_scenarios, Technologies, Time_periods]
        variables_info:
            E_s:
                Technologies:
                    dim: cols
                Time_periods:
                    dim: intra

    constant:
        description: model constants
        type: constant
        coordinates: [Technologies]
        variables_info:
            i_t:
                value: sum_vector
                Technologies:
                    dim: rows

The resulting symbolic variables are summarized below.

.. list-table:: Variables used in the tutorial model
  :header-rows: 1

  * - Related data table
    - Variable
    - Shape
    - Intra-problem sets
    - Inter-problem sets
  * - :math:`cost(t)`
    - :math:`c`
    - :math:`1 \times t`
    - :math:`-`
    - :math:`-`
  * - :math:`capacity(t,y)`
    - :math:`cap`
    - :math:`1 \times t`
    - :math:`y`
    - :math:`-`
  * - :math:`availability(t)`
    - :math:`av`
    - :math:`1 \times t`
    - :math:`-`
    - :math:`-`
  * - :math:`demand(d,y)`
    - :math:`E_d`
    - :math:`1 \times 1`
    - :math:`y`
    - :math:`d`
  * - :math:`supply(d,y,t)`
    - :math:`E_s`
    - :math:`1 \times t`
    - :math:`y`
    - :math:`d`
  * - :math:`constant(t)`
    - :math:`i_t`
    - :math:`t \times 1`
    - :math:`-`
    - :math:`-`


Problem definition
~~~~~~~~~~~~~~~~~~

The optimization problem can be represented in ``problem.yml`` as:

.. code-block:: yaml

    energy_system:
        objective:
            - Minimize(c @ tran(E_s))
        expressions:
            - E_s @ i_t >= E_d
            - E_s <= cap @ diag(av)
            - E_s >= 0

This structure keeps the tutorial aligned with the conceptual formulation
introduced in :ref:`simple-tutorial-conceptual-model-definition`.


.. _simple-tutorial-generate-model-instance:

Step 4. Generate the Model instance
-----------------------------------

Related user guide step: :ref:`generate-model-class-instance`

Once the setup files are filled, the tutorial model can be loaded into a CVXlab
``Model`` instance. This object will then be used for all remaining steps.


Typical initialization
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import cvxlab

    model = cvxlab.Model(
        model_dir_name="simple_energy_model",
        main_dir_path="path/to/tutorial_workspace",
        model_settings_from="xlsx",
        use_existing_data=False,
    )


What to expect
~~~~~~~~~~~~~~

At this point CVXlab validates the structure of:

- The three sets of the tutorial model.
- The exogenous, endogenous, and constant data tables.
- The symbolic variables associated with those tables.
- The problem definition stored in the setup files.

If validation succeeds, the model directory is ready for the next operational
step. In a workflow from scratch, the most important generated artifact is the
``sets.xlsx`` file, which is filled in the next step of this tutorial.


.. _simple-tutorial-fill-sets-data:

Step 5. Fill the sets workbook
------------------------------

Related user guide step: :ref:`fill-sets-data`

After the ``Model`` instance is created, CVXlab generates a workbook for the
set coordinates. For the simple energy system model, the coordinates are the
actual items over which scenarios, technologies, and time periods are defined.


Coordinates of the tutorial model
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Sets of the simple energy system model
  :header-rows: 1

  * - Set name
    - Symbol
    - Coordinates
    - Cardinality
    - Set type
  * - Technologies
    - :math:`t`
    - Solar, Gas, Nuclear
    - 3
    - Dimension
  * - Time periods
    - :math:`y`
    - 2025, 2026, 2027, 2028, 2029, 2030
    - 6
    - Dimension
  * - Demand scenarios
    - :math:`d`
    - Low_demand, High_demand
    - 2
    - Inter-problem


How these coordinates are used
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- The demand-scenario coordinates create two independent problem instances.
- The technology coordinates define the columns of the main decision variable.
- The time-period coordinates define the intra-problem expansion of the
  expressions.

No filters are required for this first tutorial model, so all variables are
defined on full domains.


.. _simple-tutorial-data-structures-init:

Step 6. Initialize the data structures
--------------------------------------

Related user guide step: :ref:`data-structures-init`

Once the set coordinates are available, CVXlab can generate the underlying data
structures required by the tutorial model.


Typical command
~~~~~~~~~~~~~~~

.. code-block:: python

    model.initialize_model_environment()


What this prepares for the tutorial
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For the simple energy system model, this step:

- Loads the set coordinates into the model index.
- Assigns coordinates and dimensions to the tables ``cost``, ``capacity``,
  ``availability``, ``demand``, ``supply``, and ``constant``.
- Creates a blank SQLite database with normalized tables.
- Generates blank input-data file(s) for the exogenous tables that will be
  filled in the next step.

After this step, the model structure is complete and ready to receive numerical
input data.


.. _simple-tutorial-fill-exogenous-data:

Step 7. Fill the exogenous data
-------------------------------

Related user guide step: :ref:`fill-exogenous-data`

The blank input-data files generated by CVXlab must now be populated with the
exogenous data of the tutorial model. Only exogenous tables are filled by the
user at this stage.


Input tables to populate
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table:: Exogenous data tables of the tutorial model
  :header-rows: 1

  * - Data table
    - Domain
    - Description
  * - :math:`cost(t)`
    - :math:`t`
    - Specific generation costs by technology in EUR/MWh
  * - :math:`capacity(t,y)`
    - :math:`t \times y`
    - Installed capacity by technology and time period in MW
  * - :math:`availability(t)`
    - :math:`t`
    - Availability factor by technology in MWh/MW
  * - :math:`demand(d,y)`
    - :math:`d \times y`
    - Energy demand by scenario and time period in MWh


Important distinction
~~~~~~~~~~~~~~~~~~~~~

- ``cost``, ``capacity``, ``availability``, and ``demand`` are filled by the
  user because they are exogenous inputs.
- ``supply`` is not filled manually because it is endogenous and will be solved
  by the optimizer.
- ``constant`` is not an external input table in the usual sense: it is defined
  structurally through the setup files and used to build symbolic expressions.


.. _simple-tutorial-numerical-problem-init:

Step 8. Initialize the numerical problem
----------------------------------------

Related user guide step: :ref:`numerical-problem-init`

At this point the symbolic model and the exogenous data are both available, so
CVXlab can generate the numerical optimization problem.


Typical command
~~~~~~~~~~~~~~~

.. code-block:: python

    model.refresh_database_and_initialize_problem()


Expressions generated for the tutorial
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The symbolic problem of the simple energy system model is:

.. math::
  \begin{aligned}
  \min_{E_s} \quad & c \cdot E_s' & \forall \, y\\
  \text{s.t.} \quad & E_s \cdot i_t \geq E_d & \forall \, y \\
  & E_s \leq cap \cdot \widehat{av} & \forall \, y \\
  & E_s \geq 0 & \forall \, y
  \end{aligned}

During initialization:

- One numerical problem is built for each demand scenario.
- One numerical expression instance is generated for each time period.
- Variables not indexed on ``Time_periods`` are broadcast across the generated
  expression instances.

The result of this step is a CVXPY-ready representation of the energy planning
problem for all scenarios of the tutorial model.


.. _simple-tutorial-numerical-problem-run:

Step 9. Solve the numerical problem
-----------------------------------

Related user guide step: :ref:`numerical-problem-run`

The energy system tutorial defines a standard convex optimization problem, so
the numerical problem can now be solved directly once initialization is
complete.


Typical command
~~~~~~~~~~~~~~~

.. code-block:: python

    model.run_model(
        integrated_problems=False,
        solver="ECOS",
    )


What happens in this tutorial
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- The model is solved independently for each demand scenario.
- For each scenario, the optimizer computes the least-cost feasible value of
  the endogenous supply variable :math:`E_s`.
- The solution covers all technologies and all time periods defined in the sets
  workbook.

Since this is a single linear optimization problem, no iterative decomposition
is required in the basic tutorial workflow.


.. _simple-tutorial-export-model-results:

Step 10. Export the results
---------------------------

Related user guide step: :ref:`export-model-results`

Once the optimization problem has been solved, the endogenous values can be
written back to the SQLite database for inspection and reporting.


Typical command
~~~~~~~~~~~~~~~

.. code-block:: python

    model.load_results_to_database()


Main result of the tutorial
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The key exported table is the endogenous supply table:

.. math::
  supply(d,y,t)

This table stores the optimal energy supplied by each technology, for each time
period, and for each demand scenario. After export, the results can be explored
through the CVXlab utilities, direct SQLite inspection, or downstream reporting
tools.



Practical example
-----------------

Let us consider a model with Set structure defined as below. Notice that it is 
possible to define Set structure in both the ``structure_sets.yml`` file, or in 
the ``structure_sets`` tab in the ``settings.xlsx`` Excel file. The following
tabs show the same Set structure in both formats.

.. tabs::

  .. tab:: YAML

    .. code-block:: yaml

        Scenarios:
            description: Scenarios analyzed in the model
            split_problem: True
        
        Technologies:
            description: Technologies included in the model
            filters:
                Type: [Supply, Demand, Storage]
                Category: [Renewable, Non-renewable]
            aggregations: [Sectors]

  .. tab:: XLSX (tab ``structure_sets``)

    .. list-table::
        :header-rows: 1
        :align: center

        * - set_key
          - description
          - split_problem
          - filters
          - aggregations
        * - Scenarios
          - Scenarios analyzed in the model
          - True
          -
          -
        * - Technologies
          - Technologies included in the model
          -
          - Type: [Supply, Demand, Storage], Category: [Renewable, Non-renewable]
          - Sectors


The tabs of ``sets.xlsx`` file are reported below. The header will be 
automatically generated based on the set definition, while the entries are defined 
by the user.


.. tabs::

    .. tab:: tab ``_set_SCENARIOS``

      .. list-table:: 
        :header-rows: 1
        :align: center

        * - Scenarios_Name
        * - Business As Usual
        * - Net Zero emissions
        * - Stated Policies

    .. tab:: tab ``_set_TECHNOLOGIES``

      .. list-table:: 
        :header-rows: 1
        :align: center

        * - Technologies_Name
          - Technologies_Type
          - Technologies_Category
          - Technologies_Sector
        * - Power by Coal
          - Supply
          - Non-renewable
          - Power sector
        * - Power by Solar
          - Supply
          - Renewable
          - Power sector
        * - Boiler
          - Supply
          - 
          - Heat sector
        * - Batteries
          - Storage
          - 
          - Power sector
        * - Households
          - Demand
          - 
          - Demand

In the example above, the unused fields in the structure file(s) have been omitted 
(e.g., ``copy_from`` for the all Sets).