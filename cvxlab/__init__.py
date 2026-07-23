"""CVXlab - Open-source Python laboratory for convex algebraic modeling.

This module provides shortcuts to the main functionalities of CVXlab, including 
Model class and a set of utility functions for managing model directories.
The module also includes metadata about the package such as authorship and 
licensing information.
"""
from importlib.metadata import version, PackageNotFoundError

from cvxlab.backend.model import Model
from cvxlab.defaults import Defaults
from cvxlab.support.model_directory import (
    create_model_dir,
    copy_user_defined_templates,
    transfer_setup_info_xlsx,
    handle_model_instance
)
from cvxlab.frontend import (
    run
)
installed_solvers = Defaults.NumericalSettings.get_installed_solvers


try:
    __version__ = version("cvxlab")
except PackageNotFoundError:
    __version__ = "Package not found"

__authors__ = "'Matteo V. Rocco'"
__license__ = "Apache License Version 2.0, (January 2004) <http://www.apache.org/licenses/>"
