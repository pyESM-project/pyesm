import pprint as pp


def prettify(item: dict):
    """Print a dictionary in a human-readable format in the terminal

    Args:
        item (dict): a generic dictionary
    """
    if not isinstance(item, dict):
        raise TypeError('Function argument should be a dictionary.')
    print(pp.pformat(item))
