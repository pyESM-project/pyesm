.. _tutorial-production-planning-nonlinear:

Handling non-linearities explicitly
===================================

This tutorial extends the :ref:`tutorial-production-planning` by illustrating how 
to handle a **non-linearity** in problems expressions explicitly. It is designed 
to be read *after* the base tutorial and focuses exclusively on the differences 
with respect to it: only the modified or new elements are described in detail, 
while unchanged steps are referenced to the base tutorial.

This short note highlights the minimal changes required when the base production 
planning model becomes non-linear but can still be solved by a non-linear solver 
without structural reformulation. If reformulation into coupled convex sub-problems 
is required, see the :ref:`tutorial-production-planning-decomposition` tutorial.

Use this guide when the non-linearity is supported by a nonlinear-capable solver 
available to CVXlab and no decomposition is necessary. Refer to CVXPY `Disciplined 
Non-Linear Programming (DNLP) <https://www.cvxpy.org/tutorial/dnlp/index.html>`__ 
documentation for understanding capabilities and supported solvers. 

.. _nonlinear-problem-statement:

.. admonition:: Problem statement

  The production system is the same as in the
  :ref:`base tutorial <tutorial-production-planning>`, with one key modification:
  the **unit profit of each product is no longer a fixed constant but increases with
  the production level** of that product (e.g., due to economies of scale):

  .. math::
    c_j(x_j) = c_{0,j} + c_{s,j} \cdot x_j, \qquad j \in \{product_1,\, product_2\}

  where :math:`c_{0,j}` is the initial unit profit and :math:`c_{s,j}` is the
  profit slope with respect to production. Numerical values are:

  .. math::
    \begin{array}{c|cc}
    & product_1 & product_2 \\
    \hline
      c_0 \; [\text{€/u}]      & 1.0    & 2.2    \\
      c_s \; [\text{€/u}^2]    & 0      & 0.005  \\
      e \; [\text{kWh/u}]      & 1.7    & 3.5    \\
      m \; [\text{kg/u}]       & 0.5    & 1.2
    \end{array}

  Positive slopes :math:`c_{s,j} > 0` represent **economies of scale**: the more 
  a product is sold, the higher its unit margin becomes (in the example, product 2 
  only exhibits this behavior). A linear relationship between profit and production 
  level is assumed, with :math:`c_{0,j}` representing the unit profit at zero 
  production and :math:`c_{s,j}` the increase in unit profit per additional unit 
  produced. Finally, the energy and material endowments remain:

  :math:`E = (250, 300)` kWh,  :math:`M = (60, 90)` kg.

In the :download:`zip directory <production_planning_nonlinear.zip>`, the same
materials as in the base tutorial are provided (notebook, concept workbook, and
model directory), updated for the non-linear variant.


Conceptual model definition
---------------------------

Related user guide step: :ref:`conceptual-model-definition`.

This section focuses mainly on the changes with respect to the base tutorial.

.. rubric:: Defining Sets

The *Attributes* set is updated to accommodate two separate profit-related
parameters. The coordinate ``profit`` is replaced by ``profit_initial`` and
``profit_slope``, bringing the cardinality from 3 to 4.

.. list-table:: Sets of the tutorial model (modified entries in bold)
   :header-rows: 1
   :widths: 20 10 45 10 15

   * - Set name
     - Symbol
     - Coordinates
     - Cardinality
     - Set type
   * - Products
     - :math:`p`
     - :math:`product_1`, :math:`product_2`
     - 2
     - Dimension set
   * - **Attributes** *(modified)*
     - :math:`a`
     - :math:`profit\_initial`,\ :math:`profit\_slope`,\ :math:`energy`,\ :math:`material`
     - **4**
     - Dimension set
   * - Scenarios_energy
     - :math:`e`
     - :math:`low`, :math:`high`
     - 2
     - Inter-problem set
   * - Scenarios_material
     - :math:`m`
     - :math:`low`, :math:`high`
     - 2
     - Inter-problem set

.. rubric:: Defining Data Tables and related Variables

Main changes in data tables definition include: the introduction of a new endogenous 
``profit`` table and the ``products_data`` domain grows by one attribute row, while 
all other tables are unchanged.

.. list-table:: Data Tables of the tutorial model (modified/new entries in bold)
   :header-rows: 1
   :widths: 22 20 25 33

   * - Name (sets domain)
     - Type
     - Domain [cardinality]
     - Description
   * - **production**
     - Endogenous
     - :math:`p \times e \times m \; [2 \times 2 \times 2 = 8]`
     - Total products output by scenario
   * - **profit** *(new)*
     - **Endogenous**
     - :math:`p \times e \times m \; [2 \times 2 \times 2 = 8]`
     - Unit profit by production level and scenario
   * - **products_data** *(modified)*
     - Exogenous
     - :math:`a \times p \; [4 \times 2 = 8]`
     - Product attributes: initial profit, profit slope, energy use, material use
   * - :math:`energy_{avail}(e)`
     - Exogenous
     - :math:`e \; [2]`
     - Energy availability scenarios (*kWh*)
   * - :math:`material_{avail}(m)`
     - Exogenous
     - :math:`m \; [2]`
     - Material availability scenarios (*kg*)

