.. _conceptual-model-definition:

Conceptual model definition
===========================

The CVXlab modeling process must be grounded on a solid conceptualization and
mathematical definition of the problem to be solved. As its name suggests,
CVXlab is primarily designed for **convex optimization problems**.

Definition of convex optimization problems and related mathematical concepts
lies outside the scope of this documentation. Foundational knowledge of
Operations Research can be found in several references. Among others, we
suggest the textbook:
`Introduction to Operations Research (F. Hillier and G. Lieberman, McGraw Hill 
Education, 2024) <https://www.mheducation.com/highered/product/Introduction-to-Operations-Research-Hillier.html>`_

Since numerical problem generation and solution in CVXlab is grounded on the
**CVXPY** package, we also recommend referring to the
`CVXPY documentation <https://www.cvxpy.org/tutorial/intro/index.html>`_ for a
comprehensive description of supported problem types.

Before generating a CVXlab Model, the items below must be conceptually defined.


.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Concept
     - Defines
     - Used for
   * - :ref:`Sets <defining-sets>`
     - The model domain and indexing space
     - Defining model Variables based on a coordinates system
   * - :ref:`Data Tables <definig-data-tables-variables>`
     - The model data over a domain defined by multiple Sets
     - Storing data in the database, defining Variables
   * - :ref:`Variables <definig-data-tables-variables>`
     - Symbolic references to Data Table values
     - Defining model symbolic Expressions
   * - :ref:`Expressions <definig-expressions-and-problems>`
     - Symbolic combinations of Variables and operators
     - Defining numerical Problems
   * - :ref:`Problems <definig-expressions-and-problems>`
     - Numerical problem(s) of the model
     - Determining endogenous Data Tables values


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

Definition of domains is useful to identify the scope of data tables (and
consequently of related variables) in the model.

A **sub-domain** can be identified by **filtering** each set
:math:`\Omega' \subseteq \Omega` based on defined criteria. Defining
sub-domains is useful in defining variables pointing to a subset of values in a
data table.

A **specific element** in the domain is identified by a generic index tuple
:math:`s` as:

.. math::
  s = (s_1,\ldots,s_k) \in \mathcal{S}_1 \times \cdots \times \mathcal{S}_k

Sets can be partitioned into two disjoint categories based on their role in the
problem structure:

.. math::
  \mathcal{S}_1 \times \cdots \times \mathcal{S}_k =
  \underbrace{(\mathcal{S}_{I_1} \times \cdots \times \mathcal{S}_{I_m})}_{\text{Inter-problem sets}}
  \times
  \underbrace{(\mathcal{S}_{D_1} \times \cdots \times \mathcal{S}_{D_n})}_{\text{Dimension sets}}

where :math:`m + n = k`. *Inter-problem sets* and *dimension sets* are defined
as below. A consistent definition of variable dimensions is fundamental to correctly
define symbolic expressions in the model, which must be dimensionally consistent.


.. rubric::  Inter-problem sets 
  
:math:`\mathcal{S}_{I_1}, \ldots, \mathcal{S}_{I_m}`

Define the space over which the numerical problem is solved. All variables and
expressions in the model are defined and the numerical problem is solved for
each coordinate combination in the Cartesian product of inter-problem sets:
:math:`\iota \in \mathcal{S}_{I_1} \times \cdots \times \mathcal{S}_{I_m}`.
Each combination is defined as a **scenario**, identifying a distinct
instance of the optimization problem. Inter-problem sets are used to define
multiple scenarios, for example to represent different demand projections,
cost assumptions, or sensitivity cases.


.. rubric:: Dimension sets 
  
:math:`\mathcal{S}_{D_1}, \ldots, \mathcal{S}_{D_n}`

Specify the shape and indexing of model variables, that is, how variables are
arranged into rows and columns and indexed across intra-problem coordinates.
Depending on each variable, dimension sets can be further classified as:

- **Shape sets**: define *rows* and *columns* of variables (matrix
  structure). Multiple sets can be assigned to the same row or column, and the
  resulting dimension is the Cartesian product of the assigned sets. For rows
  over :math:`\mathcal{S}_{R} = \mathcal{S}_{a} \times \mathcal{S}_{b}`, the
  variable has :math:`|\mathcal{S}_{R}| = |\mathcal{S}_{a}| \cdot |\mathcal{S}_{b}|`
  rows with row coordinates :math:`(s_a, s_b) \in \mathcal{S}_{a} \times \mathcal{S}_{b}`.
  The same applies to columns.
