"""Basic constants for definition of model structure"""

# basic package information
INFO = {
    'Package name': 'pyESM',
    'Description': 'Python-based general purpose Engineering Systems Modeller',
    'Version': 'v.0.1',
    'Author': 'Matteo V. Rocco'
}

# structure of the sets of the model
_SETS = {
    'scenarios': {
        'symbol': 's',
        'table_name': '_set_SCENARIOS',
        'table_headers': {
            'id': ['s_ID', 'INTEGER PRIMARY KEY'],
            'name': ['s_Name', 'TEXT'],
        },
    },
    'datetime': {
        'symbol': 'dt',
        'table_name': '_set_DATETIME',
        'table_headers': {
            'id': ['dt_ID', 'INTEGER PRIMARY KEY'],
            'name': ['dt_Name', 'TEXT'],
        },
    },
    'technologies': {
        'symbol': 't',
        'table_name': '_set_TECHNOLOGIES',
        'table_headers': {
            'id': ['t_ID', 'INTEGER PRIMARY KEY'],
            'name': ['t_Name', 'TEXT'],
            'category': ['t_Category', 'TEXT']
        },
        'set_categories': {
            't.s': 'Supply technology',
            't.d': 'Demand technology',
        },
    },
    'flows': {
        'symbol': 'f',
        'table_name': '_set_FLOWS',
        'table_headers': {
            'id': ['f_ID', 'INTEGER PRIMARY KEY'],
            'name': ['f_Name', 'TEXT'],
            'category': ['f_Category', 'TEXT'],
            'competition': ['f_Competition', 'TEXT'],
            'parent': ['f_Parent_technology', 'TEXT'],
            'unit': ['f_Unit', 'TEXT'],
        },
        'set_categories': {
            'f.p': 'Product flow',
            'f.e': 'Environmental flow',
        },
    },
}

# definition of standard column name-type for id and values fields
_STD_VALUES_FIELD = ['values', 'REAL']
_STD_ID_FIELD = ['id', 'INTEGER PRIMARY KEY']

# definition of standard hierarchy of problem variables dictionary
_VAR_DICT_HIERARCHY = ['scenarios', 'datetime']

# definition of model variables
_VARIABLES = {
    'v': {
        'symbol': 'v',
        'name': 'make coefficients matrix',
        'type': 'exogenous',
        'set_headers': 'name',
        'coordinates': {
            'scenarios': 'all',
            'datetime': 'all',
            'technologies': {'set_categories': 't.s'},
            'flows': {'set_categories': 'f.p'},
        },
        'var_dict_hierarchy': None,
        'shape': ['technologies', 'flows'],
    },
    'u': {
        'symbol': 'u',
        'name': 'use coefficients matrix',
        'type': 'exogenous',
        'set_headers': 'name',
        'coordinates': {
            'scenarios': 'all',
            'datetime': 'all',
            'flows': {
                'set_categories': 'f.p',
                'aggregation_key': 'competition',
            },
            'technologies': {'set_categories': 't.s'},
        },
        'var_dict_hierarchy': None,
        'shape': ['flows', 'technologies'],
    },
    'Y': {
        'symbol': 'Y',
        'name': 'total final demand matrix',
        'type': 'exogenous',
        'set_headers': 'name',
        'coordinates': {
            'scenarios': 'all',
            'datetime': 'all',
            'flows': {
                'set_categories': 'f.p',
                'aggregation_key': 'competition',
            },
            'technologies': {'set_categories': 't.d'},
        },
        'var_dict_hierarchy': None,
        'shape': ['flows', 'technologies'],
    },
    'Q': {
        'symbol': 'Q',
        'name': 'total flows demand vector',
        'type': 'endogenous',
        'set_headers': 'name',
        'coordinates': {
            'scenarios': 'all',
            'datetime': 'all',
            'flows': {
                'set_categories': 'f.p',
                'aggregation_key': 'competition',
            }
        },
        'var_dict_hierarchy': None,
        'shape': ['flows', 1],
    },
    'X': {
        'symbol': 'X',
        'name': 'total technology activity vector',
        'type': 'endogenous',
        'set_headers': 'name',
        'coordinates': {
            'scenarios': 'all',
            'datetime': 'all',
            'technologies': {
                'set_categories': 't.s',
            }
        },
        'var_dict_hierarchy': None,
        'shape': ['technologies', 1],
    },
}
