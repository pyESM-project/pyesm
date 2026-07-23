"""Module with user defined functions defined as model's constants.

This module provides various utility functions that are defined to support 
complex calculations in symbolic problems through generation of constants types,
such as generating special matrices (positive semidefinite matrices).

Functions are registered as constants in Defaults class, and actual constants data
are generated when generating variables (see backend.Variable.define_constant() method).
"""
from typing import Iterable, List

import numpy as np

from cvxlab.log_exc import exceptions as exc

_CONSTANTS_REGISTRY = {}


def constant(name: str) -> callable:
    """Decorator to register a constant generation function.

    Args:
        name (str): The name of the constant to register.

    Returns:
        callable: The decorated function.
    """
    def decorator(func: callable) -> callable:
        _CONSTANTS_REGISTRY[name] = func
        return func
    return decorator


@constant('sum_vector')
def sum_vector(dimension: List[int]) -> np.ndarray:
    """Define a vector of ones for matrix summation operations.

    Args:
        dimension (List[int]): The dimension of the vector (rows, cols).

    Returns:
        np.ndarray: A vector of ones with the specified dimension.

    Raises:
        exc.SettingsError: If passed dimension is not a list containing integers,
            or if it does not represent a vector (i.e., at least one element 
            must be equal to 1).
    """
    if not isinstance(dimension, List) or not \
            all(isinstance(i, int) for i in dimension):
        raise exc.SettingsError(
            "Constant definition | Summation vector constant accepts as argument"
            "only a list of integers.")

    if len(dimension) != 2 or not any(i == 1 for i in dimension):
        raise exc.SettingsError(
            "Constant definition | Summation vector can be defined as "
            "vector only (one dimension). Check variable shape.")

    return np.ones(dimension)


@constant('identity')
def identity_matrix(dimension: List[int]) -> np.array:
    """Generate a square identity matrix of size n x n.

    Args:
        dimension (List[int]): Either [n, n] for an n by n matrix, or [n, 1] or 
            [1, n] for a vector.

    Returns:
        np.ndarray: An n x n identity matrix.

    Raises:
        exc.SettingsError: If 'dimension' is not [n, n] with equal positive ints,
            or a vector [n, 1] or [1, n].
    """
    if not isinstance(dimension, list) or len(dimension) != 2 \
            or not all(isinstance(i, int) for i in dimension):
        raise exc.SettingsError(
            "Constant definition | Identity matrix expects a list of two integers "
            "[n, n] or a vector [n, 1] or [1, n].")

    if dimension[0] == dimension[1]:
        return np.eye(dimension[0])

    if 1 in dimension:
        size = max(dimension)
        return np.eye(size)

    raise exc.SettingsError(
        "Constant definition | Identity matrix requires either two equal integers "
        f"[n, n] or a vector [n, 1] or [1, n]. Passed dimension: {dimension}")


@constant('set_length')
def set_length(dimension: List[int]) -> np.array:
    """Define the length of a set as a constant.

    Args:
        dimension (List[int]): The dimension of the vector (rows, cols).

    Returns:
        np.ndarray: A 1x1 array (scalar) containing the length of the set.

    Raises:
        exc.SettingsError: If passed dimension is not a list containing integers,
            or if it does not represent a vector (i.e., at least one element 
            must be equal to 1).
    """
    if not isinstance(dimension, List) or not \
            all(isinstance(i, int) for i in dimension):
        raise exc.SettingsError(
            "Constant definition | Set lenght constant accepts as argument"
            "only a list of integers.")

    if len(dimension) != 2 or not any(i == 1 for i in dimension):
        raise exc.SettingsError(
            "Constant definition | Set lenght constant accetps as argument a list "
            "representing a vector only (one dimension). Check variable shape.")

    dimension_size = np.array(np.max(dimension))
    if dimension_size.ndim == 0:
        dimension_size = dimension_size.reshape(-1, 1)

    return dimension_size


def arange(dimension: List[int], start_from: int, order: str = 'F') -> np.array:
    """Define a reshaped range array.

    Generate a reshaped array with values ranging from 'start_from' to 
    'start_from + total_elements'.
    Notice that this function is not directly registered as a constant, but it 
    is used to define other constants (e.g., arange_0)

    Args:
        shape_size (Iterable[int]): The shape of the output array.
        start_from (int, optional): The starting value for the range.
        order (str, optional): The order of the reshaped array. Defaults to 'F'.

    Returns:
        np.ndarray: The reshaped array with values ranging from 'start_from' 
            to 'start_from + total_elements'.

    Raises:
        exc.SettingsError: If passed dimension is not a list containing integers.
        ValueError: If 'start_from' is not an integer.
        ValueError: If 'order' is not a string or not in ['C', 'F'].
    """
    if not isinstance(dimension, Iterable) or \
            not all(isinstance(i, int) for i in dimension):
        raise exc.SettingsError(
            "Constant definition | Range constant accepts as argument only a "
            "list of integers.")

    if not isinstance(start_from, int):
        raise ValueError("'start_from' must be an integer.")

    if not isinstance(order, str):
        raise ValueError("'order' must be a string.")

    if order not in ['C', 'F']:
        raise ValueError("'order' must be either 'C' or 'F'.")

    total_elements = np.prod(dimension)
    values = np.arange(start_from, start_from+total_elements)
    reshaped_array = values.reshape(dimension, order=order)

    return reshaped_array


@constant('arange_0')
def arange_0(dimension: List[int]) -> np.ndarray:
    """Define a reshaped range array starting from zero."""
    return arange(dimension=dimension, start_from=0)


@constant('arange_1')
def arange_1(dimension: List[int]) -> np.ndarray:
    """Define a reshaped range array starting from one."""
    return arange(dimension=dimension, start_from=1)


@constant('lower_triangular')
def lower_triangular_matrix(dimension: List[int]) -> np.array:
    """Define a lower triangular matrix.

    Generate a square matrix with ones in the lower triangular region
    (including the diagonal) and zeros elsewhere.

    Args:
        dimension (List[int]): The dimension of the matrix row/col.

    Returns:
        np.ndarray: A square matrix with ones in the lower triangular region 
            and zeros elsewhere.

    Raises:
        exc.SettingsError: If passed dimension is not a list containing integers,
            or if it does not represent a vector (i.e., at least one element 
            must be equal to 1).
    """
    if not isinstance(dimension, List) or not \
            all(isinstance(i, int) for i in dimension):
        raise exc.SettingsError(
            "Constant definition | Lower triangular matrix accepts as argument"
            "only a list of integers.")

    if len(dimension) != 2 or not any(i == 1 for i in dimension):
        raise exc.SettingsError(
            "Constant definition | Lower triangular matrix accetps as argument "
            "a list representing a vector only (one dimension). Check variable shape.")

    size = max(dimension)
    matrix = np.tril(np.ones((size, size)))
    np.fill_diagonal(matrix, 1)

    return matrix


CONSTANTS = _CONSTANTS_REGISTRY
