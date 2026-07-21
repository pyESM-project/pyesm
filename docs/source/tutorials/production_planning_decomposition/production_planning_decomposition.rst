.. _tutorial-production-planning-decomposition:

Non-linear problem decomposition
================================

This tutorial extends the :ref:`tutorial-production-planning` by illustrating how 
to handle a **non-linearity** in problems expressions. It is designed to be read 
*after* the base tutorial and focuses exclusively on the differences with respect 
to it: only the modified or new elements are described in detail, while unchanged 
steps are referenced to the base tutorial.

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

In the :download:`zip directory <production_planning_decomposition.zip>`, the same
materials as in the base tutorial are provided (notebook, concept workbook, and
model directory), updated for the non-linear variant.


Summary of changes with respect to the base tutorial
-----------------------------------------------------

The table below summarises all elements that differ from the
:ref:`tutorial-production-planning`. Everything not listed here is unchanged.

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Element
     - Change
   * - **Sets**
     - The *Attributes* set gains a new filter entry ``profit_slope`` and the
       existing ``profit`` entry is renamed ``profit_initial``, giving four
       attributes in total.
   * - **Data Tables**
     - The ``production`` table becomes *hybrid* (endogenous in sub-problem
       ``production``, exogenous in sub-problem ``profit``).
       A new *hybrid* ``profit`` table is added (exogenous in ``production``,
       endogenous in ``profit``).
       The ``products_data`` table grows from 6 to 8 rows.
   * - **Variables**
     - Since endogenous and exogenous variables must stay in separate Data Tables, 
       the variable :math:`c` moves from ``products_data`` to the new ``profit``
       table and becomes endogenous. Two new exogenous variables :math:`c_0`
       (initial profit) and :math:`c_s` (profit slope) replace it in
       ``products_data`` (these are exogenous).
   * - **Problems**
     - A second sub-problem ``profit`` is added, defining the equality
       :math:`c = c_0 + c_s \odot x`. The existing expressions are now placed
       under the named sub-problem ``production``.
   * - **Solving**
     - ``model.run_model()`` must be called with ``solution_mode='integrated'``
       to activate the iterative coupled solver.


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

Two data tables change: ``production`` becomes hybrid and the new ``profit``
table is introduced. The ``products_data`` domain grows by one attribute row.
All other tables are unchanged.

.. list-table:: Data Tables of the tutorial model (modified/new entries in bold)
   :header-rows: 1
   :widths: 22 20 25 33

   * - Name (sets domain)
     - Type
     - Domain [cardinality]
     - Description
   * - **production** *(modified)*
     - **Hybrid**: endogenous in ``production``; exogenous in ``profit``
     - :math:`p \times e \times m \; [2 \times 2 \times 2 = 8]`
     - Total products output by scenario
   * - **profit** *(new)*
     - **Hybrid**: exogenous in ``production``; endogenous in ``profit``
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

The key concept introduced here is the **hybrid data table**: a table whose
associated variable plays a different role (endogenous vs. exogenous) in
different sub-problems. This is how CVXlab resolves the circular dependency
that would arise from multiplying two endogenous variables: at each iteration
one variable is held fixed (exogenous) while the other is optimised
(endogenous), then the roles alternate (see
:ref:`definig-data-tables-variables`).

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

In CVXlab, this class of problem can be handled by :ref:`problem decomposition 
<definig-expressions-and-problems>`: once the user splits the problem into two 
coupled *convex* sub-problems, CVXlab solves them iteratively with a **block 
Gauss–Seidel** scheme. Specifically, the two sub-problems are:

.. math::
  \begin{aligned}
  &\textbf{Sub-problem } \texttt{production}: \\[4pt]
  &\quad \max_{x} \quad c \cdot x' \\
  &\quad \text{s.t.} \quad e \cdot x' - E \leq 0 \\
  &\quad\phantom{\text{s.t.}\;} m \cdot x' - M \leq 0 \\
  &\quad\phantom{\text{s.t.}\;} x \geq 0 \\[8pt]
  &\textbf{Sub-problem } \texttt{profit}: \\[4pt]
  &\quad c - c_s \cdot \mathrm{diag}(x) - c_0 = 0
  \end{aligned}

At each iteration, :math:`c` is held fixed while ``production`` optimises
:math:`x`; then :math:`x` is held fixed while ``profit`` updates :math:`c`.
The scheme repeats until convergence.

Notice that:

- The two sub-problem names (``production`` and ``profit``) must **match the
  keys used in the hybrid** ``type`` **dictionary** in ``structure_variables.yml``
  (e.g. ``{production: endogenous, profit: exogenous}``). CVXlab uses these
  names to route each variable to the correct role in each sub-problem.
- The ``diag()`` built-in operator constructs a diagonal matrix from a row
  vector, so that :math:`c_s \cdot \mathrm{diag}(x)` evaluates to the
  element-wise product :math:`c_s \odot x` (see :ref:`api_symbolic_operators`).
- Sub-problem ``profit`` has **no objective**: it defines a system of equalities
  rather than an optimisation problem. CVXlab handles mixed problem types
  (optimisation and equality systems) in the same model transparently.
- The iterative scheme starts from an initial feasible :math:`c` (e.g. :math:`c_0`),
  solves ``production`` to obtain :math:`x`, then solves ``profit`` to update
  :math:`c`, and repeats until convergence.


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

         # MODIFIED: type is now a hybrid dict mapping sub-problem → role
         production:
             description: products supply
             type: {production: endogenous, profit: exogenous}
             coordinates: [Products, Scenarios_energy, Scenarios_material]
             variables_info:
                 x:
                     Products:
                         dim: cols

         # NEW: hybrid profit data table
         profit:
             description: unit profit by production
             type: {production: exogenous, profit: endogenous}
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
            - {production: endogenous, profit: exogenous}
            - Products, Scenarios_energy, Scenarios_material
            - x
            - dim: cols
            -
          * - profit
            - unit profit by production
            - {production: exogenous, profit: endogenous}
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