- **Intra-problem sets**: variables with a given shape are indexed over the
  Cartesian product of the remaining dimension sets. For intra-problem
  coordinates over
  :math:`\mathcal{S}_{P} = \mathcal{S}_{P_1} \times \cdots \times \mathcal{S}_{P_p}`,
  each variable :math:`x` of shape :math:`\mathcal{S}_{R} \times \mathcal{S}_{C}`
  has :math:`|\mathcal{S}_{P}| = \prod_{j=1}^{p} |\mathcal{S}_{P_j}|`
  instances, one for each
  :math:`\pi = (s_{P_1},\ldots,s_{P_p}) \in \mathcal{S}_{P}`.


.. _definig-data-tables-variables:

Data Tables and Variables
-------------------------

**Data tables** represent collections of model data identified by a set domain.
Specifically, a **data table** :math:`D` over domain :math:`\Omega` is a
function:

.. math::
  D : \Omega \to \mathbb{R} \quad \text{(or } \mathbb{Z}, \{0,1\}\text{)}

where :math:`\Omega \subseteq \mathcal{S}_1 \times \cdots \times \mathcal{S}_k`.

Data tables can be classified as:

- **Exogenous**: known parameters :math:`d(s)` for :math:`s \in \Omega`
- **Endogenous**: unknowns to be determined. These can be further classified as
  *decision variables* or *auxiliary variables*, and can be continuous,
  integer (:math:`\mathbb{Z}`), or boolean (:math:`\{0,1\}`).
- **Constants**: fixed values. Multiple built-in constant types are supported,
  and user-defined constants can also be defined at the variable level
  (see :ref:`api_constants_types`).

.. admonition:: Hybrid Data Tables
  
  In case of integrated problems solved iteratively, variables can be defined as
  endogenous or exogenous depending on the role they play in each problem,
  avoiding circular dependencies (see :ref:`definig-expressions-and-problems`). 
  In this case, Data Tables can be classified as **hybrid**, meaning that the 
  variables stemming from them are defined as endogenous for some problems and 
  exogenous for others.

A **variable** :math:`x` associated with a data table :math:`D` is a symbolic
reference to values in :math:`D`, defined over the same domain :math:`\Omega`,
or over a filtered sub-domain :math:`\Omega'`. Multiple variables can reference
the same data table, characterized by:

- A different allocation of dimension sets, defining different sets as shapes
  and intra-problem sets.
- Different filterings, referring to sub-domains
  :math:`\Omega' \subseteq \Omega`.
- Different constant definitions, in case the table stores constants.

The reason why data tables and variables are defined separately is to allow
multiple variables to reference the same data table in different ways,
increasing flexibility in problem definition and optimizing data management in
the model SQLite database.


.. _definig-expressions-and-problems:

Expressions and Problems
------------------------

An **expression** :math:`f` is a symbolic composition of variables and linear
operators:

.. math::
  f(x_1, \ldots, x_n) = \sum_{j=1}^{n} A_j(x_j)

where:

- :math:`x_j` are variables, defined over domains :math:`\Omega_j`
- :math:`A_j : \mathbb{R}^{\Omega_j} \to \mathbb{R}^{\Theta}` are linear
  aggregation operators (summations, weighted sums, matrix multiplications,
  etc.). Complex operations not expressible through built-in operators can be
  implemented as user-defined operators
  (see :ref:`api_symbolic_operators`).

Symbolic expressions must be **dimensionally consistent**: variable shapes must
be compatible and, when needed, properly aligned or broadcast. Moreover, when a
variable is characterized by **intra-problem sets**, one numerical expression
instance is generated for each coordinate combination of those sets. Variables
with different intra-problem sets can appear in the same symbolic expression:
each variable is automatically broadcast or reused across all generated
expression instances.

This can be formalized using the notation introduced in :ref:`defining-sets`:
dimension sets are partitioned into shape sets :math:`\mathcal{S}_{R}` (rows)
and :math:`\mathcal{S}_{C}` (columns), plus :math:`p` intra-problem sets
:math:`\mathcal{S}_{P_1}, \ldots, \mathcal{S}_{P_p}`.

