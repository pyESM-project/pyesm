.. _resources:

Resources
=========

This section collects tutorials and example models to help you get started with
**cvxlab**. Each tutorial walks you through the steps described in the
:ref:`User Guide <user_guide>` for a specific use-case.

Tutorial directories (with supplementary modeling materials such as Jupyter
Notebooks, Excel concept files, input-data files and SQLite databases) can be
downloaded from the table below, so that you can run them locally on your machine.


.. _tutorials:

Tutorials
---------


.. list-table::
    :header-rows: 1
    :widths: 30 60 10

    * - Tutorial
      - Description
      - Material
    * - :doc:`Production planning <tutorials/production_planning/production_planning>`
      - Complete workflow for definining and solving a simple production planning 
        under resource constraints. Step by step guide aligned with :ref:`User 
        Guide <model_generation_from_scratch>`. *Ideal for newbies*.
      - :download:`link <tutorials/production_planning/production_planning.zip>`
    * - :doc:`Production planning (non-linear) <tutorials/production_planning_nonlinear/production_planning_nonlinear>`
      - Complete workflow for definining and solving a non-linear production planning 
        under resource constraints. Similar to previous production planning tutorial, 
        but handling non-linearities. 
      - :download:`link <tutorials/production_planning_nonlinear/production_planning_nonlinear.zip>`


.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Tutorials index

   tutorials/production_planning/production_planning
   tutorials/production_planning_nonlinear/production_planning_nonlinear


.. _models_gallery:

Models gallery
--------------

A collection of published models built with CVXlab, including links to data
repositories where models and input data can be found.

.. list-table::
    :header-rows: 1
    :widths: 40 45 15

    * - Model
      - Description
      - Repository
    * - **Parametric LCA model of floating offshore wind farm**
        *(Ghezzi D, Rocco MV | 2025)*
      - Parametric life-cycle assessment of electricity generation from
        semi-submersible floating offshore wind farms. Covers 192 configurations
        defined by turbine capacity, platform and mooring material, end-of-life
        treatment, capacity factor, cable type, and steel origin.
      - `Dataset <https://doi.org/10.5281/zenodo.17161021>`__
        `Related article <https://www.scopus.com/pages/publications/105039704468?origin=resultslist>`__


.. _publications:

Publications
------------

A collection of published articles that use CVXlab for modeling and solving
optimization problems.

- **Parametric life cycle assessment of carbon footprint of electricity generation from floating offshore wind farms**
  *(Ghezzi D, Rocco MV | Sustainable Energy Technology and Assessments | 2025)* |
  `Article link <https://www.scopus.com/pages/publications/105039704468?origin=resultslist>`__