"""
util_functions.py 

@author: Matteo V. Rocco
@institution: Politecnico di Milano

This module provides various utility functions that are defined to support 
complex calculations in symbolic problems and generation of constants values,
such as generating special matrices, reshaping arrays, and calculating matrix 
inverses.
"""

from typing import Iterable
import numpy as np
import pandas as pd
import cvxpy as cp


def tril(dimension: int) -> np.array:
    """
    Generate a square matrix with ones in the lower triangular region
    (including the diagonal) and zeros elsewhere.

    Parameters:
        dimension (int): The size of the square matrix.

    Returns:
        np.ndarray: A square matrix of size 'dimension x dimension' with 
            ones in the lower triangular region and zeros elsewhere.

    Raises:
        ValueError: If passed dimension is not greater than zero.
        TypeError: If passed dimension is not an integer.
    """
    if not isinstance(dimension, int):
        raise TypeError("Passed dimension is not an integer.")

    if dimension <= 0:
        raise ValueError("Passed dimension must be greater than zero.")

    matrix = np.tril(np.ones((dimension, dimension)))
    np.fill_diagonal(matrix, 1)

    return matrix


def identity_rcot(related_dims_map: pd.DataFrame) -> np.ndarray:
    """
    Generate a special identity matrix from a map of columns and rows items 
    provided by a 'related_dims_map' dataframe. 

    Parameters:
        related_dims_map: pandas DataFrame containing rows and corresponding
            columns items.

    Returns:
        numpy ndarray containing the special identity matrix.

    Raises:
        ValueError: If 'related_dims_map' is not a DataFrame or if it does not 
            contain 'rows' and 'cols' columns.
    """
    if not isinstance(related_dims_map, pd.DataFrame):
        raise ValueError("'related_dims_map' must be a pandas DataFrame.")

    if 'rows' not in related_dims_map.columns or \
            'cols' not in related_dims_map.columns:
        raise ValueError(
            "'related_dims_map' must contain 'rows' and 'cols' columns labels.")

    related_dims_map['value'] = 1

    unique_rows = related_dims_map['rows'].drop_duplicates().tolist()
    unique_cols = related_dims_map['cols'].drop_duplicates().tolist()

    pivot_df = related_dims_map.pivot_table(
        index='rows',
        columns='cols',
        values='value',
        aggfunc='sum'
    ).fillna(0).astype(int)

    pivot_df_reorder = pivot_df.reindex(
        index=unique_rows,
        columns=unique_cols,
        fill_value=0
    )

    return pivot_df_reorder.values


def arange(
        shape_size: Iterable[int],
        start_from: int = 1,
        order: str = 'F',
) -> np.ndarray:
    """
    Generate a reshaped array with values ranging from 'start_from' to 
    'start_from + total_elements'.

    Parameters:
        shape_size (Iterable[int]): The shape of the output array.
        start_from (int, optional): The starting value for the range. 
            Defaults to 1.
        order (str, optional): The order of the reshaped array. 
            Defaults to 'F'.

    Returns:
        np.ndarray: The reshaped array with values ranging from 'start_from' 
            to 'start_from + total_elements'.

    Raises:
        ValueError: If 'shape_size' is not an iterable of integers, 
            'start_from' is not an integer, or 'order' is not a string.
        ValueError: If 'order' is not 'C' or 'F'.
    """
    if not isinstance(shape_size, Iterable) or \
            not all(isinstance(i, int) for i in shape_size):
        raise ValueError("'shape_size' must be an iterable of integers.")

    if not isinstance(start_from, int):
        raise ValueError("'start_from' must be an integer.")

    if not isinstance(order, str):
        raise ValueError("'order' must be a string.")

    if order not in ['C', 'F']:
        raise ValueError("'order' must be either 'C' or 'F'.")

    total_elements = np.prod(shape_size)
    values = np.arange(start_from, start_from+total_elements)
    reshaped_array = np.reshape(a=values, newshape=shape_size, order=order)

    return reshaped_array


def matrix_inverse(matrix: cp.Parameter | cp.Expression) -> cp.Parameter:
    """
    Calculates the inverse of a square matrix.

    Args:
        matrix (cp.Parameter | cp.Expression): The matrix to calculate the 
        inverse of.

    Returns:
        cp.Parameter: The inverse of the input matrix.

    Raises:
        TypeError: If the passed item is not a cvxpy Parameter or Expression.
        ValueError: If the passed matrix values are None, or if the passed 
            item is not a matrix, or if the passed item is not a square 
            matrix, or if the passed matrix is singular and cannot be inverted.
    """
    if not isinstance(matrix, (cp.Parameter, cp.Expression)):
        raise TypeError("Passed item must be a cvxpy Parameter or Expression.")

    matrix_val: np.ndarray = matrix.value

    if matrix_val is None:
        raise ValueError("Passed matrix values cannot be None.")

    if not isinstance(matrix_val, np.ndarray) or len(matrix_val.shape) != 2:
        raise ValueError("Passed item is not a matrix.")

    if matrix_val.shape[0] != matrix_val.shape[1]:
        raise ValueError("Passed item is not a square matrix.")

    try:
        inverse = np.linalg.inv(matrix_val)
    except np.linalg.LinAlgError as exc:
        raise ValueError(
            "Passed matrix is singular and cannot be inverted.") from exc

    return cp.Parameter(shape=matrix_val.shape, value=inverse)


