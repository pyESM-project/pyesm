"""Input parsing and display helpers for the guided user interface."""
import ast
import os

from typing import Any, Callable

from cvxlab.frontend.gui_defaults import GuiDefaults


MISSING = object()


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in ('true', 't', 'yes', 'y', '1'):
        return True
    if normalized in ('false', 'f', 'no', 'n', '0'):
        return False
    raise ValueError(GuiDefaults.BOOLEAN_REQUIRED)


def parse_literal(value: str) -> Any:
    return ast.literal_eval(value)


def parse_string_or_literal(value: str) -> Any:
    stripped = value.strip()
    if stripped.startswith(('[', '{', '(', '"', "'")):
        return ast.literal_eval(stripped)
    return stripped


def parse_bool_or_literal(value: str) -> Any:
    try:
        return parse_bool(value)
    except ValueError:
        return parse_literal(value)


PARSERS: dict[str, Callable[[str], Any]] = {
    'string': str,
    'bool': parse_bool,
    'literal': parse_literal,
    'string_or_literal': parse_string_or_literal,
    'bool_or_literal': parse_bool_or_literal,
    'float': float,
    'int': int,
}


def ask(
        label: str,
        default: Any = MISSING,
        parser: str = 'string',
        choices: tuple[Any, ...] | None = None,
) -> Any:
    """Request, parse, and validate one interactive value."""
    while True:
        default_text = "" if default is MISSING else f" [{default!r}]"
        raw_value = input(f"{label}{default_text}: ").strip()

        if not raw_value:
            if default is MISSING:
                print(GuiDefaults.REQUIRED_VALUE)
                continue
            value = default
        else:
            try:
                value = PARSERS[parser](raw_value)
            except (TypeError, ValueError, SyntaxError) as error:
                print(GuiDefaults.INVALID_VALUE.format(error=error))
                continue

        if choices is not None and value not in choices:
            print(GuiDefaults.INVALID_CHOICE.format(choices=list(choices)))
            continue

        return value


def clear_screen() -> None:
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header() -> None:
    print(
        f"\n{GuiDefaults.SEPARATOR}\n"
        f"{GuiDefaults.HEADER}\n"
        f"{GuiDefaults.SEPARATOR}\n"
    )


def print_separator() -> None:
    print(f"\n{GuiDefaults.SEPARATOR}")


def print_menu(labels: list[str], is_submenu: bool = False) -> None:
    print(GuiDefaults.MENU_TITLE)
    for index, label in enumerate(labels, start=1):
        print(f"{index}. {label}")
    if is_submenu:
        print(GuiDefaults.BACK_OPTION)
    print(GuiDefaults.QUIT_OPTION)


def prompt_choice(n_options: int, is_submenu: bool = False) -> str:
    alternatives = f"1 to {n_options}"
    if is_submenu:
        alternatives += ", 'back'"
    alternatives += ", or 'quit'"
    return input(
        GuiDefaults.SELECT_ACTION.format(alternatives=alternatives)
    ).strip()


def print_log_start() -> None:
    print(f"\n{GuiDefaults.LOG_START}")


def print_log_end() -> None:
    print(GuiDefaults.LOG_END)