Variable :math:`c` migrates from ``products_data`` (exogenous, constant across
scenarios) to the new ``profit`` table (endogenous, scenario-dependent). Two new
exogenous variables, :math:`c_0` and :math:`c_s`, replace it in
``products_data``.

.. list-table:: Variables of the tutorial model (modified/new entries in bold)
   :header-rows: 1
   :widths: 15 10 15 13 17 30

   * - Source Data Table
     - Symbol
     - Shape [rows, cols]
     - Intra-problem sets
     - Inter-problem sets
     - Description
   * - **profit** *(new)*
     - :math:`c`
     - :math:`1,\, p \; [1,2]`
     - :math:`-`
     - :math:`e \times m \; [4]`
     - Unit profit per product (*€/unit*)
   * - **products_data** *(new)*
     - :math:`c_0`
     - :math:`1,\, p \; [1,2]`
     - :math:`-`
     - :math:`-`
     - Initial unit profit per product (*€/unit*)
   * - **products_data** *(new)*
     - :math:`c_s`
     - :math:`1,\, p \; [1,2]`
     - :math:`-`
     - :math:`-`
     - Profit slope per unit of production (*€/unit²*)
   * - production
     - :math:`x`
     - :math:`1,\, p \; [1,2]`
     - :math:`-`
     - :math:`e \times m \; [4]`
     - Products output (*unit*)
   * - products_data
     - :math:`e`
     - :math:`1,\, p \; [1,2]`
     - :math:`-`
     - :math:`-`
     - Specific energy use per product (*kWh/unit*)
   * - products_data
     - :math:`m`
     - :math:`1,\, p \; [1,2]`
     - :math:`-`
     - :math:`-`
     - Specific material use per product (*kg/unit*)
   * - :math:`energy_{avail}`
     - :math:`E`
     - :math:`1,\, 1`
     - :math:`-`
     - :math:`e \; [2]`
     - Energy endowment (*kWh*)
   * - :math:`material_{avail}`
     - :math:`M`
     - :math:`1,\, 1`
     - :math:`-`
     - :math:`m \; [2]`
     - Material endowment (*kg*)

.. rubric:: Defining Problems and related Expressions

The mathematical formulation of the problem is defined below.