An expression :math:`f(x_1, \ldots, x_k)` with variables over domains
:math:`\Omega_1, \ldots, \Omega_k` is **dimensionally consistent** if all shape
components are compatible.

For each
:math:`\pi \in \mathcal{S}_{P_1} \times \cdots \times \mathcal{S}_{P_p}`, a
**numerical expression instance** :math:`f_{\pi}` is generated:

.. math::
  f_{\pi}(x_1|_{\pi}, \ldots, x_k|_{\pi})

where :math:`x_j|_{\pi}` denotes the restriction or broadcast of variable
:math:`x_j` to the intra-problem coordinate :math:`\pi`.

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

where :math:`f_0` is convex, :math:`f_i` are convex, and :math:`h_j` are
affine.

Multiple problems can be defined in the same CVXlab model, all sharing common
sets, data tables, and variables.

A CVXlab model can formulate and solve multiple problems that share the same
sets, data tables, and variables. Problems are all solved over the same
inter-problem sets
:math:`\mathcal{S}_{I_1} \times \cdots \times \mathcal{S}_{I_m}`. Two execution
schemes are supported:

- **Parallel** (independent problems): problems with no coupling, meaning no
  shared endogenous variables in expressions, can be solved independently and in
  parallel over the inter-problem sets.

- **Iterative decomposition** (coupled or nonlinear): if a problem is nonlinear
  due to products of endogenous variables, it can be split into two or more
  convex subproblems. CVXlab solves them iteratively with a *block Gauss-Seidel*
  (alternating optimization) scheme, updating shared endogenous variables
  between subproblems until convergence. In this case, data tables must be
  classified as endogenous or exogenous per subproblem to allow proper
  information exchange and avoid circular dependencies within the same
  subproblem.

.. admonition:: Non-linear problem decomposition
  
   A simple conceptual example is the following coupled system of equalities:

   .. math::
     \text{Problem 0: }
     \left\{
     \begin{aligned}
     a + xy &= 0 \\
     b + cx &= 0
     \end{aligned}
     \right.
     \begin{aligned}
     &\text{endogenous: } x, y \\
     \end{aligned}

   The term :math:`xy` makes the system nonlinear because it multiplies two
   endogenous variables. Problem 0 can be decomposed into two separate linear
   subproblems 1 and 2:

   .. math::
     \begin{aligned}
     &\text{Problem 1: } \left\{ a + xy = 0 \right.
     \text{endogenous: } y
     \\
     &\text{Problem 2: } \left\{ b + cx = 0 \right.
     \text{endogenous: } x
     \end{aligned}

   In this way, the same shared variable :math:`x` appears in both subproblems 
   with different roles: as *endogenous* in Problem 2 and *exogenous* in Problem 1. 
   Each subproblem is linear once the shared variable coming from the other block 
   is fixed.


Dimensional consistency
-----------------------

The allocation of dimension sets to shapes and intra-problem sets offers
significant modeling flexibility. The same problem can be formulated in
multiple equivalent ways.

In case variables *Dimension sets* are defined by including *Shape sets*, the 
variable is defined as vector or matrix. This leads to a **matrix-based 
formulation** of mathematical problem, including one or multiple vectorized 
expressions. In this case, vectorized expressions must be dimensionally consistent, 
and variable shapes must be compatible for matrix operations such as matrix 
multiplication or transposition. This representation is compact and usually 
leads to more efficient computations; however, it could be more complex to be 
formulated and understood.

In case *Dimension sets* are all defined as *Intra-problem sets*, all variables 
are reduced to scalars with shape :math:`(1,1)`. This leads to a **scalar-based 
formulation** of mathematical problem, where all expressions are written in an 
element-wise way. This representation is more explicit and easier to understand, 
but it can lead to a higher number of expression instances and less efficient 
computations.

Trade-offs between the two formulations are summarized in the table below.

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


It is recommended to rely on a *matrix-based formulations* when the problem has 
a natural matrix structure, a compact symbolic expression is preferred, or 
computational efficiency matters. Conversely, use *scalar formulations* when 
element-wise constraints are complex and benefit from explicit indexing, debugging 
and transparency are priorities, or the problem is small-scale.

CVXlab supports both approaches and any intermediate allocation, allowing users
to choose the most appropriate abstraction level for their specific modeling
needs. All formulations are **mathematically equivalent** and produce
**identical numerical solutions**.