from typing import Tuple
import numpy as np
import pandas as pd
import cvxpy as cp


def tril(dimension: int) -> np.ndarray:
    """
    Generate a square matrix with ones in the lower triangular region
    (including the diagonal) and zeros elsewhere.

    Parameters:
        dimension (int): The size of the square matrix.

    Returns:
        np.ndarray: A square matrix of size 'dimension x dimension' with 
            ones in the lower triangular region and zeros elsewhere.
    """
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
    """
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


def range(
        shape_size: Tuple[int],
        start_from: int = 1,
        order: str = 'F',
) -> np.ndarray:
    """
    Generate a reshaped array with values ranging from `start_from` to 
    `start_from + total_elements`.

    Parameters:
        shape_size (Tuple[int]): The shape of the output array.
        start_from (int, optional): The starting value for the range. 
            Defaults to 1.
        order (str, optional): The order of the reshaped array. 
            Defaults to 'F'.

    Returns:
        np.ndarray: The reshaped array with values ranging from `start_from` 
            to `start_from + total_elements`.
    """

    total_elements = np.prod(shape_size)
    values = np.arange(start_from, start_from+total_elements)
    reshaped_array = values.reshape(shape_size, order=order)

    return reshaped_array


def weibull_distribution(
        scale,
        shape,
        range,
        dimensions=1,
        rounding=2,
):
    """
    Generate a weibull probability density function as a vector or a matrix.
    """
    # extract values from cvxpy parameters
    sc = scale.value
    sh = shape.value
    rx = range.value

    # calculate Weibull probability density function
    # use a custom range larger than the highest scale
    rx_weib_length = int(np.max(rx)*2)
    rx_weib = np.arange(1, rx_weib_length+1).reshape((rx_weib_length, 1))

    weib_dist = sh/sc * (rx_weib/sc)**(sh-1) * np.exp(-((rx_weib/sc)**sh))
    weib_dist = np.round(weib_dist, rounding)

    # re-scale weib_dist to get the sum equal to 1
    if any(list(np.sum(weib_dist, 0) != 1)):
        weib_dist = weib_dist / np.sum(weib_dist, 0)

    weib_dist = weib_dist[:len(rx)]

    if dimensions == 1:
        weib_parameter = cp.Parameter((len(rx), 1))
        weib_parameter.value = weib_dist

    elif dimensions == 2:
        pass  # da qui implementare weibull bidimensionale np.roll

    else:
        raise KeyError(
            f"Wrong input passed to user-defined weibull_distribution "
            "'weib()' function. Valid dimensions are 1 (vector), 2 (matrix).")

    return weib_parameter
