.. _conceptual-model-definition:

Conceptual model definition
===========================

The CVXlab modeling process must be grounded on a solid conceptualization and 
mathematical definition of the problem to be solved. As its name suggests, CVXlab 
is primarily designed for **convex optimization problems**.

Definition of convex optimization problems and related mathematical concepts
lies outside the scope of this documentation. Fundational knowledge of Opearations 
Research and can be found in several references. Among others, we suggest the textbook:
`Introduction to Operations Research (F.Hillier and G.Lieberman, McGraw Hill Education, 
2024) <https://www.mheducation.com/highered/product/Introduction-to-Operations-
Research-Hillier.html>`_

Since numerical problem generation and solution in CVXlab is grounded on the **CVXPY**
package, we also recommend referring to the `CVXPY documentation <https://www.cvxpy.org/
tutorial/intro/index.html>`_ for a comprehensive description of supported problem 
types.

Before generating a CVXlab Model, the items below must be conceptually defined.


.. _defining-sets:

Sets
----

Let :math:`\mathcal{S}_1, \ldots, \mathcal{S}_k` be finite, generic non-empty 
index sets. Sets represent the dimensions of the model, defining its scope. 
Each set :math:`\mathcal{S}_i` is characterized by a list of elements called 
**coordinates**. A **domain** (or **shape**) is defined as a Cartesian product 
of a subset of sets:

.. math::
  \Omega = \mathcal{S}_{i_1} \times \cdots \times \mathcal{S}_{i_p} \subseteq 
  \mathcal{S}_1 \times \cdots \times \mathcal{S}_k.

Definition of domains is useful to identify the scope of data tables (and consequently 
of related variables) in the model. 

A **sub-domain** can be identified by **filtering** each set :math:`\Omega' \subseteq \Omega` 
based on defined criteria. Defining sub-domains is useful in defining variables 
pointing to a subset of values in data table. 

A **specific element** in the domain is identified by a generic index tuple :math:`s` as:

.. math::
  s = (s_1,\ldots,s_k) \in \mathcal{S}_1 \times \cdots \times \mathcal{S}_k

Sets can be partitioned into two disjoint categories based on their role in problem 
structure:

.. math::
  \mathcal{S}_1 \times \cdots \times \mathcal{S}_k = 
  \underbrace{(\mathcal{S}_{I_1} \times \cdots \times \mathcal{S}_{I_m})}_{\text{Inter-problem sets}} 
  \times 
  \underbrace{(\mathcal{S}_{D_1} \times \cdots \times \mathcal{S}_{D_n})}_{\text{Dimensions sets}}

where :math:`m + n = k`. *Inter-problem sets* and *dimensions sets* are defined as:

- **Inter-problem sets** :math:`\mathcal{S}_{I_1}, \ldots, \mathcal{S}_{I_m}`: 
  Define the space over which the numerical problem is solved. All variables and 
  expressions in the model are defined and the numerical problem solved for each 
  coordinate combination in the Cartesian product of inter-problem sets: 
  :math:`\iota \in \mathcal{S}_{I_1} \times \cdots \times \mathcal{S}_{I_m}`. 
  Each combination is defined as a **scenario**, defining a distinct instance of 
  the optimization problem. Inter-problem sets are used to define multiple scenarios,
  e.g., to represent different demand projections, cost assumptions, or to perform 
  sensitivity analysis on critical parameters.

