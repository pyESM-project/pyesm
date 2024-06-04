"""
test_util_functions.py 

@author: Matteo V. Rocco
@institution: Politecnico di Milano

This module contains tests for the functions in the 'esm.support.util_functions' 
module.
"""


import pytest
import pandas as pd
import numpy as np

from esm.support.util_functions import *


def test_tril():
    """
    Test the tril function.
    This function tests the tril function with valid and invalid input, and 
    checks if the function correctly generates a lower triangular matrix with 
    ones and handles invalid input.
    """

    # valid input
    matrix = tril(3)
    expected_matrix = np.array([
        [1, 0, 0],
        [1, 1, 0],
        [1, 1, 1]
    ])
    assert np.array_equal(matrix, expected_matrix)

    # valid input
    matrix = tril(1)
    expected_matrix = np.array([[1.]])
    assert np.array_equal(matrix, expected_matrix)

    # invalid input
    with pytest.raises(TypeError):
        tril('not an integer')

    with pytest.raises(ValueError):
        tril(-1)


def test_identity_rcot():
    """
    Test the identity_rcot function.
    This function tests the identity_rcot function with valid and invalid 
    input, and checks if the function correctly generates a special identity 
    matrix and handles invalid input.
    """

    # valid input
    df = pd.DataFrame({
        'rows': ['a', 'b', 'c'],
        'cols': ['x', 'y', 'z']
    })
    matrix = identity_rcot(df)
    expected_matrix = np.array([
        [1, 0, 0],
        [0, 1, 0],
        [0, 0, 1]
    ])
    assert np.array_equal(matrix, expected_matrix)

    # valid input
    df = pd.DataFrame({
        'rows': ['a', 'b', 'b', 'c', 'c'],
        'cols': ['x', 'y1', 'y2', 'z1', 'z2']
    })
    matrix = identity_rcot(df)
    expected_matrix = np.array([
        [1, 0, 0, 0, 0],
        [0, 1, 1, 0, 0],
        [0, 0, 0, 1, 1]
    ])
    assert np.array_equal(matrix, expected_matrix)

    # valid input
    df = pd.DataFrame({
        'rows': ['a', 'a', 'a'],
        'cols': ['x1', 'x2', 'x3']
    })
    matrix = identity_rcot(df)
    expected_matrix = np.array([[1, 1, 1]])
    assert np.array_equal(matrix, expected_matrix)

    # invalid input
    with pytest.raises(ValueError):
        identity_rcot('not a dataframe')

    with pytest.raises(ValueError):
        df = pd.DataFrame({
            'not_rows': ['a', 'b', 'c'],
            'not_cols': ['x', 'y', 'z']
        })
        identity_rcot(df)


def test_arange():
    """
    Test the arange function.
    This function tests the 'arange' function with valid and invalid input, 
    and checks if the function correctly generates a reshaped array and 
    handles invalid input.
    """

    # valid input
    array = arange((2, 3), 1, 'F')
    expected_array = np.array([
        [1, 3, 5],
        [2, 4, 6]
    ])
    assert np.array_equal(array, expected_array)

    # valid input
    array = arange((2, 3), 1, 'C')
    expected_array = np.array([
        [1, 2, 3],
        [4, 5, 6]
    ])
    assert np.array_equal(array, expected_array)

    # valid input
    expected_array = np.array([[1, 2, 3]])
    array1 = arange((1, 3), 1, 'C')
    assert np.array_equal(array1, expected_array)
    array2 = arange((1, 3), 1, 'F')
    assert np.array_equal(array2, expected_array)

    # invalid input
    with pytest.raises(ValueError):
        arange('not an iterable', 1, 'F')

    with pytest.raises(ValueError):
        arange((2, 3), 'not an integer', 'F')

    with pytest.raises(ValueError):
        arange((2, 3), 1, 'not C or F')


