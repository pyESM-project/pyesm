# essenstial model config files
_SETUP_FILES = {
    'settings': 'settings.yml',
    'variables': 'variables.yml',
    'problem': 'problem.yml',
    'sets_structure': 'sets_structure.yml',
}

# definition of standard column name-type for sets id and values fields
_STD_VALUES_FIELD = {'values': ['values', 'REAL']}
_STD_ID_FIELD = {'id': ['id', 'INTEGER PRIMARY KEY']}
_STD_TABLE_HEADER_KEY = 'name'

# definition of standard headers for variables dataframe
_CVXPY_VAR_HEADER = 'variable'
_FILTER_DICT_HEADER = 'filter'

# definition of standard headers for problem dataframe
_OBJECTIVE_HEADER = 'objective function'
_CONSTRAINTS_HEADER = 'constraints'
_PROBLEM_HEADER = 'problem'
_PROBLEM_INFO_HEADER = 'info'

# definition of allowed operators for defining symbolic problem
_ALLOWED_OPERATORS = {
    '+': '+',
    '-': '-',
    '*': '*',
    '@': '@',
    '==': '==',
}
