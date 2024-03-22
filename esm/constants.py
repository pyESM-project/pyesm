import cvxpy as cp
import numpy as np

from esm.support import util_constants

# essenstial model config files
_SETUP_FILES = {
    0: 'structure_sets.yml',
    1: 'structure_variables.yml',
    2: 'problem.yml',
}

# available template models to be replicated and customized
_TEMPLATE_MODELS = {
    '1_sut': 'standard SUT, primal, industry/product-based',
    '2_multi_year': 'SUT model, multi-year, rcot, primal problem, industry-based'
}

# headers for table related to sets and data
_STD_TABLE_HEADER = 'name'
_STD_CATEGORY_HEADER = 'category'

# default column name-type for sets id and values fields
_STD_VALUES_FIELD = {'values': ['values', 'REAL']}
_STD_ID_FIELD = {'id': ['id', 'INTEGER PRIMARY KEY']}

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

# default DataTable and Variable structures (for validation purpose)
_DATA_TABLE_DEFAULT_STRUCTURE = {
    'name': str,
    'type': str,
    'coordinates': list,
    'variables_info': dict,
}
_VARIABLE_DEFAULT_STRUCTURE = {
    'rows': dict,
    'cols': dict,
    'value': str
}

# allowed constants. more can be added, but Variable.define_constant must
# be modified accordingly
_ALLOWED_CONSTANTS = {
    'sum_vector': (np.ones, ),  # vector of 1s
    'identity': (np.eye, ),  # itentity matrix
    # lower triangular matrix of 1s(inc. diagonal)
    'lower_triangular': (util_constants.tril, ),
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
    'tran': cp.transpose,
    'diag': cp.diag,
    'sum': cp.sum,
    'mult': cp.multiply,
    'Minimize': cp.Minimize,
}