- **Dimensions sets** :math:`\mathcal{S}_{D_1}, \ldots, \mathcal{S}_{D_n}`: 
  Specify the shape and indexing of model variables — i.e., how variables are arranged 
  into rows and columns and indexed across intra-problem coordinates. Depending 
  by each variable, dimension sets can be further classified as:

  - **Shape sets**: Define *rows* and *columns* of variables (matrix structure). 
    Multiple sets can be assigned to the same row or column; the resulting dimension 
    is the Cartesian product of the assigned sets. For rows over 
    :math:`\mathcal{S}_{R} = \mathcal{S}_{a} \times \mathcal{S}_{b}`, the variable 
    has :math:`|\mathcal{S}_{R}| = |\mathcal{S}_{a}| \cdot |\mathcal{S}_{b}|` rows 
    with row coordinates :math:`(s_a, s_b) \in \mathcal{S}_{a} \times \mathcal{S}_{b}`. 
    The same applies to columns.
  - **Intra-problem sets**: Variables with a given shape are indexed over the 
    Cartesian product of the remaining dimensions sets, defined as intra-problem sets.
    For intra-problem coordinates over 
    :math:`\mathcal{S}_{P} = \mathcal{S}_{P_1} \times \cdots \times \mathcal{S}_{P_p}`, 
    each variable :math:`x` of shape :math:`\mathcal{S}_{R} \times \mathcal{S}_{C}` 
    has :math:`|\mathcal{S}_{P}| = \prod_{j=1}^{p} |\mathcal{S}_{P_j}|` instances, 
    one for each :math:`\pi = (s_{P_1},\ldots,s_{P_p}) \in \mathcal{S}_{P}`.

A consistent definition of variables dimensions is fundamental to correctly define 
symbolic expressions in the model, that must be dimensionally consistent. 


.. _definig-data-tables-variables:

Data Tables and Variables
-------------------------

**Data tables** represent collections of model data identified by a sets domain.
Specifically, a **data table** :math:`D` over domain :math:`\Omega` is a function:

.. math::
  D : \Omega \to \mathbb{R} \quad \text{(or } \mathbb{Z}, \{0,1\}\text{)}

where :math:`\Omega \subseteq \mathcal{S}_1 \times \cdots \times \mathcal{S}_k`.

Data tables can be classified as:

- **Exogenous**: known parameters :math:`d(s)` for :math:`s \in \Omega`
- **Endogenous**: unknowns to be determined (can be further classified as *decision 
  variables* or *auxiliary variables*). Can be further defined as *continuous* or *integer*.
- **Constants**: fixed values. Multiple built-in constant types are supported, 
    and user-defined constants can also be defined (both defined at the variable 
    level, see :ref:`api_constants_types`).

In case of integrated problems solved iteratively, variables can be defined as 
*endogenous or exogenous* based on the role they play in each problem, avoiding 
circular dependencies (see :ref:`definig-expressions-and-problems`).

A **variable** :math:`x` associated with a data table :math:`D` is a symbolic 
reference to values in :math:`D`, defined over the same domain :math:`\Omega`, 
or over a filtered sub-domain :math:`\Omega'`. Multiple variables can reference 
the same data table, characterized by:

- A different allocation of dimensions sets (i.e. defining different sets as  
  shapes and intra-problem sets)
- Different filterings (i.e. referring to sub-domains :math:`\Omega' \subseteq \Omega`)
- In case of constants, different *built-in constant types* are supported, 
  and *user-defined constants* can also be defined.

The reason why data tables and variables are defined separately is to allow multiple
variables to reference the same data table in different ways, increasing flexibility 
in problem definition, and optimizing data management in the model SQLite database.


.. _definig-expressions-and-problems:

Expressions and Problems
------------------------

An **expression** :math:`f` is a symbolic composition of variables and linear operators:

.. math::
  f(x_1, \ldots, x_n) = \sum_{j=1}^{n} A_j(x_j)

where:

- :math:`x_j` are variables, defined over domains :math:`\Omega_j`
- :math:`A_j : \mathbb{R}^{\Omega_j} \to \mathbb{R}^{\Theta}` are linear aggregation 
  operators (summations, weighted sums, matrix multiplications, etc.). Complex 
  operations not expressible through built-in operators can be implemented as 
  user-defined operators (see :ref:`api_symbolic_operators`).

Symbolic expressions must be **dimensionally consistent**: variables shapes must 
be compatible (defined over matching or properly aligned domains/sub-domains)
Moreover, when a variable is characterized by **intra-problem sets**, one numerical 
expression instance is generated for each coordinate combination of those intra-problem 
sets. Variables with different intra-problem sets can appear in the same symbolic 
expression: each variable is automatically broadcast/reused across all generated 
expression instances, allowing for a flexible problem definition.

