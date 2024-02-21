import cvxpy as cp

# essenstial model config files
_SETUP_FILES = {
    'settings': 'settings.yml',
    'variables': 'variables.yml',
    'problem': 'problem.yml',
    'sets_structure': 'sets_structure.yml',
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
    'sum': cp.sum,
    'Minimize': cp.Minimize,
}
