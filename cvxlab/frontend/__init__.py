"""CVXlab guided user interface (frontend package).

Public API::

    from cvxlab.frontend import guided_session
    guided_session(model_dir_name='model', log_level='debug')
"""
from cvxlab.frontend.cli import run_interface

__all__ = ["run_interface"]