.. math::
    \begin{aligned}
    \max \quad & (c \cdot x') \\
    \text{s.t.} \quad & e \cdot x' - E \leq 0 \\
    & m \cdot x' - M \leq 0 \\
    & c - c_s \cdot \mathrm{diag}(x) - c_0 = 0 \\
    & x \geq 0
    \end{aligned}

Unit profit :math:`c_j` becomes a function of the production level :math:`x_j`: 
since unit profit and production level are multiplied in the objective function, 
the latter becomes non-linear (non-convex).

Notice that:

- The ``diag()`` built-in operator constructs a diagonal matrix from a row
  vector, so that :math:`c_s \cdot \mathrm{diag}(x)` evaluates to the
  element-wise product :math:`c_s \odot x` (see :ref:`api_symbolic_operators`).


Generation of model directory
------------------------------

| Related user guide step: :ref:`generation-of-model-directory`
| Related API: :py:func:`cvxlab.create_model_dir`

This step is **identical** to the base tutorial. Refer to the corresponding
section of :ref:`tutorial-production-planning` for details.


Fill model setup file(s)
-------------------------

Related user guide step: :ref:`fill-model-setup-files`

Only the modified or new parts of the setup files are shown below.

.. rubric:: Modified sets definition

The only change in ``structure_sets.yml`` (or the ``structure_sets`` tab) is
the updated filter list of the *Attributes* set.

.. tabs::

   .. group-tab:: YAML

      File: ``structure_sets.yml``

      .. code-block:: yaml

         Attributes:
             description: attributes of the products | dimension set
             filters:
                 type: [profit_initial, profit_slope, energy, material]

   .. group-tab:: XLSX

      File: ``model_settings.xlsx`` | tab ``structure_sets``

      .. list-table::
         :header-rows: 1
         :align: center

         * - set_key
           - description
           - split_problem
           - filters
         * - Attributes
           - attributes of the products | dimension set
           -
           - type: [profit_initial, profit_slope, energy, material]

   All other set definitions are unchanged.

.. rubric:: Modified and new Data Tables and Variables

The full updated ``structure_variables.yml`` is shown below. The two hybrid
tables and the new variables are annotated with inline comments.

.. tabs::

   .. group-tab:: YAML

      File: ``structure_variables.yml``

      .. code-block:: yaml

         production:
             description: products supply
             type: endogenous
             coordinates: [Products, Scenarios_energy, Scenarios_material]
             variables_info:
                 x:
                     Products:
                         dim: cols

         # NEW: hybrid profit data table
         profit:
             description: unit profit by production
             type: endogenous
             coordinates: [Products, Scenarios_energy, Scenarios_material]
             variables_info:
                 c:
                     Products:
                         dim: cols

         # MODIFIED: variable 'c' removed; 'c_0' and 'c_s' added
         products_data:
             description: attributes of products | profits, energy use, material use
             type: exogenous
             coordinates: [Products, Attributes]
             variables_info:
                 c_0:
                     Products:
                         dim: cols
                     Attributes:
                         dim: rows
                         filters: {type: profit_initial}
                 c_s:
                     Products:
                         dim: cols
                     Attributes:
                         dim: rows
                         filters: {type: profit_slope}
                 e:
                     Products:
                         dim: cols
                     Attributes:
                         dim: rows
                         filters: {type: energy}
                 m:
                     Products:
                         dim: cols
                     Attributes:
                         dim: rows
                         filters: {type: material}

         energy_avail:
             description: availability scenarios for energy
             type: exogenous
             coordinates: [Scenarios_energy]
             variables_info:
                 E:

         material_avail:
             description: availability scenarios for material
             type: exogenous
             coordinates: [Scenarios_material]
             variables_info:
                 M:

   .. group-tab:: XLSX

      File: ``model_settings.xlsx`` | tab ``structure_variables``

      .. list-table::
          :header-rows: 1
          :align: center

          * - table_key
            - description
            - type
            - coordinates
            - variables_info
            - Products
            - Attributes
          * - production
            - products supply
            - endogenous
            - Products, Scenarios_energy, Scenarios_material
            - x
            - dim: cols
            -
          * - profit
            - unit profit by production
            - endogenous
            - Products, Scenarios_energy, Scenarios_material
            - c
            - dim: cols
            -
          * - products_data
            - attributes of products | initial profit
            - exogenous
            - Products, Attributes
            - c_0
            - dim: cols
            - dim: rows, filters: {type: profit_initial}
          * - products_data
            - attributes of products | profit slope
            - exogenous
            - Products, Attributes
            - c_s
            - dim: cols
            - dim: rows, filters: {type: profit_slope}
          * - products_data
            - attributes of products | energy use
            - exogenous
            - Products, Attributes
            - e
            - dim: cols
            - dim: rows, filters: {type: energy}
          * - products_data
            - attributes of products | material use
            - exogenous
            - Products, Attributes
            - m
            - dim: cols
            - dim: rows, filters: {type: material}
          * - energy_avail
            - availability scenarios for energy
            - exogenous
            - Scenarios_energy
            - E
            -
            -
          * - material_avail
            - availability scenarios for material
            - exogenous
            - Scenarios_material
            - M
            -
            -


.. rubric:: Modified symbolic problem definition

In the problem formulation, an expression is added representing the dependancy of 
profit on production level, linking :math:`c` to :math:`c_0`, :math:`c_s`, and :math:`x`.

.. tabs::

   .. group-tab:: YAML

      File: ``problem.yml``

      .. code-block:: yaml

        objective:
          - Maximize(c @ tran(x))

        expressions:
          - e @ tran(x) - E <= 0
          - m @ tran(x) - M <= 0
          - c - c_s @ diag(x) - c_0 == 0
          - x >= 0

        description:
          - maximization of total profit
          - energy use less than endowment
          - material use less than endowment
          - unit profit as a function of product demand
          - positive products supply

   .. group-tab:: XLSX

      File: ``model_settings.xlsx`` | tab ``problem``

      .. list-table::
          :header-rows: 1
          :align: center

          * - objective
            - expressions
            - description
          * - Maximize(c @ tran(x))
            -
            - maximization of total profit
          * -
            - e @ tran(x) - E <= 0
            - energy use less than endowment
          * -
            - m @ tran(x) - M <= 0
            - material use less than endowment
          * -
            - c - c_s @ diag(x) - c_0 == 0
            - unit profit as a function of product demand
          * -
            - x >= 0
            - positive products supply

Notice that:

- Since one unique problem is defined, the problem key could even not be specified.
- The ``diag()`` built-in operator constructs a diagonal matrix from a
  row vector (see :ref:`api_symbolic_operators`).


Model class instance generation
---------------------------------

| Related user guide step: :ref:`generate-model-class-instance`
| Related class constructor: :py:class:`cvxlab.Model`

This step is **identical** to the base tutorial. Refer to the corresponding
section of :ref:`tutorial-production-planning` for details.


Fill sets data (model coordinates)
------------------------------------

Related user guide step: :ref:`fill-sets-data`

All set tabs in ``sets.xlsx`` are identical to the base tutorial with one
exception: the ``_set_ATTRIBUTES`` tab now contains **four rows** instead of
three, reflecting the updated filter structure.

.. list-table:: ``sets.xlsx`` file | tab ``_set_ATTRIBUTES``
   :header-rows: 1

   * - Attributes_Name
     - Attributes_type
   * - profit_initial
     - profit_initial
   * - profit_slope
     - profit_slope
   * - energy
     - energy
   * - material
     - material


Initialization of data structures
------------------------------------

| Related user guide step: :ref:`data-structures-init`
| Related API: :py:meth:`~cvxlab.Model.initialize_model_environment`

This step is **identical** to the base tutorial. Refer to the corresponding
section of :ref:`tutorial-production-planning` for details.

The ``products_data`` input data file tab will now contain **eight rows**
(four attributes × two products) instead of six, reflecting the new attribute
structure. Fill the additional ``profit_slope`` rows with the :math:`c_s`
coefficient values.


Fill exogenous model data
---------------------------

Related user guide step: :ref:`fill-exogenous-data`

The ``energy_avail`` and ``material_avail`` tabs are **unchanged**. The
``products_data`` tab now has **eight rows** due to the additional
``profit_initial`` and ``profit_slope`` attributes.

.. list-table:: ``input_data.xlsx`` file | tab ``products_data``
   :header-rows: 1

   * - id
     - Products_Name
     - Attributes_Name
     - values
   * - 1
     - product_1
     - profit_initial
     - 1.0
   * - 2
     - product_1
     - profit_slope
     - 0
   * - 3
     - product_1
     - energy
     - 1.7
   * - 4
     - product_1
     - material
     - 0.5
   * - 5
     - product_2
     - profit_initial
     - 2.2
   * - 6
     - product_2
     - profit_slope
     - 0.005
   * - 7
     - product_2
     - energy
     - 3.5
   * - 8
     - product_2
     - material
     - 1.2

Note that the ``profit`` data table is endogenous and therefore does **not**
appear in the input data file: its values are computed by CVXlab during the
solution process.


Initialization of numerical problem(s)
--------------------------------------

| Related user guide step: :ref:`numerical-problem-init`
| Related API: :py:meth:`~cvxlab.Model.refresh_database_and_initialize_problem`

This step is **identical** to the base tutorial. Refer to the corresponding
section of :ref:`tutorial-production-planning` for details.

CVXlab generates **eight** CVXPY problem instances in total: four scenario
instances for sub-problem ``production`` and four for sub-problem ``profit``,
corresponding to the Cartesian product of the energy and material sets
(:math:`2 \times 2 = 4` per sub-problem).


Solution of numerical problem(s)
--------------------------------

| Related user guide step: :ref:`numerical-problem-run`
| Related API: :py:meth:`~cvxlab.Model.run_model`

Problem solution is **identical** to the base tutorial, with one exception: since
the problem is now non-linear, a non-linear capable solver must be specified in the
``solver`` argument of ``run_model()``. The ``solver_settings`` dictionary must also
be specified with the ``nlp`` argument set to ``True`` to activate the non-linear
solver mode.

.. code-block:: python

  model.run_model(
    solver='IPOPT', # or any other nonlinear-capable solver available to CVXPY backend
    solver_settings={'nlp': True}, # must be specified for nonlinear problems
  )

Notice that:

- the `nlp` argument must be set to ``True`` in the ``solver_settings`` dictionary to
  activate the non-linear solver mode;
- a non-linear capable solver must be specified in the ``solver`` argument: check 
  CVXPY-compatible solvers for non-linear problems `here <https://www.cvxpy.org/tutorial/dnlp/index.html>`__ ;


Export endogenous model data
------------------------------

| Related user guide step: :ref:`export-model-results`
| Related API: :py:meth:`~cvxlab.Model.load_results_to_database`

The export step is **identical** to the base tutorial:

.. code-block:: python

   model.load_results_to_database()

After this step, the SQLite database ``database.db`` contains solved values in
**two** endogenous tables: ``production`` (values of :math:`x`) and ``profit``
(converged values of :math:`c`).

.. rubric:: Inspecting the exported results

After export, the SQLite database contains two endogenous tables: ``production``
(optimal output levels :math:`x`) and ``profit`` (converged unit profits
:math:`c`). Both tables are indexed over the four scenario combinations.