def test_power():
    # scalar base and exponent
    base = cp.Parameter(shape=(1,), value=np.array([2]))
    exponent = cp.Parameter(shape=(1,), value=np.array([3]))
    result = power(base, exponent)
    assert np.allclose(result.value, np.array([8]))

    # scalar base and vector exponent
    base = cp.Parameter(shape=(1,), value=np.array([2]))
    exponent = cp.Parameter(shape=(3,), value=np.array([1, 2, 3]))
    result = power(base, exponent)
    assert np.allclose(result.value, np.array([2, 4, 8]))

    # vector base and scalar exponent
    base = cp.Parameter(shape=(3,), value=np.array([1, 2, 3]))
    exponent = cp.Parameter(shape=(1,), value=np.array([2]))
    result = power(base, exponent)
    assert np.allclose(result.value, np.array([1, 4, 9]))

    # vector base and exponent
    base = cp.Parameter(shape=(1, 3), value=np.array([[1, 2, 3]]))
    exponent = cp.Parameter(shape=(1, 3), value=np.array([[1, 2, 3]]))
    result = power(base, exponent)
    assert np.allclose(result.value, np.array([1, 4, 27]))

    # mismatched shapes
    base = cp.Parameter(shape=(1, 3), value=np.array([[1, 2, 3]]))
    exponent = cp.Parameter(shape=(1, 2), value=np.array([[1, 2]]))
    with pytest.raises(ValueError):
        power(base, exponent)


def test_matrix_inverse():
    """
    Test the matrix_inverse function.
    This function tests the matrix_inverse function with valid and invalid 
    input, and checks if the function correctly calculates the inverse of a 
    matrix and handles invalid input.
    """

    # valid input
    matrix = cp.Parameter((2, 2), value=np.array([[4, 7], [2, 6]]))
    inverse = matrix_inverse(matrix)
    expected_inverse = np.array([[0.6, -0.7], [-0.2, 0.4]])
    assert np.allclose(inverse.value, expected_inverse)

    # invalid input
    with pytest.raises(TypeError):
        matrix_inverse('not a cvxpy Parameter or Expression')

    with pytest.raises(ValueError):
        matrix_inverse(cp.Parameter((2, 2)))

    with pytest.raises(ValueError):
        matrix_inverse(cp.Parameter((2,), value=np.array([1, 2])))

    with pytest.raises(ValueError):
        matrix_inverse(
            cp.Parameter((2, 3), value=np.array([[1, 2, 3], [4, 5, 6]])))

    with pytest.raises(ValueError):
        matrix_inverse(
            cp.Parameter((2, 2), value=np.array([[1, 2], [2, 4]])))


def test_weibull_distribution():
    """
    Test the weibull_distribution function.
    This function tests the weibull_distribution function with valid and 
    invalid input, and checks if the function correctly calculates the Weibull 
    PDF and handles invalid input.
    """

    scale_param = cp.Parameter(shape=(1, 1), value=np.array([[1.5]]))
    shape_param = cp.Parameter(shape=(1, 1), value=np.array([[2.0]]))
    range_vals = cp.Constant(value=np.array([[0, 1, 2, 3, 4, 5]]).T)

    # valid input for mono-dimensional Weibull PDF
    weib_dist = weibull_distribution(
        scale_factor=scale_param,
        shape_factor=shape_param,
        range_vector=range_vals,
        dimensions=1)
    expected_output = np.array([[0.62, 0.33, 0.05, 0., 0., 0.]]).T
    assert np.allclose(weib_dist.value, expected_output, atol=0.01)

    # valid input bi-dimensional Weibull PDF
    weib_dist = weibull_distribution(
        scale_factor=scale_param,
        shape_factor=shape_param,
        range_vector=range_vals,
        dimensions=2)
    expected_output = np.array([
        [0.62, 0., 0., 0., 0., 0.],
        [0.33, 0.62, 0., 0., 0., 0.],
        [0.05, 0.33, 0.62, 0., 0., 0.],
        [0., 0.05, 0.33, 0.62, 0., 0.],
        [0., 0., 0.05, 0.33, 0.62, 0.],
        [0., 0., 0., 0.05, 0.33, 0.62]
    ])
    assert np.allclose(weib_dist.value, expected_output, atol=0.01)

    # invalid input
    with pytest.raises(TypeError):
        weibull_distribution('not cvxpy parameter', shape_param, range_vals, 1)

    with pytest.raises(TypeError):
        weibull_distribution(scale_param, 'not cvxpy parameter', range_vals, 1)

    with pytest.raises(TypeError):
        weibull_distribution(scale_param, shape_param, 'not cvxpy constant', 1)

    with pytest.raises(ValueError):
        scale_param = cp.Parameter(shape=(1, 2), value=np.array([[1.5, 2.]]))
        weibull_distribution(scale_param, shape_param, range_vals, 1)

    with pytest.raises(ValueError):
        shape_param = cp.Parameter(shape=(1, 2), value=np.array([[2., 3.]]))
        weibull_distribution(scale_param, shape_param, range_vals, 1)

    with pytest.raises(ValueError):
        weibull_distribution(scale_param, shape_param, range_vals, 3)
