"""Module defining utility functions for text processing and evaluation.

This module includes functions to evaluate strings representing data structures,
add necessary brackets or quotes, convert string representations of booleans,
and extract tokens from expressions while handling parentheses balancing.
"""
import ast
import re
from typing import Any, Iterable, List, Optional


def is_iterable(value: str) -> bool:
    """Check if a string represents an iterable (list, tuple, or dict).

    This function checks if the input string starts with an opening
    bracket, brace, or parenthesis, indicating that it may represent
    a list, dictionary, or tuple.

    Args:
        value (str): The string to check.

    Returns:
        bool: True if the string represents an iterable, False otherwise.

    Raises:
        TypeError: If the input is not a string.
        ValueError: If the string has unmatched parentheses, brackets, or braces.
    """
    if not isinstance(value, str):
        raise TypeError(f'Passed value {value} must be a string.')

    stack = []
    matching = {')': '(', ']': '[', '}': '{'}

    for char in value:
        if char in matching.values():
            stack.append(char)
        elif char in matching.keys():
            if stack == [] or matching[char] != stack.pop():
                raise ValueError(f"Unmatched parentheses in string: {value}")

    if stack:
        raise ValueError(f"Unmatched parentheses in string: {value}")

    return bool(re.match(r'^\s*[\{\[\(]', value))


def add_brackets(value: str) -> Optional[str]:
    """Check if a string represents a list or dict without brackets and add them.

    This function checks if the input string represents a list or dictionary
    structure without the necessary opening and closing brackets. If so, it adds
    the appropriate brackets and returns the modified string. If the string
    already contains brackets or does not represent a list or dictionary, it
    returns the string unchanged.

    Args:
        value (str): The string to check and potentially modify.

    Returns:
        Optional[str]: The modified string with added brackets if necessary,
            or the original string if no modification was needed.

    Raises:
        TypeError: If the input is not a string.
        ValueError: If the string has unmatched parentheses, brackets, or braces.
    """
    if not isinstance(value, str):
        raise TypeError(f'Passed value {value} must be a string.')

    # check for unmatched brackets
    stack = []
    matching = {')': '(', ']': '[', '}': '{'}
    for char in value:
        if char in matching.values():
            stack.append(char)
        elif char in matching.keys():
            if not stack or matching[char] != stack.pop():
                raise ValueError(f"Unmatched parentheses in string: {value}")
    if stack:
        raise ValueError(f"Unmatched parentheses in string: {value}")

    # check if the string is a list or dict without brackets
    if ',' in value and not re.match(r'^\s*[\{\[\(]', value):
        items = [item.strip() for item in value.split(',')]

        if ':' in items[0]:
            # handle comma-separated pairs of key-value items
            value = '{' + ', '.join(items) + '}'
        else:
            # handle comma-separated items
            value = '[' + ', '.join(items) + ']'

    # check if the string is a dict without brackets
    if ':' in value and not re.match(r'^\s*[\{\[\(]', value):
        items = [item.strip() for item in value.split(':')]
        value = '{' + ': '.join(items) + '}'

    return value


def add_quotes(value: str) -> str:
    """Convert all unquoted symbols into quoted symbols.

    This function processes a string that represents a list or dictionary and
    ensures that all unquoted symbols are enclosed in quotes. It handles
    various delimiters such as commas, colons, brackets, braces, and parentheses.

    Args:
        value (str): The string to process.

    Returns:
        str: The modified string with all unquoted symbols enclosed in quotes.

    Raises:
        TypeError: If the input is not a string.
    """
    if not isinstance(value, str):
        raise TypeError(f'Passed value {value} must be a string.')

    # Split the string by commas and strip whitespace
    items = [
        item.strip()
        for item in re.split(r'(\s*[:,\[\]\{\}\(\)]\s*)', value)
    ]

    # Enclose each item in quotes if not already quoted and not a symbol
    quoted_items = []
    for item in items:
        if item and \
                not re.match(r'^\s*[:,\[\]\{\}\(\)]\s*$', item) and \
                not (item.startswith("'") and item.endswith("'")) and \
                not re.match(r'^-?\d+(\.\d+)?$', item):
            item = f"'{item}'"
        quoted_items.append(item)

    # Join the quoted items back into a single string
    result = ''.join(quoted_items)

    # Add spaces after commas and colons
    for item in [',', ':']:
        result = result.replace(f"{item}", item+' ')

    return result


