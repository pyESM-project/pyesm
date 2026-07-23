"""Module with allowed functions to be used as symbolic operators.

This module provides various built-in utility functions that are defined to support 
calculations in symbolic problems, ranging from simple operations like transposition 
and diagonal extraction to more complex operations such as generating special matrices, 
reshaping arrays, or any special numerical manipulation that can be hardly defined
based on symbolic expressions.

Functions are registered as operators in Constants class, and can be directly
used in defining symbolic problem expressions simply by writing its name followed 
by parentheses containing the required arguments (defined as problems variables).
"""
from typing import Optional

from scipy.sparse import issparse
import numpy as np
import cvxpy as cp

_OPERATORS_REGISTRY = {}


def operator(name: str):
    """Decorator to register a symbolic operator function.

    Args:
        name (str): The name of the operator to register.

    Returns:
        callable: The decorated function.
    """
    def decorator(func: callable) -> callable:
        _OPERATORS_REGISTRY[name] = func
        return func
    return decorator


@operator('tran')
def transposition(x):
    """Transpose a matrix or vector.

    Args:
        x (cp.Parameter | cp.Expression): The matrix or vector to transpose.

    Returns:
        cp.Parameter | cp.Expression: The transposed matrix or vector.
    """
    return cp.transpose(x)


@operator('diag')
def diagonal(x):
    """Extract the diagonal of a matrix or create a diagonal matrix from a vector.

    If x is a matrix, extracts its diagonal as a vector.
    If x is a vector, creates a diagonal matrix with x on the diagonal.

    Args:
        x (cp.Parameter | cp.Expression): A matrix (to extract diagonal) or 
            vector (to create diagonal matrix).

    Returns:
        cp.Parameter | cp.Expression: A vector containing the diagonal elements 
            (if x is a matrix) or a diagonal matrix (if x is a vector).
    """
    return cp.diag(x)


@operator('sum')
def summation(x, axis=None, keepdims=True):
    """Sum elements of a matrix or vector along a specified axis.

    Args:
        x (cp.Parameter | cp.Expression): The matrix or vector to sum.
        axis (Optional[int]): The axis along which to sum. If None, sums all 
            elements. If 0, sums along columns. If 1, sums along rows.
        keepdims (bool): Whether to keep the reduced dimensions in the result.
            default is True.

    Returns:
        cp.Parameter | cp.Expression: The sum of elements along the specified 
            axis, or a scalar if axis is None.
    """
    return cp.sum(x, axis=axis, keepdims=keepdims)


@operator('mult')
def multiplication(x, y):
    """Element-wise multiplication of two matrices or vectors.

    Performs element-wise (Hadamard) multiplication between x and y.

    Args:
        x (cp.Parameter | cp.Expression): The first matrix or vector.
        y (cp.Parameter | cp.Expression): The second matrix or vector.
            Must have the same shape as x.

    Returns:
        cp.Parameter | cp.Expression: A matrix or vector containing the 
            element-wise product of x and y.
    """
    return cp.multiply(x, y)


@operator('Minimize')
def minimize(x):
    """Create a minimization objective.

    Args:
        x (cp.Expression): The scalar expression to minimize.

    Returns:
        cp.Minimize: A cvxpy Minimize objective function.
    """
    return cp.Minimize(x)


@operator('Maximize')
def maximize(x):
    """Create a maximization objective.

    Args:
        x (cp.Expression): The scalar expression to maximize.

    Returns:
        cp.Maximize: A cvxpy Maximize objective function.
    """
    return cp.Maximize(x)


