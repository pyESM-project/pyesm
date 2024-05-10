""" 
constants.py

@author: Matteo V. Rocco
@institution: Politecnico di Milano

This module collects all the fundamental constants of the package, necessary 
for simplifying renaming package labels and for validation purposes.
The module also collects allowed operators and constants labels necessary for 
defining symbolic problem.
To avoid direct access and eventual unexpected modification of protected items 
may occur in other modules, constants are defined as class variables of the 
Constants class, accessible through the 'get' getter method.
"""

import cvxpy as cp
import numpy as np

from esm.support import util_functions


class Constants:
    """
    A centralized repository of constants used throughout the package for various 
    purposes, including configuration file management, symbolic problem definition, 
    and data structure validation. The class prevents direct modification and 
    unintended use of internal constants by exposing a single, controlled access 
    point through a class method.

    This class encapsulates essential model configuration files, default headers, 
    and allowed constants and operators necessary for defining symbolic problems 
    using CVXPY. The constants are stored as protected class attributes to discourage
    direct access.

    Attributes:
        _SETUP_FILES (dict): Essential model configuration files.
        _TUTORIAL_FILE_NAME (str): Default tutorial file name.
        _DEFAULT_MODELS_DIR_PATH (str): directory path for default models.
        _DEFAULT_MODELS_LIST (list): List of default models.
        _STD_NAME_HEADER (str): Standard header for the 'name' field in data tables.
        _STD_FILTERS_HEADERS (str): Standard header for the 'filters' field in data tables.
        _STD_AGGREGATION_HEADER (str): Standard header for the 'aggregation' field in data tables.
        _STD_VALUES_FIELD (dict): Default column name-type for 'values' field in sets.
        _STD_ID_FIELD (dict): Default column name-type for 'id' field in sets.
        _CVXPY_VAR_HEADER (str): Default header for variables in a dataframe.
        _FILTER_DICT_HEADER (str): Default header for filters in a dataframe.
        _OBJECTIVE_HEADER (str): Header for the objective function in problem definitions.
        _CONSTRAINTS_HEADER (str): Header for constraints in problem definitions.
        _PROBLEM_HEADER (str): Header for identifying problems in data structures.
        _PROBLEM_INFO_HEADER (str): Header for additional information about problems.
        _PROBLEM_STATUS_HEADER (str): Header for the status of problems.
        _SET_DEFAULT_STRUCTURE (dict): Default structure for validation of set information.
        _DATA_TABLE_DEFAULT_STRUCTURE (dict): Default structure for data tables.
        _VARIABLE_DEFAULT_STRUCTURE (dict): Default structure for variables.
        _ALLOWED_CONSTANTS (dict): Allowed constants for use in symbolic problem definitions.
        _ALLOWED_OPERATORS (dict): Allowed operators for defining symbolic CVXPY problems.

    Methods:
        get(constant_name: str): Retrieves the value of a constant by name, 
            ensuring safe, read-only access to class-defined constants.

    Usage:
        To retrieve a constant, call the `get` method with the name of the 
        constant as an argument. For example, to get the list of default models, use:
        >>> Constants.get('_DEFAULT_MODELS_LIST')

    Raises:
        AttributeError: If the specified constant name does not exist within the class.
    """

    _SETUP_FILES = {
        0: 'structure_sets.yml',
        1: 'structure_variables.yml',
        2: 'problem.yml',
    }

    _TUTORIAL_FILE_NAME = 'tutorial.ipynb'

    _DEFAULT_MODELS_DIR_PATH = 'default'
    _DEFAULT_MODELS_LIST = [
        '1_sut_multi_year',
        '2_sut_multi_year_rcot',
        '3_sut_multi_year_rcot_cap',
        '4_sut_multi_year_rcot_cap_dis',
    ]

    _STD_NAME_HEADER = 'name'
    _STD_FILTERS_HEADERS = 'filters'
    _STD_AGGREGATION_HEADER = 'aggregation'

    _STD_VALUES_FIELD = {'values': ['values', 'REAL']}
    _STD_ID_FIELD = {'id': ['id', 'INTEGER PRIMARY KEY']}

    _CVXPY_VAR_HEADER = 'variable'
    _FILTER_DICT_HEADER = 'filter'

    _OBJECTIVE_HEADER = 'objective function'
    _CONSTRAINTS_HEADER = 'expressions'
    _PROBLEM_HEADER = 'problem'
    _PROBLEM_INFO_HEADER = 'info'
    _PROBLEM_STATUS_HEADER = 'status'

    _SET_DEFAULT_STRUCTURE = {
        'symbol': str,
        'table_name': str,
        'split_problem': bool,
        'copy_from': str,
        'table_structure': dict,
    }

    _DATA_TABLE_DEFAULT_STRUCTURE = {
        'name': str,
        'type': str,
        'coordinates': list,
        'variables_info': dict,
    }
    _VARIABLE_DEFAULT_STRUCTURE = {
        'intra': dict,
        'rows': dict,
        'cols': dict,
        'value': str,
    }

    _ALLOWED_CONSTANTS = {
        'sum_vector': (np.ones, ),  # vector of 1s
        'identity': (np.eye, ),  # identity matrix
        # vector/matrix with a range from 1 up to dimension size
        'arange': (util_functions.arange, ),
        # lower triangular matrix of 1s(inc. diagonal)
        'lower_triangular': (util_functions.tril, ),
        # special identity matrix for rcot problems
        'identity_rcot': (util_functions.identity_rcot, ),
    }

    _ALLOWED_OPERATORS = {
        '+': '+',
        '-': '-',
        '*': '*',
        '@': '@',
        '==': '==',
        '>=': '>=',
        '<=': '<=',
        '(': '(',
        ')': ')',
        ',': ',',
        'tran': cp.transpose,
        'diag': cp.diag,
        'sum': cp.sum,
        'mult': cp.multiply,
        'minv': util_functions.matrix_inverse,
        'weib': util_functions.weibull_distribution,
        'Minimize': cp.Minimize,
    }

    @classmethod
    def get(cls, constant_name):
        """
        Generic getter method to access constants.

        Args:
            constant_name (str): The name of the constant to retrieve.

        Returns:
            The value of the constant.

        Raises:
            AttributeError: If the constant is not found.
        """
        try:
            return getattr(cls, constant_name)
        except AttributeError as e:
            raise AttributeError(
                f"Constant '{constant_name}' not found.") from e
