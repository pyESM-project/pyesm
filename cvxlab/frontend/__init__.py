"""CVXlab guided user interface (frontend package).

Public API::

    from cvxlab.frontend import run
    run(model_dir_name='model', log_level='debug')
"""
from cvxlab.frontend.interface import run

__all__ = ["run"]