@operator('pow')
def power(
        base: cp.Parameter | cp.Expression,
        exponent: cp.Parameter | cp.Expression,
) -> cp.Parameter:
    """Calculate the element-wise power of a matrix or scalar.

    This funciton calculates the element-wise power of the base, provided an 
    exponent. Either base or exponent can be a scalar.

    Args:
        base (cp.Parameter | cp.Expression): The base for the power operation. 
            The corresponding value can be a scalar or a 1-D numpy array.
        exponent (cp.Parameter | cp.Expression): The exponent for the power 
            operation. The corresponding value can be a scalar or a 1-D numpy array.

    Returns:
        cp.Parameter: A new parameter with the same shape as the input parameters, 
            containing the result of the power operation.

    Raises:
        TypeError: If the base and exponent are not both instances of cvxpy 
            Parameter or Expression.
        ValueError: If the base and exponent do not have the same shape and 
            neither is a scalar. If the base and exponent are not numpy arrays.
            If the base and exponent include non-numeric values.
    """
    if not isinstance(base, cp.Parameter | cp.Expression) or \
            not isinstance(exponent, cp.Parameter | cp.Expression):
        raise TypeError(
            "Arguments of power method must be cvxpy Parameter or Expression.")

    if base.shape != exponent.shape:
        if base.is_scalar() or exponent.is_scalar():
            pass
        else:
            raise ValueError(
                "Base and exponent must have the same shape. In case of "
                "different shapes, one must be a scalar. "
                f"Shapes -> base: {base.shape}, exponent: {exponent.shape}.")

    base_val: np.ndarray = base.value
    exponent_val: np.ndarray = exponent.value

    if not isinstance(base.value, np.ndarray) or \
            not isinstance(exponent.value, np.ndarray):
        raise ValueError("Base and exponent must be numpy arrays.")

    if not (
        np.issubdtype(base.value.dtype, np.number) and
        np.issubdtype(exponent.value.dtype, np.number)
    ):
        raise ValueError("Base and exponent must be numeric.")

    power_value = np.power(base_val, exponent_val)
    return cp.Parameter(shape=power_value.shape, value=power_value)


