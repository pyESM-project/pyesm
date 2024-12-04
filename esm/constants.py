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
    Centralized repository of constants grouped into meaningful categories for 
    clarity and ease of access. Supports direct attribute access of constants 
    using '__getattr__' method.

    Usage:
        Direct access:
            >>> Constants.ConfigFiles.SETUP_FILES
    """

    _SUBGROUPS = []

    class ConfigFiles:
        """Constants related to configuration and file management."""
        SETUP_INFO = {
            0: 'structure_sets',
            1: 'structure_variables',
            2: 'problem'
        }
        SETUP_XLSX_FILE = 'model_settings.xlsx'
        SETS_FILE = 'sets.xlsx'
        INPUT_DATA_DIR = 'input_data'
        INPUT_DATA_FILE = 'input_data.xlsx'
        DATA_FILES_EXTENSION = '.xlsx'
        SQLITE_DATABASE_FILE = 'database.db'
        SQLITE_DATABASE_FILE_TEST = 'database_expected.db'
        TUTORIAL_FILE_NAME = 'tutorial.ipynb'
        DEFAULT_MODELS_DIR_PATH = 'default'

    class Headers:
        """Standard headers and field names."""
        NAME_HEADER = 'name'
        FILTERS_HEADERS = 'filters'
        AGGREGATION_HEADER = 'aggregation'
        VALUES_FIELD = {'values': ['values', 'REAL']}
        ID_FIELD = {'id': ['id', 'INTEGER PRIMARY KEY']}
        CVXPY_VAR_HEADER = 'variable'
        FILTER_DICT_HEADER = 'filter'
        SUB_PROBLEM_KEY_HEADER = 'sub_problem_key'
        PROBLEM_HEADER = 'problem'
        PROBLEM_INFO_HEADER = 'info'
        PROBLEM_STATUS_HEADER = 'status'
        OBJECTIVE_HEADER = 'objective'
        CONSTRAINTS_HEADER = 'expressions'

    class DefaultStructures:
        """Default structures for data validation."""
        OPTIONAL = object()

        SET_STRUCTURE = {
            'symbol': str,
            'table_name': str,
            'split_problem': (OPTIONAL, bool),
            'copy_from': (OPTIONAL, str),
            'table_structure': {
                'name': [str, str],
                'aggregation': (OPTIONAL, [str, str]),
                'filters': (OPTIONAL, {
                    str | int: {
                        'headers': [str, str],
                        'values': [str | int | bool, str],
                    }
                })
            }
        }
        DATA_TABLE_STRUCTURE = {
            'name': str,
            'type': str | dict[int | str, str],
            'integer': bool,
            'coordinates': list[str],
            'variables_info': {
                str: {
                    'value': str,
                    'dim': str,
                    'filters': dict[str | int, str | int | bool]
                }
            }
        }

    class SymbolicDefinitions:
        """Allowed constants and operators for symbolic problem definitions."""
        ALLOWED_VARIABLES_TYPES = ['constant', 'exogenous', 'endogenous']
        REGEX_PATTERN = r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'
        ALLOWED_CONSTANTS = {
            'sum_vector': (np.ones, {}),
            'identity': (np.eye, {}),
            'set_length': (np.size, {}),
            'arange_1': (util_functions.arange, {}),
            'arange_0': (util_functions.arange, {'start_from': 0}),
            'lower_triangular': (util_functions.tril, {}),
            'identity_rcot': (util_functions.identity_rcot, {}),
        }
        ALLOWED_OPERATORS = {
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
            'shift': util_functions.shift,
            'pow': util_functions.power,
            'minv': util_functions.matrix_inverse,
            'weib': util_functions.weibull_distribution,
            'Minimize': cp.Minimize,
            'Maximize': cp.Maximize,
        }

    class NumericalSettings:
        """Settings for numerical solvers and tolerances."""
        ALLOWED_VALUES_TYPES = (int, float)
        STD_VALUES_TYPE = float
        DB_EMPTY_DATA_FILL = 0
        ALLOWED_SOLVERS = cp.installed_solvers()
        DEFAULT_SOLVER = 'GUROBI'
        TOLERANCE_TESTS_RESULTS_CHECK = 0.02
        TOLERANCE_MODEL_COUPLING_CONVERGENCE = 0.01
        MAXIMUM_ITERATIONS_MODEL_COUPLING = 20
        ROUNDING_DIGITS_RELATIVE_DIFFERENCE_DB = 5

    _SUBGROUPS = [
        ConfigFiles,
        Headers,
        DefaultStructures,
        SymbolicDefinitions,
        NumericalSettings
    ]

    @classmethod
    def __getattr__(cls, name):
        """
        Provides direct access to constants by searching nested groups.

        Args:
            name (str): The name of the attribute to retrieve.

        Returns:
            Any: The requested constant or attribute.

        Raises:
            AttributeError: If the attribute is not found.
        """
        for subgroup in cls._SUBGROUPS:
            if hasattr(subgroup, name):
                return getattr(subgroup, name)
        raise AttributeError(
            f"Constant or group '{name}' not found in {cls.__name__}.")
