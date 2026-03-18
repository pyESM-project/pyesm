"""Display helpers: headers, separators, and menu rendering."""
import os

SEPARATOR = "-" * 49
_LOG_MARKER = f"{'CVXLAB logs ':─<49}"


def clear_screen() -> None:
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header() -> None:
    print(
        f"\n{SEPARATOR}"
        "\n             CVXlab User Interface              "
        f"\n{SEPARATOR}\n"
    )


def print_separator() -> None:
    print(f"\n{SEPARATOR}")


def print_menu(labels: list[str]) -> None:
    """Print a numbered list of action labels.

    Keys are assigned automatically: 1, 2, 3, ...
    """
    print("Operational modes: (type 'exit' to quit)\n")
    for idx, label in enumerate(labels, start=1):
        print(f"{idx}. {label}")


def prompt_choice(n_options: int) -> str:
    """Ask the user to pick a menu entry. Returns the raw string."""
    return input(
        f"\nSelect operational mode "
        f"(Enter values between 1 and {n_options}): "
    ).strip()


def print_log_start() -> None:
    print(f"\n{'CVXLAB logs below ' :─<49}")


def print_log_end() -> None:
    print(f"{'CVXLAB logs above ' :─<49}")


def exit_msg() -> None:
    print("\nExiting CVXlab. Goodbye!\n")
