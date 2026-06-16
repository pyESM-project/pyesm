Installation
============

CVXlab supports **Python 3.11** and is tested on Windows and macOS. Using an 
isolated ``conda`` environment is strongly recommended to avoid dependency 
conflicts with other projects.


Create a Conda Environment
---------------------------

Creating a dedicated conda environment ensures *CVXlab* and its dependencies don't 
interfere with other Python projects. This step is optional but highly recommended.

For **Windows**: Open **Anaconda Prompt** or **Command Prompt** (with conda in PATH); 
for **macOS / Linux**: Open a terminal. Then run:

.. code-block:: bash

   conda create -n cvxlab python=3.11
   conda activate cvxlab

Once the environment is activated, your prompt should show ``(cvxlab)`` at the 
beginning. You can now proceed to install CVXlab.


Install from PyPI (Users)
-------------------------

If you want to **use** CVXlab for modeling and solving optimization problems 
(without modifying the source code), install it via pip.

With the ``cvxlab`` conda environment active, run:

.. code-block:: bash

   pip install cvxlab

This command installs CVXlab and all required dependencies (numpy, pandas, cvxpy, 
openpyxl, etc.).


Install from Dev Branch (Latest Features)
------------------------------------------

If you want to **try the latest unreleased features** without modifying the source 
code yourself, you can install directly from the ``dev`` branch on GitHub:

.. code-block:: bash

   pip install git+https://github.com/cvxlab/cvxlab.git@dev

This installs the current state of the ``dev`` branch as a regular (non-editable) 
package. No git clone is required. To update to the newest commits later, re-run 
the same command with the ``--upgrade`` flag:

.. code-block:: bash

   pip install --upgrade git+https://github.com/cvxlab/cvxlab.git@dev

.. note::

   The ``dev`` branch may contain features or fixes not yet in the stable PyPI 
   release. It is generally functional but not guaranteed to be fully stable.


Install from Source (Developers)
----------------------------------

If you want to **contribute** to CVXlab or modify the source code, install it in 
editable mode from the GitHub repository.


.. rubric:: Option 1: Clone directly (for private development)

1. Clone the repository:

   .. code-block:: bash

      git clone https://github.com/cvxlab/cvxlab.git
      cd cvxlab

2. With the ``cvxlab`` conda environment active, install in editable mode:

   .. code-block:: bash

      pip install -e .[dev]


.. rubric:: Option 2: Fork (for contributing via pull requests)

If you plan to submit changes back to the project:

1. Fork the repository on GitHub (click "Fork" at https://github.com/cvxlab/cvxlab).

2. Clone **your fork**:

   .. code-block:: bash

      git clone https://github.com/YOUR_USERNAME/cvxlab.git
      cd cvxlab

3. Add the upstream repository as a remote:

   .. code-block:: bash

      git remote add upstream https://github.com/cvxlab/cvxlab.git

4. With the ``cvxlab`` conda environment active, install in *editable mode* (with 
   the ``-e`` flag), so all changes make to the source code are immediately 
   reflected without reinstalling. This is ideal for development and testing.

   .. code-block:: bash

      pip install -e .[dev]

   Extras can be included to install additional dependencies for development, 
   documentation, or solvers:

   - ``[dev]``: Installs development dependencies (pytest, black, flake8, mypy, etc.).
   - ``[docs]``: Installs Sphinx and related tools for building documentation.
   - ``[solvers]``: Installs additional solver interfaces (e.g., ``gurobipy`` for GUROBI).

5. Create a feature branch for your changes:

   .. code-block:: bash

      git checkout -b feature/my-new-feature

6. After making changes, push to your fork and open a pull request on GitHub.


Verify Installation
-------------------

After installation, verify that CVXlab is correctly installed and importable:

.. code-block:: bash

   python -c "import cvxlab; print(cvxlab.__version__)"

If the import succeeds and prints the version, CVXlab is ready to use.


Troubleshooting
---------------

- Check the `GitHub Issues <https://github.com/cvxlab/cvxlab/issues>`_ page.
- Consult the `cvxpy installation guide <https://www.cvxpy.org/install/>`_ for 
  solver-specific troubleshooting.
- Reach out via email: |author_email|
