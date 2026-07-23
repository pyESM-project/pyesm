"""
test_util_operators.py

This module contains tests for the functions in the 'cvxlab.support.util_operators'
module.
"""
import numpy as np
import cvxpy as cp

from tests.unit.conftest import run_test_cases

from cvxlab.support.util_operators import (
    power,
    matrix_inverse,
    shift,
    weibull_distribution,
)


def test_power():

    base = {
        0: cp.Parameter(shape=(1,), value=np.array([2])),
        1: cp.Parameter(shape=(1,), value=np.array([2])),
        2: cp.Parameter(shape=(1, 3), value=np.array([[1, 2, 3]])),
        3: cp.Parameter(shape=(1, 3), value=np.array([[1, 2, 3]])),
        4: cp.Parameter(shape=(1, 3), value=np.array([[1, 2, 3]])),
    }

    exponent = {
        0: cp.Parameter(shape=(1,), value=np.array([3])),
        1: cp.Parameter(shape=(3,), value=np.array([1, 2, 3])),
        2: cp.Parameter(shape=(1,), value=np.array([2])),
        3: cp.Parameter(shape=(1, 3), value=np.array([[1, 2, 3]])),
        4: cp.Parameter(shape=(1, 2), value=np.array([[1, 2]])),
    }

    test_cases = [
        # scalar base and scalar exponent
        ((base[0], exponent[0]), np.array([8]), None),
        # scalar base and vector exponent
        ((base[1], exponent[1]), np.array([2, 4, 8]), None),
        # vector base and scalar exponent
        ((base[2], exponent[2]), np.array([1, 4, 9]), None),
        # vector base and vector exponent
        ((base[3], exponent[3]), np.array([[1, 4, 27]]), None),
        # mismatched shapes
        ((base[4], exponent[4]), None, ValueError),
    ]

    run_test_cases(power, test_cases, tolerance=True)


# def test_matrix_inverse():
#     """
#     Test the matrix_inverse function.
#     This function tests the matrix_inverse function with valid and invalid
#     input, and checks if the function correctly calculates the inverse of a
#     matrix and handles invalid input.
#     """

#     arguments = {
#         0: cp.Parameter((2, 2), value=np.array([[4, 7], [2, 6]])),
#         # invalid input type
#         1: 'text',
#         # no value set
#         2: cp.Parameter((2, 2)),
#         # not square
#         3: cp.Parameter((2,), value=np.array([1, 2])),
#         # not square
#         4: cp.Parameter((2, 3), value=np.array([[1, 2, 3], [4, 5, 6]])),
#         # singular matrix
#         5: cp.Parameter((2, 2), value=np.array([[1, 2], [2, 4]])),
#     }

#     test_cases = [
#         (arguments[0], np.array([[0.6, -0.7], [-0.2, 0.4]]), None),
#         (arguments[1], None, TypeError),
#         (arguments[2], None, ValueError),
#         (arguments[3], None, ValueError),
#         (arguments[4], None, ValueError),
#         (arguments[5], None, ValueError),

#     ]

#     run_test_cases(matrix_inverse, test_cases, tolerance=True)


def test_shift():

    set_length = {
        0: 1,
        1: cp.Constant(value=np.array([[2]])),
        2: cp.Constant(value=np.array([[10]])),
        3: cp.Constant(value=np.array([[10]])),
        4: cp.Constant(value=np.array([[10]])),
        5: cp.Constant(value=np.array([[5]])),
        6: cp.Constant(value=np.array([[5]])),
        7: cp.Constant(value=np.array([[5]])),
    }

    shift_values = {
        0: 1,
        1: cp.Parameter(shape=(1, 3), value=np.array([[1, 2, 3]])),
        2: cp.Parameter(shape=(1, 1), value=np.array([[0]])),
        3: cp.Parameter(shape=(1, 1), value=np.array([[-2]])),
        4: cp.Parameter(shape=(1, 1), value=np.array([[5]])),
        5: cp.Parameter(shape=(1, 5), value=np.array([[0, -1, 2, 0, -2]])),
        6: cp.Parameter(shape=(1, 5), value=np.array([[1, 1, 1, 1, 1]])),
        7: cp.Parameter(shape=(1, 5), value=np.array([[-1, -1, -1, -1, -1]])),
    }

    expected_results = {
        5: np.array([
            [1, 1, 0, 0, 0],  # col 0: no shift
            [0, 0, 0, 0, 0],  # col 1: shift up (-1) → appears at row 0
            [0, 0, 0, 0, 1],  # col 2: shift down (2) → appears at row 4
            [0, 0, 0, 1, 0],  # col 3: no shift
            [0, 0, 1, 0, 0],  # col 4: shift up (-2) → appears at column 2
        ]),
        6: np.array([
            [0, 0, 0, 0, 0],   # Main diagonal shifted down by 1
            [1, 0, 0, 0, 0],
            [0, 1, 0, 0, 0],
            [0, 0, 1, 0, 0],
            [0, 0, 0, 1, 0],
        ]),
        7: np.array([
            [0, 1, 0, 0, 0],   # Main diagonal shifted up by 1
            [0, 0, 1, 0, 0],
            [0, 0, 0, 1, 0],
            [0, 0, 0, 0, 1],
            [0, 0, 0, 0, 0],
        ]),
    }

    test_cases = [
        # invalid arguments types
        ((set_length[0], shift_values[0]), None, TypeError),
        # invalid arguments shapes
        ((set_length[1], shift_values[1]), None, ValueError),
        # valid scalar shifts
        ((set_length[2], shift_values[2]), np.eye(10, k=0), None),
        ((set_length[3], shift_values[3]), np.eye(10, k=2), None),
        ((set_length[4], shift_values[4]), np.eye(10, k=-5), None),
        # valid vector shifts
        ((set_length[5], shift_values[5]), expected_results[5], None),
        ((set_length[6], shift_values[6]), expected_results[6], None),
        ((set_length[7], shift_values[7]), expected_results[7], None),
    ]
    run_test_cases(shift, test_cases)


def test_weibull_distribution():
    """
    Test the weibull_distribution function.
    This function tests the weibull_distribution function with valid and 
    invalid input, and checks if the function correctly calculates the Weibull 
    PDF and handles invalid input.
    """

    scale = cp.Parameter(shape=(1, 1), value=np.array([[1.5]]))
    shape = cp.Parameter(shape=(1, 1), value=np.array([[2.0]]))
    values_range = cp.Constant(value=np.array([[0, 1, 2, 3, 4, 5]]).T)

    expected_results = {
        0: np.array([[0.62, 0.33, 0.05, 0., 0., 0.]]).T,
        1: np.array([
            [0.62, 0., 0., 0., 0., 0.],
            [0.33, 0.62, 0., 0., 0., 0.],
            [0.05, 0.33, 0.62, 0., 0., 0.],
            [0., 0.05, 0.33, 0.62, 0., 0.],
            [0., 0., 0.05, 0.33, 0.62, 0.],
            [0., 0., 0., 0.05, 0.33, 0.62]
        ])
    }

    test_cases = [
        # invalid inputs types
        (('scale', shape, 'range', 1), None, TypeError),
        ((scale, 'shape', values_range, 1), None, TypeError),
        ((scale, shape, 'range', 1), None, TypeError),
        ((scale, shape, values_range, 5), None, ValueError),
        # valid input for mono-dimensional Weibull PDF
        ((scale, shape, values_range, 1), expected_results[0], None),
        # valid input bi-dimensional Weibull PDF
        ((scale, shape, values_range, 2), expected_results[1], None),
    ]

    run_test_cases(weibull_distribution, test_cases, tolerance=0.01)
