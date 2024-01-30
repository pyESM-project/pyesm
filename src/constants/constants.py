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

# definition of standard items for problem variables dictionary
_CVXPY_VAR_HEADER = 'variable'
_FILTER_DICT_HEADER = 'filter'
