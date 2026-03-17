"""CVXlab guided user interface (frontend package).

Public API::

    from cvxlab.frontend import run_interface
    run_interface(model_dir_name='model', log_level='debug')
"""
from cvxlab.frontend.interface import run_interface

__all__ = ["run_interface"]
