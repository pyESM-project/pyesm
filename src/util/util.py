import pprint as pp
import pandas as pd


def prettify(item: dict) -> None:
    """Print a dictionary in a human-readable format in the terminal

    Args:
        item (dict): a generic dictionary

    Raises:
        TypeError: If the argument is not a dictionary.
    """
    if not isinstance(item, dict):
        raise TypeError('Function argument should be a dictionary.')
    print(pp.pformat(item))


def find_dict_depth(item) -> int:
    """Find and return the depth of a generic dictionary

    Args:
        item (dict): a generic dictionary

    Returns:
        int: depth of the dictionary
    """
    if not isinstance(item, dict) or not item:
        return 0
    return 1 + max(find_dict_depth(v) for k, v in item.items())