This can be formalized using the notation introduced in :ref:`defining-sets`: 
dimension sets are partitioned into shape sets :math:`\mathcal{S}_{R}` (rows) and 
:math:`\mathcal{S}_{C}` (columns), plus :math:`p` intra-problem sets 
:math:`\mathcal{S}_{P_1}, \ldots, \mathcal{S}_{P_p}`.

An expression :math:`f(x_1, \ldots, x_k)` with variables over domains 
:math:`\Omega_1, \ldots, \Omega_k` is **dimensionally consistent** if all shape 
components are compatible (matching row/column dimensions or properly broadcastable).

For each :math:`\pi \in \mathcal{S}_{P_1} \times \cdots \times \mathcal{S}_{P_p}`, 
a **numerical expression instance** :math:`f_{\pi}` is generated:

.. math::
  f_{\pi}(x_1|_{\pi}, \ldots, x_k|_{\pi})

where :math:`x_j|_{\pi}` denotes the restriction/broadcast of variable :math:`x_j` 
to the intra-problem coordinate :math:`\pi`. Variables with different intra-problem 
sets are automatically broadcast across all instances.

A **problem** is defined by one or more symbolic expressions, as either:

**1. System of linear equations:**

.. math::
  \begin{aligned}
  f_1(x) &= b_1 \\
  &\vdots \\
  f_p(x) &= b_p
  \end{aligned}

**2. Convex optimization problem:**

.. math::
  \begin{aligned}
  \min_{x} \quad & f_0(x) \\
  \text{s.t.} \quad & f_i(x) \le b_i, \quad i = 1, \ldots, p \\
  & h_j(x) = c_j, \quad j = 1, \ldots, q \\
  & \ell \le x \le u
  \end{aligned}

where :math:`f_0` is convex, :math:`f_i` are convex, and :math:`h_j` are affine.

Multiple problems can be defined in the same CVXlab model, all sharing common sets,
data tables, and variables. 

A CVXlab model can formulate and solve multiple problems that share the same sets, 
data tables, and variables. Problems are all solved over the same inter-problem sets
:math:`\mathcal{S}_{I_1} \times \cdots \times \mathcal{S}_{I_m}`. Two execution schemes 
are supported:

- **Parallel** (independent problems): problems with no coupling (no shared endogenous 
  variables in expressions) can be solved independently and in parallel over the 
  inter-problem sets.

- **Iterative decomposition** (coupled/nonlinear): if a problem is *nonlinear* due 
  to products of endogenous variables, split it into two or more convex subproblems. 
  CVXlab solves them iteratively with a *block Gauss-Seidel* (alternating optimization) 
  scheme, updating shared endogenous variables between subproblems until convergence.
  In this case, data tables must be classified as endogenous or exogenous per subproblem 
  to allow proper information exchange and avoid circular dependencies. 


.. _conceptual-example:

Example: energy system model
----------------------------

**Problem statement**

Let us consider a *conceptual* energy system planning model, where the goal is to 
define the *least-cost energy production plan* for one region over a defined time 
horizon, able to satisfy energy demand (assumed as known data defined according to 
different scenarios). Energy can be supplied by different technologies, characterized 
by specific production costs and installed capacities and availabilities (i.e. values 
able to convert installed capacity in MW to energy supplied in MWh). Installed 
capacity is varying over time, while costs and availabilities are assumed as fixed.


**Definition of model sets and related coordinates**

Sets defined for the model are summarized in the table below. 

.. list-table:: Sets defining model's domain
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

Notice that:

- Inter-problem sets (:math:`d`) define multiple problem instances.  
  This implies that one optimization problem is generated and solved for each 
  combination of demand scenario and cost sensitivity (in this case, only :math:`2` 
  problem instances).
