"""Backward-compatibility utilities.

Expose a compact, readable API for translating deprecated keyword
arguments into the current form. Callers can import the module-level
instance ``backwardCompat`` and invoke clearly-named methods, e.g.

    from cvxlab.backward_compat import backwardCompat
    solution_mode, kwargs = backwardCompat.run_model_params(...)

Keeping compatibility logic in one place keeps the rest of the codebase
clean and makes it easy to add further translations.
"""
from typing import Any, Dict, Optional, Tuple


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
        logger: Optional[Any] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """Normalize deprecated kwargs for ``Model.run_model``.

        - Maps deprecated ``integrated_problems`` -> ``solution_mode``.
        - Removes the deprecated key from ``kwargs`` so it is not forwarded.

        Returns (solution_mode, kwargs).
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

        return solution_mode, kwargs

    @staticmethod
    def normalize_solver_kwargs(solver_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize frontend `solver` kwargs for backward compatibility.

        If the old `integrated_problems` flag is present, translate it into
        the new `solution_mode` key and remove the deprecated key.
        """
        # Use run_model_params to translate the deprecated flag and get the
        # canonical `solution_mode` value.
        solution_mode, new_kwargs = BackwardCompat.run_model_params(
            solution_mode=solver_kwargs.get('solution_mode', 'parallel'),
            kwargs=dict(solver_kwargs),
            logger=None,
        )

        new_kwargs['solution_mode'] = solution_mode
        return new_kwargs
