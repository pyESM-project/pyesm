CVXlab documentation
====================

.. warning::
   **Beta Release Notice**

   CVXlab is currently in beta (|version|). The API may still change before the
   stable 1.0.1 release. Feedback and bug reports are welcome via `GitHub Issues
   <https://github.com/cvxlab/cvxlab/issues>`_.

**CVXlab** is an open-source Python package for building convex optimization models 
from high-level settings, structured data, and symbolic expressions. It combines 
*YAML* or *Excel*-based model setup, *SQLite*-backed data management, and 
*CVXPY*-based numerical solving in one workflow.

**Version:** |version|
**Date:** |today|

**Useful links**: `PyPI <https://pypi.org/project/cvxlab/>`_ | 
`Source code <https://github.com/cvxlab/cvxlab>`_ | 
`Issue tracker <https://github.com/cvxlab/cvxlab/issues>`_


Start here
----------

.. list-table::
   :header-rows: 1
   :widths: 24 76

   * - Section
     - What you will find
   * - :doc:`installation`
     - How to install CVXlab and verify that the environment is ready.
   * - :doc:`user_guide`
     - The full modeling workflow, from conceptual model definition to results export.
   * - :doc:`tutorials`
     - Worked examples and downloadable materials to learn by running models.
   * - :doc:`api_reference`
     - Technical reference for ``cvxlab.Model``, utilities, operators, constants, and defaults.


Why CVXlab
----------

- **General-purpose model generator**. Build a wide range of convex optimization models.
- **Almost no code required**. Define model structure through *YAML* or *Excel* 
  templates instead of hand-coding every object.
- **Centralized data management**. Organize data in a *SQLite* database for 
  traceable, reusable data handling.
- **Powerful engine embedded**. Build convex and decomposed optimization workflows 
  on top of `CVXPY <https://www.cvxpy.org/tutorial/intro/index.html>`_.


Workflow at a glance
--------------------

The figure below summarizes the package workflow. The detailed step-by-step
explanation is in the :ref:`user_guide`, while runnable examples are collected
in the :ref:`tutorials`.

.. _fig:cvxlab_in_a_nutshell:

.. figure:: _static/CVXlab_nutshell.png
   :alt: CVXlab modeling process in a nutshell
   :align: center


.. toctree::
   :maxdepth: 1
   :caption: Documentation contents:

   installation
   user_guide
   tutorials
   api_reference
   resources
   changelog
   contributing


.. note::
   CVXlab is developed by *Matteo V. Rocco*, Associate Professor at *SESAM
   group*, `Department of Energy, Politecnico di Milano
   <https://www.energia.polimi.it/en/>`_. The project is released under the
   `Apache License 2.0 <http://www.apache.org/licenses/>`_.