- Dimension sets (:math:`t`, :math:`y`) are used to define the scope of data tables 
  and the shapes of related variables.
- Coordinates of each set can be associated to filters to define sub-domains. As 
  example, the *technologies* set may classify technologies as *renewable* and
  *non-renewable*, allowing to define variables with sub-domains including only 
  specific categories. In this simplified example, all variables are defined over 
  *full domains* (no filtering is applied).


**Definition of data tables and variables**

The following tables summarizes the data tables and associated variables for the 
energy system model. 

.. list-table:: Data tables properties
  :header-rows: 1

  * - Type
    - Name
    - Domain [Cardinality]
    - Description
  * - Exogenous
    - :math:`cost(t)`
    - :math:`t - [3]`
    - Specific costs of generation by cost scenario and technology (in *€/MWh*).
  * - Exogenous
    - :math:`capacity(t,y)`
    - :math:`t \times y - [3 \times 6 = 18]`
    - Installed capacity by technology and time period (in *MW*).
  * - Exogenous
    - :math:`availability(t)`
    - :math:`t - [3]`
    - Availability factors by technology (in *MWh/MW*).
  * - Exogenous
    - :math:`demand(d,y)`
    - :math:`d \times y - [2 \times 1 \times 6 = 12]`
    - Energy demand defined by demand scenarios and time periods.
  * - Endogenous
    - :math:`supply(d,y,t)`
    - :math:`d \times y \times t - [2 \times 6 \times 3 = 72]`
    - Energy supply defined by demand and cost scenarios, technology and time period.
  * - Constant
    - :math:`constant(t)`
    - :math:`t - [3]`
    - Model constants defined based on the shape of :math:`t` set.

Regarding data tables above:

- Endogenous data table has a domain defined over all model sets, while exogenous 
  data tables are defined over specific sets.
- For each data table, the cardinality (i.e. the total number of data entries) is 
  reported, calculated as the product of the cardinalities of all sets in the domain. 
  As example, the `availability(t)` data table includes 3 entries only, one for each 
  technology, due to its domain defined over the *technologies* set only.

.. list-table:: Variables properties
  :header-rows: 1

  * - Related data table
    - Variable name
    - Shape (rows,columns)
    - Intra-problem sets
    - Inter-problem sets
  * - :math:`cost(t)`
    - :math:`c`
    - :math:`1, t - [1, 3]`
    - :math:`-`
    - :math:`-`
  * - :math:`capacity(t, y)`
    - :math:`cap`
    - :math:`1, t - [1, 3]`
    - :math:`y - [6]`
    - :math:`-`
  * - :math:`availability(d, y)`
    - :math:`av`
    - :math:`1, t - [1, 3]`
    - :math:`-`
    - :math:`-`
  * - :math:`demand(d, y)`
    - :math:`E_d`
    - :math:`1, 1 - [1, 1]`
    - :math:`y - [6]`
    - :math:`d - [2]`
  * - :math:`supply(d,y,t)`
    - :math:`E_s`
    - :math:`1, t - [1, 3]`
    - :math:`y - [6]`
    - :math:`d - [2]`
  * - :math:`consant(t)`
    - :math:`i_t`
    - :math:`t, 1 - [3, 1]`
    - :math:`-`
    - :math:`-`

Regarding variables above:

- Each variable stem from a related data table, inheriting its properties: the 
  domain (defined by sets) and the data type (exogenous, endogenous, constant).
- Each variable is characterized by a specific allocation of dimensions sets 
  into shapes and intra-problem sets. As example, the energy supply `E_s` variable 
  has 1 row and 3 columns (defined by the *technologies* set), it is indexed over 
  6 intra-problem coordinates (defined by the *time periods* set) and over 2 
  inter-problem coordinates (defined by the *demand scenarios* set).
- Constants can be defined with different built-in or user defined types (see 
  :ref:`api_constants_types`). In the example above, the `i_t` variable is
  defined as a *summation vector*, consisting in a column vector of 1s, useful to 
  perform summations by matrix multiplications.


**Definition of symbolic problem**