Notice that:

- The ``type`` field for ``production`` and ``profit`` is now a **dictionary**
  keyed by sub-problem name. This is the CVXlab syntax for
  :ref:`hybrid variables <definig-data-tables-variables>`.
- The sub-problem keys in the ``type`` dictionary (``production``, ``profit``)
  must exactly match the problem keys used in ``problem.yml``.

.. rubric:: Modified symbolic problem definition

The problem file is restructured from a single flat problem into two named
sub-problems. The ``production`` expressions are unchanged in content; the new
``profit`` sub-problem contains only the equality that links :math:`c` to
:math:`c_0`, :math:`c_s`, and :math:`x`.

.. tabs::

   .. group-tab:: YAML

      File: ``problem.yml``

      .. code-block:: yaml

         production:

             objective:
                 - Maximize(c @ tran(x))

             expressions:
                 - e @ tran(x) - E <= 0
                 - m @ tran(x) - M <= 0
                 - x >= 0

             description:
                 - maximization of total profit
                 - energy use less than endowment
                 - material use less than endowment
                 - positive products supply

         profit:

             expressions:
                 - c - c_s @ diag(x) - c_0 == 0

             description:
                 - unit profit as a function of product demand

   .. group-tab:: XLSX

      File: ``model_settings.xlsx`` | tab ``problem``

      .. list-table::
          :header-rows: 1
          :align: center

          * - problem_key
            - objective
            - expressions
            - description
          * - production
            - Maximize(c @ tran(x))
            -
            - maximization of total profit
          * - production
            -
            - e @ tran(x) - E <= 0
            - energy use less than endowment
          * - production
            -
            - m @ tran(x) - M <= 0
            - material use less than endowment
          * - production
            -
            - x >= 0
            - positive products supply
          * - profit
            -
            - c - c_s @ diag(x) - c_0 == 0
            - unit profit as a function of product demand

Notice that:

- Compared to the base tutorial, the problem file gains an outer level of
  named keys (``production:``, ``profit:``). In the XLSX format, this is
  reflected by the addition of a ``problem_key`` column.
- The ``diag()`` built-in operator constructs a diagonal matrix from a
  row vector (see :ref:`api_symbolic_operators`).
- Sub-problem ``profit`` has no objective, only an equality expression.
  CVXlab resolves equality-only sub-problems as linear systems.


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

Because the two sub-problems are **coupled** (i.e., the output of ``production``
feeds into ``profit`` and vice versa) they cannot be solved independently.
The ``solution_mode`` argument must be set to ``'integrated'`` to activate the
iterative block Gauss–Seidel solver.

.. code-block:: python

   model.run_model(solution_mode='integrated')

During execution, CVXlab logs the convergence progress at each iteration,
reporting the norm of the change in endogenous values between successive
iterations. The solver repeats until the norm falls below the convergence
threshold defined in ``Defaults.NumericalSettings.MODEL_COUPLING_SETTINGS``.
Output of the convergence log is saved in a dedicated file in the model directory 
(e.g. ``convergence_high-high.log`` for the ``high``/``high`` scenario).
The file content for the ``high``/``high`` scenario is shown below.

.. code-block:: text

    ===============================================================================
    CONVERGENCE MONITORING - Scenario: high-high
    Numerical changes across iteration assessed based on Norm metric: 'l2'
    Relative tolerance on data tables norm: 0.010
    Thresholds in absolute values. '*' indicates value above tolerance.
    Absolute tolerances are defined per table based on first iteration values.
    ===============================================================================

    Table           Thresholds    Iter_0-1    Iter_1-2    Iter_2-3    Iter_3-4  
    ----------------------------------------------------------------------------
    production      2.473e+00     2.368e+01*  2.368e+01*  0.000e+00   0.000e+00 
    profit          5.496e-02     8.774e-01*  1.485e-01*  1.485e-01*  0.000e+00 

    Convergence reached!

Notice that:

- One log file is generated per scenario (one per combination of inter-problem
  set coordinates). In this tutorial, four files are produced, one for each
  energy/material scenario pair.
- The **Threshold** column reports the absolute convergence tolerance threshold 
  for each endogenous table, calculated from the first-iteration norm of each table, 
  scaled by the relative tolerance (``0.010``, i.e. 1%).
- Other columns report the norm of the change in each table between
  iteration 0 and iteration 1. A value of ``0.000e+00`` means that the solution
  did not change at all between the two iterations, while a numeric value indicates 
  a change: if the value is followed by an asterisk (e.g. ``2.368e+01*``), it means 
  that the change is above the convergence threshold. 
- Different norm types can be selected; in this tutorial, the default L2 norm is 
  used (Euclidean norm).
- The log ends with ``Convergence reached!``, confirming that both tables satisfy
  their tolerance after a single iteration. This is expected: given the linear
  structure of both sub-problems, the block Gauss–Seidel scheme converges in one
  step for all scenarios.

At convergence, the values of :math:`c` and :math:`x` are mutually consistent:
:math:`c` satisfies the equality constraint in ``profit`` given the current
:math:`x`, and :math:`x` is optimal for ``production`` given the current
:math:`c`. All four scenario instances converge successfully and return the
*optimal* status.


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