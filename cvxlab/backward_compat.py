"""Backward-compatibility utilities.

Expose a compact, readable API for translating deprecated keyword
arguments into the current form. Callers can invoke clearly-named
static methods, e.g.

    from cvxlab.backward_compat import BackwardCompat
    solution_mode = BackwardCompat.run_model_params(...)
    solver_kw   = BackwardCompat.run_params(...)

Keeping compatibility logic in one place keeps the rest of the codebase
clean and makes it easy to add further translations.
"""
from typing import Any, Dict, Optional

from cvxlab.log_exc.logger import Logger


class BackwardCompat:
    """Container for backward-compatibility helpers.

    Use as a clear namespace when addressing legacy translations, e.g.
    ``BackwardCompat.run_model_params(...)``. The methods are stateless
    and implemented as staticmethods so callers don't need to instantiate
    the class.
    """

    @staticmethod
    def run_model_params(
        solution_mode: str,
        kwargs: Dict[str, Any],
        logger: Optional[Logger] = None,
    ) -> str:
        """Normalize deprecated kwargs for ``Model.run_model``.

        - Maps deprecated ``integrated_problems`` -> ``solution_mode``.
        - Removes the deprecated key from ``kwargs`` in-place so it is
          not forwarded to the backend.

        Returns the (possibly updated) ``solution_mode`` string.
        """

        if 'integrated_problems' in kwargs:
            integrated_val = kwargs.pop('integrated_problems')
            try:
                integrated_flag = bool(integrated_val)
            except Exception:
                integrated_flag = False

            msg = (
                "Parameter 'integrated_problems' is deprecated; use 'solution_mode'. "
                "Mapping to 'integrated' if True, otherwise to 'parallel'."
            )

            if logger is not None and hasattr(logger, 'warning'):
                logger.warning(msg)
            else:
                # Fallback to stdout for extremely early import/use cases.
                print("WARNING: " + msg)

            solution_mode = 'integrated' if integrated_flag else 'parallel'

        return solution_mode

    @staticmethod
    def run_params(
        solver_kwargs: Dict[str, Any],
        logger: Optional[Logger] = None,
    ) -> Dict[str, Any]:
        """Normalize deprecated kwargs for ``interface.run``.

        If the old ``integrated_problems`` flag is present, translate it
        into the new ``solution_mode`` key and remove the deprecated key.

        Returns a new dict with the canonical kwargs.
        """
        new_kwargs = dict(solver_kwargs)
        solution_mode = BackwardCompat.run_model_params(
            solution_mode=new_kwargs.pop('solution_mode', 'parallel'),
            kwargs=new_kwargs,
            logger=logger,
        )
        new_kwargs['solution_mode'] = solution_mode
        return new_kwargs
