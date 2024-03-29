import numpy as np
import pandas as pd
import scipy.stats as stats


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


def tril_weibull(
        l:float,
        alpha:float,
        shape:int,
) -> np.ndarray:
    """
    Generate a lower-triangular matrix containing the weibull probability density function
     
    Parameters:
        l: float
        alpha: float
        shape: int

    Returns:
        numpy ndarray containing the lower-triangular identity matrix.
    """

    matrix = np.zeros((shape,shape))

    # Populate lower-triangular matrix with Weibull distributed values
    for row in range(1,shape+1):
        for col in range(row):
            matrix[row-1, col] = stats.weibull_min.pdf(row, alpha, l)
            
    return matrix


def vect_weibull(
        l:float,
        alpha:float,
        start:float,
        shape:int,       
) -> np.ndarray:
    """
    Generate a vector containing a weibull probability density function
     
    Parameters:
        l: float
        alpha: float
        start:float
        shape: int

    Returns:
        numpy ndarray containing the vector.
    """

    vector = np.zeros((shape, 1))

    # Populate vector with Weibull distributed values
    for row in range(1,shape+1):
        vector[i-1] = weibull_min.pdf(row+start,shape,l)    

    return vector