@operator('minv')
def matrix_inverse(matrix: cp.Parameter | cp.Expression) -> cp.Parameter:
    """Calculate the inverse of a matrix.

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

    matrix_val = matrix.value

    if matrix_val is None:
        raise ValueError("Passed matrix values cannot be None.")

    if not isinstance(matrix_val, np.ndarray) and not issparse(matrix_val):
        raise TypeError(
            "Type expected: numpy array or scipy sparse array. "
            f"Passed type: {type(matrix_val)}.")

    if len(matrix_val.shape) != 2:
        raise ValueError(
            "Passed item is not a 2-dimensional array: passed shape: "
            f"{matrix_val.shape}.")

    if matrix_val.shape[0] != matrix_val.shape[1]:
        raise ValueError(
            "Passed item is not a square matrix: passed shape: "
            f"{matrix_val.shape}.")

    try:
        if issparse(matrix_val):
            inverse = np.linalg.inv(matrix_val.toarray())
        else:
            inverse = np.linalg.inv(matrix_val)
    except np.linalg.LinAlgError as exc:
        raise ValueError(
            "Passed matrix is singular and cannot be inverted.") from exc

    return cp.Parameter(shape=matrix_val.shape, value=inverse)


@operator('shift')
def shift(
        set_length: cp.Constant,
        shift_values: cp.Parameter,
) -> cp.Parameter:
    """Shift values of an identity matrix diagonal upwards/downwards.

    This function generates a square matrix of specified dimension, with all zeros 
    except a diagonal of ones that is shifted with respect to the main diagonal by a 
    specified shift_value. A positive shift_value results in a downward shift, 
    while a negative shift_value results in an upward shift. If shift_value is 0, 
    identity matrix is returned.

    Args:
        set_length (cp.Constant): The dimension of the matrix row/col.
        shift_values (cp.Parameter): (scalar) the number of positions to shift 
            the diagonal.

    Returns:
        cp.Parameter: A square matrix with a diagonal of ones downward shifted by 
            the specified shift_value.

    Raises:
        ValueError: If passed dimension is not greater than zero.
        TypeError: If passed dimension is not an iterable containing integers.
    """
    if not isinstance(set_length, cp.Constant) or \
            not isinstance(shift_values, cp.Parameter):
        raise TypeError(
            "Passed set_length must be a cvxpy Constant, "
            "shift_value must be a cvxpy Parameter.")

    # extract values from cvxpy parameters
    set_length: np.ndarray = set_length.value
    shift_values = shift_values.value

    # checks
    if set_length is None or shift_values is None:
        raise ValueError(
            "Values assigned to set_length and shift_value cannot be None.")

    if not isinstance(set_length, np.ndarray):
        raise TypeError(
            "Set length value must be a numpy array. Passed type: "
            f"'{type(set_length)}'.")

    if not isinstance(shift_values, np.ndarray) and not issparse(shift_values):
        raise TypeError(
            "Shift value must be numpy arrays or a scipy sparse matrix."
            f"Passed type: '{type(shift_values)}'.")

    if issparse(shift_values):
        shift_values = shift_values.toarray()

    if not set_length.size == 1:
        raise ValueError(
            "Set length must be a scalar. Passed dimension: "
            f"'{set_length.shape}'.")

    sl: int = int(set_length[0, 0])

    # case of scalar shift value
    if shift_values.size == 1:
        sv: int = int(shift_values[0, 0])
        matrix = np.eye(N=sl, k=-sv)

    # case of vector shift values
    else:
        if shift_values.size != sl:
            raise ValueError(
                "Shift values vector must have the same size as set length. "
                f"Passed shift values size: '{shift_values.size}'; "
                f"set length: '{sl}'.")

        matrix = np.zeros((sl, sl))
        shift_values = shift_values.squeeze()

        for i in range(sl):
            sv: int = int(shift_values[i])

            if sv > 0:
                # downward shift, ensuring it stays in bounds
                if i + sv < sl:
                    matrix[i + sv, i] = 1

            elif sv < 0:
                # upward shift, ensuring it stays in bounds
                if i + sv >= 0:
                    matrix[i + sv, i] = 1

            else:
                # no shift, set the diagonal to 1
                matrix[i, i] = 1

    return cp.Parameter(shape=(sl, sl), value=matrix)


@operator('annuity')
def annuity(
        period_length: cp.Parameter | cp.Constant,
        tech_lifetime: cp.Parameter,
        interest_rate: Optional[cp.Parameter] = None,
) -> cp.Parameter:
    """Calculate the annuity factor.

    This function calculate the annuity factor, used to calculate the present 
    value of an annuity for a given period length, lifetime, and interest rate, 
    which is a series of equal payments made at regular intervals.

    Args:
        period_length (cp.Parameter): The length of the period for which the
            annuity factor is calculated.
        lifetime (cp.Parameter): The total number of periods over which the
            annuity is paid.
        interest_rate (cp.Parameter): The interest rate used to discount the
            annuity payments.

    Returns:
        cp.Parameter: The annuity factor calculated based on the input parameters.

    Raises:
        TypeError: If period_length or lifetime are not cvxpy Parameters, or if
            interest_rate is provided and is not a cvxpy Parameter.
        ValueError: If the values assigned to period_length, lifetime, or
            interest_rate are None, or if period_length or lifetime are not
            scalars, or if interest_rate is not a vector of size equal to
            period_length.
    """
    if not isinstance(period_length, (cp.Parameter, cp.Constant)) or \
            not isinstance(tech_lifetime, cp.Parameter):
        raise TypeError(
            "Period length and lifetime must be cvxpy Parameters.")

    if interest_rate is not None and not isinstance(interest_rate, cp.Parameter):
        raise TypeError("Interest rate must be a cvxpy Parameter.")

    # extract and check values from period_length and lifetime cvxpy parameters
    pl: np.ndarray = period_length.value
    lt: np.ndarray = tech_lifetime.value

    if pl is None or lt is None:
        raise ValueError(
            "Values assigned to period_length and lifetime cannot be None.")

    if not len(pl) == 1:
        raise ValueError(
            f"Period length must be a scalar. Passed shape: '{pl.shape}'.")

    if not len(lt) == 1:
        raise ValueError(
            f"Lifetime must be a scalar. Passed dimension: '{len(lt)}'.")

    pl = int(pl[0][0])
    lt = int(lt[0][0])

    # extract and check values from interest_rate cvxpy parameter
    if interest_rate is not None:
        ir: np.ndarray = interest_rate.value
    else:
        ir: np.ndarray = np.zeros([1, pl])

    if not 1 in ir.shape:
        raise ValueError(
            f"Interest rate must be a vector. Passed dimension: '{len(ir)}'.")

    if ir.size != pl:
        raise ValueError(
            "Interest rate vector must have size equal to period length."
            f"Passed interest rate size: '{ir.size}'; period length: '{pl}'.")

    if ir.shape[0] != 1:
        ir = ir.T

    # calculate annuity matrix
    annuity_values = np.zeros((pl, pl))

    for row in range(pl):
        for col in range(pl):
            if col > row:
                continue
            elif (row - col) < lt:
                if ir[0, col] == 0:
                    annuity_values[row, col] = 1/lt
                else:
                    _ir = ir[0, col]
                    annuity_values[row, col] = _ir * \
                        (1 + _ir)**lt / ((1 + _ir)**lt - 1)

    return cp.Parameter(shape=(pl, pl), value=annuity_values)


@operator('weib')
def weibull_distribution(
        scale_factor: cp.Parameter,
        shape_factor: cp.Parameter,
        range_vector: cp.Parameter | cp.Constant,
        dimensions: int,
        rounding: int = 2,
) -> cp.Parameter:
    """Generate a Weibull probability density function.

    This function can be produced either as a one-dimensional vector or a 
    two-dimensional matrix, based on specified dimensions. This function 
    primarily uses parameters from 'cvxpy' to enable integration with 
    optimization tasks and 'numpy' for handling numerical operations.

    Args:
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
        cp.Parameter: A cvxpy Parameter object that contains the Weibull PDF in 
            the specified dimension (vector or matrix). This can be directly used 
            in further cvxpy optimizations.

    Raises:
        ValueError: If any of the input parameters (scale_factor, shape_factor,
            or range_vector) is None, or if their contained values do not meet 
            the expected requirements (e.g., non-scalar for scale or shape 
            factors, or if dimensions is not 1 or 2).
    """
    if not isinstance(scale_factor, cp.Parameter) or \
            not isinstance(shape_factor, cp.Parameter) or \
            not isinstance(range_vector, cp.Parameter | cp.Constant):
        raise TypeError(
            "Custom function weibull_distribution() | scale_factor and "
            "shape_factor must be cvxpy.Parameters, range_vector must be "
            "cvxpy.Constant or cvxpy.Parameter."
        )

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
    if not sc.size == 1:
        err_msg.append(
            "Weibull scale factor must be a scalar. "
            f"Passed dimension: '{sc.shape}'.")

    if not sh.size == 1:
        err_msg.append(
            "Weibull shape factor must be a scalar. "
            f"Passed dimension: '{sh.shape}'.")

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
    if weib_range <= rx.size:
        weib_range = rx.size

    rx_weib = np.arange(1, weib_range+1).reshape((weib_range, 1))

    weib_dist = sh/sc * (rx_weib/sc)**(sh-1) * np.exp(-((rx_weib/sc)**sh))
    weib_dist = np.round(weib_dist, rounding)

    # re-scale weib_dist to get the sum equal to 1
    weib_dist /= np.sum(weib_dist)

    # reshape weib_dist to match the lenght of range
    weib_dist = weib_dist[:rx.size]

    # generates a vector of Weibull probability distribution
    if dimensions == 1:
        weib_parameter = cp.Parameter(shape=(rx.size, 1))
        weib_parameter.value = weib_dist

    # generates a matrix of Weibull probability distribution
    # each column of the matrix is the original vector rolled down
    # WARNING: per implementare un lifetime che varia di anno in anno, bisogna
    # ricalcolare weib_dist ogni anno!
    elif dimensions == 2:
        weib_parameter = cp.Parameter(shape=(rx.size, rx.size))
        weib_dist_matrix = np.zeros((rx.size, rx.size))

        for i in range(rx.size):
            weib_dist_rolled = np.roll(weib_dist, i)
            weib_dist_rolled[:i] = 0
            weib_dist_matrix[:, i] = weib_dist_rolled.flatten()

        weib_parameter.value = weib_dist_matrix

    return weib_parameter


OPERATORS = _OPERATORS_REGISTRY
