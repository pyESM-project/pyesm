"""CLI loop engine and public entry-point function."""
from __future__ import annotations

import os
import sys
from typing import Any, List

from cvxlab.frontend.config import SessionConfig
from cvxlab.frontend.display import (
    clear_screen,
    print_header,
    print_menu,
    print_separator,
    prompt_choice,
)
from cvxlab.frontend.menu import Action, MAIN_MENU
from cvxlab.frontend.state import ModelState
from cvxlab.log_exc.exceptions import CVXLabError


def run_menu(
    actions: List[Action],
    config: SessionConfig,
    state: ModelState,
) -> None:
    """Generic menu loop that works for any list of ``Action`` objects.

    Handles sub-menus via recursion when ``action.children`` is set.
    Backend exceptions (``CVXLabError`` and subclasses) are caught so that
    only the package logger output is visible — no raw tracebacks.
    """
    labels = [a.label for a in actions]
    n = len(actions)

    while True:
        print_menu(labels)
        choice = prompt_choice(n)

        if choice.lower() in ('exit', ''):
            print("\nExiting CVXlab. Goodbye!\n")
            break

        if not choice.isdigit() or not (1 <= int(choice) <= n):
            print(f"\nERROR. Valid selections: 1 to {n}.\n")
            continue

        action = actions[int(choice) - 1]

        try:
            if action.children:
                run_menu(action.children, config, state)
            else:
                action.handler(config, state)
        except CVXLabError:
            # Already logged by the backend logger — just return to menu.
            pass

        print_separator()


def run_interface(**kwargs: Any) -> None:
    """Launch the CVXlab guided user interface.

    All keyword arguments are forwarded to ``SessionConfig``.  If
    ``main_dir_path`` is not provided it defaults to the current
    working directory.

    Example::

        import cvxlab
        cvxlab.guided_session(
            model_dir_name='my_model',
            main_dir_path='/path/to/models',
            log_level='debug',
            solver='ECOS',
        )
    """
    kwargs.setdefault('main_dir_path', os.getcwd())
    config = SessionConfig(**kwargs)
    state = ModelState()

    clear_screen()
    print_header()
    run_menu(MAIN_MENU, config, state)
