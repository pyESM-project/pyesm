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


def arange(
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

    Example:
        >>> scale_param = cp.Parameter(value=np.array([1.5]))
        >>> shape_param = cp.Parameter(value=np.array([2.0]))
        >>> range_vals = cp.Constant(value=np.array([0, 1, 2, 3, 4, 5]))
        >>> weib_dist = weibull_distribution(scale_param, shape_param, range_vals, 1)
        >>> print(weib_dist.value)
        [[0.  , 0.25, 0.49, 0.69, 0.84, 0.94]]
    """
    # extract values from cvxpy parameters
    sc = scale_factor.value
    sh = shape_factor.value
    rx = range_vector.value

    # checks
    if sc is None or sh is None or rx is None:
        raise ValueError(
            "Scale factor, shape factor, or range cannot be None.")

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

    if err_msg != []:
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
