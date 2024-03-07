import cvxpy as cp
import numpy as np

# essenstial model config files
_SETUP_FILES = {
    'variables': 'variables.yml',
    'problem': 'problem.yml',
    'sets_structure': 'sets_structure.yml',
}

_TEMPLATE_MODELS = {
    '1_sut': 'standard SUT, primal, industry/product-based',
}

# default column name-type for sets id and values fields
_STD_VALUES_FIELD = {'values': ['values', 'REAL']}
_STD_ID_FIELD = {'id': ['id', 'INTEGER PRIMARY KEY']}
_STD_TABLE_HEADER_KEY = 'name'

# default headers for variables dataframe
_CVXPY_VAR_HEADER = 'variable'
_FILTER_DICT_HEADER = 'filter'

# default headers for problem dataframe
_OBJECTIVE_HEADER = 'objective function'
_CONSTRAINTS_HEADER = 'constraints'
_PROBLEM_HEADER = 'problem'
_PROBLEM_INFO_HEADER = 'info'
_PROBLEM_STATUS_HEADER = 'status'

# default Set info structure (for validation purpose)
_SET_DEFAULT_STRUCTURE = {
    'symbol': str,
    'table_name': str,
    'table_headers': dict,
    'set_categories': dict,
    'split_problem': bool,
}

# default Variable info structure (for validation purpose)
_VARIABLE_DEFAULT_STRUCTURE = {
    'symbol': str,
    'name': str,
    'type': str,
    'coordinates_info': dict,
    'shape': list,
    'value': str,
}

# allowed constants. more can be added, but Variable.define_constant must
# be modified accordingly
_ALLOWED_VALUES = {
    'sum_vector': (np.ones, ),  # vector of 1s
    'identity': (np.eye, ),  # itentity matrix
}

# allowed operators for defining symbolic CVXPY problem
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
    '.T': '.T',
    'diag': cp.diag,
    'sum': cp.sum,
    'Minimize': cp.Minimize,
}