def evaluate_bool(value: Any) -> Any:
    """Check and convert str representing bool to bool.

    This function parses a generic expression and find str representing bool 
    (in bool_map dictionary) and converts them to bool.

    Args:
        value (Any): The value to check and potentially convert.

    Returns:
        Any: The converted bool value if the input was a str representing bool,
            otherwise returns the input value unchanged.
    """
    bool_map = {
        'true': True, 'True': True, 'TRUE': True,
        'false': False, 'False': False, 'FALSE': False,
    }

    if isinstance(value, str):
        return bool_map.get(value, value)
    elif isinstance(value, dict):
        return {k: evaluate_bool(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [evaluate_bool(item) for item in value]
    elif isinstance(value, Iterable):
        return type(value)(evaluate_bool(item) for item in value)
    else:
        return value


def process_str(value: Any) -> Any:
    """Process a string to evaluate its content.

    This function processes a string to determine if it represents a list,
    dictionary, or boolean value. It adds necessary brackets or quotes,
    evaluates the string to convert it into the corresponding Python data
    structure, and converts string representations of booleans to actual
    boolean values.

    Args:
        value (Any): The value to process, which may be a string or other type.

    Returns:
        Any: The processed value, which may be a list, dictionary, boolean,
            or the original value if no processing was needed.

    Raises:
        ValueError: If the string is malformed and cannot be evaluated.
    """
    # if value is not a string, return it as is
    if not isinstance(value, str):
        return value

    # add brackets in case value is a string representing list | dict without brackets
    value = add_brackets(value)

    # in case the string is a list | dict, add quotes to all items and evaluate it
    if is_iterable(value):
        value = add_quotes(value)
        try:
            value = ast.literal_eval(value)
        except ValueError as e:
            raise ValueError(
                f"Malformed string cannot be evaluated: '{value}'") from e

    # in case there are str representing bool, convert to bool
    value = evaluate_bool(value)

    return value


def balanced_parentheses(parentheses_list: List[str]) -> bool:
    """Check if the parentheses in a list are balanced.

    This function checks if the parentheses in the input list are balanced.
    It uses a stack to track opening parentheses and ensures that each closing
    parenthesis matches the most recent opening parenthesis.

    Args:
        parentheses_list (List[str]): A list of parentheses characters to check.

    Returns:
        bool: True if the parentheses are balanced, False otherwise.
    """
    stack = []
    matching = {')': '('}

    for char in parentheses_list:
        if char in matching.values():
            stack.append(char)
        elif char in matching.keys():
            if not stack or matching[char] != stack.pop():
                return False

    return not stack


def extract_tokens_from_expression(
    expression: str,
    pattern: str | List[str],
    tokens_to_skip: Optional[List[str]] = None,
    avoid_duplicates: Optional[bool] = False,
) -> List[str]:
    """Extract tokens from a symbolic expression.

    This function parses and extracts variable names from a symbolic expression, 
    excluding any non-allowed tokens.
    This method uses regular expressions to identify potential variable names
    within the given expression and filters out any tokens that are designated
    as non-allowed, such as mathematical operators or reserved keywords.

    Args:
        expression (str): The symbolic expression from which to extract
            variable names.
        pattern (str | List[str]): The regular expression pattern(s) to use for
            matching tokens' names. This can be a single pattern or a list of
            patterns.
        tokens_to_skip (Optional[List[str]]): A list of tokens to skip when
            extracting variable names. Default is None.
        avoid_duplicates (Optional[bool]): if True, it eliminates duplicates from
            the resulting list by preserving items order.

    Returns:
        List[str]: A list of valid variable names extracted from the expression.

    Raises:
        TypeError: If the input types are incorrect.
    """
    if tokens_to_skip is None:
        tokens_to_skip = []
    else:
        if not isinstance(tokens_to_skip, list):
            raise TypeError(
                f'tokens_to_skip {tokens_to_skip} must be a list.')
        for token in tokens_to_skip:
            if not isinstance(token, str):
                raise TypeError(
                    f'Each token in tokens_to_skip {tokens_to_skip} must be a string.')

    if not isinstance(expression, str):
        raise TypeError(f'Passed expression {expression} must be a string.')

    if not isinstance(pattern, (str, list)):
        raise TypeError(
            f'pattern {pattern} must be a string or a list of strings.')

    if not isinstance(avoid_duplicates, bool):
        raise TypeError(
            f'avoid_duplicates {avoid_duplicates} must be a bool.'
        )

    tokens = []

    if isinstance(pattern, list):
        for pat in pattern:
            tokens += re.findall(pat, expression)
    elif isinstance(pattern, str):
        tokens = re.findall(pattern, expression)

    allowed_tokens = [token for token in tokens if token not in tokens_to_skip]

    if avoid_duplicates:
        allowed_tokens = list(dict.fromkeys(allowed_tokens))

    return allowed_tokens
