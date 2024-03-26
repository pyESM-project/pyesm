import numpy as np


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
