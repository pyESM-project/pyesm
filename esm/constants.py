import cvxpy as cp
import numpy as np

from esm.support import util_constants

# essenstial model config files
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

# headers for table related to sets and data
_STD_NAME_HEADER = 'name'
_STD_FILTERS_HEADERS = 'filters'
_STD_AGGREGATION_HEADER = 'aggregation'

# default column name-type for sets id and values fields
_STD_VALUES_FIELD = {'values': ['values', 'REAL']}
_STD_ID_FIELD = {'id': ['id', 'INTEGER PRIMARY KEY']}

# default headers for variables dataframe
_CVXPY_VAR_HEADER = 'variable'
_FILTER_DICT_HEADER = 'filter'

# default headers for problem dataframe
_OBJECTIVE_HEADER = 'objective function'
_CONSTRAINTS_HEADER = 'expressions'
_PROBLEM_HEADER = 'problem'
_PROBLEM_INFO_HEADER = 'info'
_PROBLEM_STATUS_HEADER = 'status'

# default Set info structure (for validation purpose)
_SET_DEFAULT_STRUCTURE = {
    'symbol': str,
    'table_name': str,
    'split_problem': bool,
    'table_structure': dict,
}

# default DataTable and Variable structures (for validation purpose)
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

# allowed constants. more can be added, but Variable.define_constant must
# be modified accordingly
_ALLOWED_CONSTANTS = {
    'sum_vector': (np.ones, ),  # vector of 1s
    'identity': (np.eye, ),  # identity matrix
    # lower triangular matrix of 1s(inc. diagonal)
    'lower_triangular': (util_constants.tril, ),
    # special identity matrix for rcot problems
    'identity_rcot': (util_constants.identity_rcot, ),
    # 'range_vector': (np.arange, ),  # vector given a range TBD
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
    'tweib': util_constants.tril_weibull,
    'vweib': util_constants.vect_weibull,
    'Minimize': cp.Minimize,
}