def weibull_distribution(
        scale_factor: cp.Parameter,
        shape_factor: cp.Parameter,
        range_vector: cp.Constant,
        dimensions: int,
        rounding: int = 2,
) -> cp.Parameter:
    """
    Generates a Weibull probability density function configured either as a 
    one-dimensional vector or a two-dimensional matrix, based on specified 
    dimensions. This function primarily uses parameters from 'cvxpy' to enable 
    integration with optimization tasks and 'numpy' for handling numerical 
    operations.

    Parameters:
        scale_factor (cp.Parameter): A cvxpy Parameter object containing a 
            scalar value representing the scale parameter (λ) of the Weibull 
            distribution. This value must be positive.
        shape_factor (cp.Parameter): A cvxpy Parameter object containing a 
            scalar value representing the shape parameter (k) of the Weibull 
            distribution. Typically, this value must be positive to define the 
            distribution correctly.
        range_vector (cp.Constant): A cvxpy Constant object that includes an 
            array of values over which the Weibull PDF is computed. The range 
            should be a one-dimensional array of non-negative values.
        dimensions (int): Determines the output dimension of the Weibull PDF:
            1 for a vector output,
            2 for a matrix output where each subsequent column is a downward 
                rolled version of the Weibull PDF vector.
        rounding (int, optional): Number of decimal places to which the 
            computed Weibull PDF values are rounded. Defaults to 2.

    Returns:
        cp.Parameter: A cvxpy Parameter object that contains the Weibull PDF 
            in the specified dimension (vector or matrix). This can be 
            directly used in further cvxpy optimizations.

    Raises:
        ValueError: If any of the input parameters (scale_factor, shape_factor,
            or range_vector) is None, or if their contained values do not meet 
            the expected requirements (e.g., non-scalar for scale or shape 
            factors, or if dimensions is not 1 or 2).
    """
    if not isinstance(scale_factor, cp.Parameter) or \
            not isinstance(shape_factor, cp.Parameter) or \
            not isinstance(range_vector, cp.Constant):
        raise TypeError(
            "scale_factor and shape_factor must be cvxpy.Parameters, "
            "range_vector must be cvxpy.Constant.")

    # extract values from cvxpy parameters
    sc: np.ndarray = scale_factor.value
    sh: np.ndarray = shape_factor.value
    rx: np.ndarray = range_vector.value

    # checks
    if sc is None or sh is None or rx is None:
        raise ValueError(
            "Values assigned to scale_factor, shape_factor and range_vector "
            "cannot be None.")

    if not isinstance(sc, np.ndarray) or \
            not isinstance(sh, np.ndarray) or \
            not isinstance(rx, np.ndarray):
        raise TypeError(
            "Scale factor, shape factor, and range must be numpy arrays.")

    err_msg = []

    # WARNING: non è possibile avere sc e sh funzioni del tempo (rx)
    if not len(sc) == 1:
        err_msg.append(
            "Weibull scale factor must be a scalar. "
            f"Passed dimension: '{len(sc)}'.")

    if not len(sh) == 1:
        err_msg.append(
            "Weibull shape factor must be a scalar. "
            f"Passed dimension: '{len(sh)}'.")

    if dimensions not in [1, 2]:
        err_msg.append(
            "Output of Weibull distribution must be '1' (vector) "
            f"or 2 (matrix). Passed value: '{dimensions}'")

    if not isinstance(rounding, int) or rounding < 0:
        err_msg.append(
            "Rounding parameter must be an integer greater than or equal to zero."
        )

    if err_msg:
        raise ValueError("\n".join(err_msg))

    # defining Weibull function range
    weib_range = int(sc[0, 0]) * 2
    if weib_range <= len(rx):
        weib_range = len(rx)

    rx_weib = np.arange(1, weib_range+1).reshape((weib_range, 1))

    weib_dist = sh/sc * (rx_weib/sc)**(sh-1) * np.exp(-((rx_weib/sc)**sh))
    weib_dist = np.round(weib_dist, rounding)

    # re-scale weib_dist to get the sum equal to 1
    weib_dist /= np.sum(weib_dist)

    # reshape weib_dist to match the lenght of range
    weib_dist = weib_dist[:len(rx)]

    # generates a vector of Weibull probability distribution
    if dimensions == 1:
        weib_parameter = cp.Parameter(shape=(len(rx), 1))
        weib_parameter.value = weib_dist

    # generates a matrix of Weibull probability distribution
    # each column of the matrix is the original vector rolled down
    # WARNING: per implementare un lifetime che varia di anno in anno, bisogna
    # ricalcolare weib_dist ogni anno!
    elif dimensions == 2:
        weib_parameter = cp.Parameter(shape=(len(rx), len(rx)))
        weib_dist_matrix = np.zeros((len(rx), len(rx)))

        for i in range(len(rx)):
            weib_dist_rolled = np.roll(weib_dist, i)
            weib_dist_rolled[:i] = 0
            weib_dist_matrix[:, i] = weib_dist_rolled.flatten()

        weib_parameter.value = weib_dist_matrix

    return weib_parameter