For the current energy system model, a symbolic problem can be defined as a linear 
optimization problem as follows.

.. math::
  \begin{aligned}
  \min_{E_s} \quad & c \cdot E_s' & \forall \, y\\
  \text{s.t.} \quad & E_s \cdot i_t \geq E_d & \forall \, y \\
  & E_s \leq cap \cdot \widehat{av} & \forall \, y \\
  & E_s \geq 0 & \forall \, y
  \end{aligned}

Notice that:

- The problem is defined a number of times equal to the cardinality of the inter-problem 
  set. Specifically, one problem instance is defined and solved for each energy demand 
  scenarios :math:`d`. In case of multiple inter-problem sets, the problem is defined
  for each coordinate combination in the Cartesian product of all inter-problem sets.
- For each simbolic expression, a number of numerical expressions is generated, equal 
  to the Cartesian product of all intra-problem sets of the related variables. 
  In this case, all expressions are defined over the intra-problem set *time periods* 
  :math:`y`, generating one numerical expression per time period for all symbolic 
  expressions.
- In case of variables defined over different intra-problem sets, automatic broadcasting 
  is applied, Variables not defined over specific intra-problem sets are automatically 
  reused across all generated numerical expressions.
- In this problem, the dot operator :math:`\cdot` represents matrix multiplication, 
  the :math:`\widehat{(*)}` is the diagonalization operator, and the :math:`(*)'` represents 
  the transposition operator (see :ref:`api_symbolic_operators` for a comprehensive 
  description of built-in symbolic operators).


A note on dimensional consistency
---------------------------------

The allocation of dimension sets to shapes and intra-problem sets offers significant 
modeling flexibility. The same problem can be formulated in multiple equivalent ways.


**Matrix-based formulation (as in the example above):**

- Expressions must be dimensionally consistent, and variables shapes must be 
  compatible for matrix operations. Multiple variables can stem from the same data 
  table, each characterized by different allocations of dimension sets: this allows
  for flexible model definitions.
- Expressions works with matrix operations (multiplication, transposition, ...).
- Compact symbolic representation with fewer expression instances.
- Potentially more efficient numerical problem generation and solution.


**Scalar-based formulation (extreme case):**

All dimension sets can be allocated as *intra-problem sets*, reducing all variables 
to scalars (shape :math:`(1,1)`). In this case, for each energy demand scenario :math:`d`,
the problem can be reformulated as:

.. math::
  \begin{aligned}
  \min_{E_s} \quad & \sum_{t} c \cdot E_s \\
  \text{s.t.} \quad & \sum_{t} E_s \geq E_d & \forall \, y \\
  & E_s \leq cap \cdot av & \forall \, t \, y \\
  & E_s \geq 0 & \forall \, t \, y
  \end{aligned}

where all variables become scalars indexed over :math:`t` and :math:`y`.


**Trade-offs:**

.. list-table::
  :header-rows: 1
  
  * - Aspect
    - Matrix-based
    - Scalar-based
  * - Symbolic complexity
    - Lower (fewer expressions)
    - Higher (many expression instances)
  * - Mathematical notation
    - Compact and elegant
    - Explicit summations
  * - Computational overhead
    - Efficient matrix operations
    - More expression instances to generate
  * - Model readability
    - High-level abstraction
    - Detailed element-wise view
  * - Debugging
    - Harder (matrix operations)
    - Easier (scalar operations)


**Recommendation:**

Use matrix formulations when:

- The problem has natural matrix structure (e.g., flows over networks, resource allocation).
- A compact symbolic expression is preferred.
- Computational efficiency matters (large-scale problems).

Use scalar formulations when:

- Element-wise constraints are complex and benefit from explicit indexing.
- Debugging and transparency are priorities.
- The problem is small-scale.

CVXlab supports both approaches and any intermediate allocation, allowing users to 
choose the most appropriate abstraction level for their specific modeling needs. 
All formulations are **mathematically equivalent** and produce **identical numerical 
solutions**.