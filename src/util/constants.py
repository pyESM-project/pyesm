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
            'id': ['s_ID', 'TEXT PRIMARY KEY'],
            'name': ['s_Name', 'TEXT'],
        },
        'variables_shape': False
    },
    'technologies': {
        'symbol': 't',
        'table_name': '_set_TECHNOLOGIES',
        'table_headers': {
            'id': ['t_ID', 'TEXT PRIMARY KEY'],
            'name': ['t_Name', 'TEXT'],
            'category': ['t_Category', 'TEXT']
        },
        'set_categories': {
            't.s': 'Supply technology',
            't.d': 'Demand technology',
        },
        'variables_shape': True,
    },
    'flows': {
        'symbol': 'f',
        'table_name': '_set_FLOWS',
        'table_headers': {
            'id': ['f_ID', 'TEXT PRIMARY KEY'],
            'name': ['f_Name', 'TEXT'],
            'category': ['f_Category', 'TEXT'],
            'competition': ['f_Competition', 'TEXT'],
            'parent': ['f_Parent technology', 'TEXT'],
            'unit': ['f_Unit', 'TEXT'],
        },
        'set_categories': {
            'f.p': 'Product flow',
            'f.e': 'Environmental flow',
        },
        'variables_shape': True,
    },
}

# definition of model variables
_VARIABLES = {
    'v': {
        'symbol': 'v',
        'name': 'make coefficients matrix',
        'type': 'exogenous',
        'set_headers': 'name',
        'coordinates': {
            'scenarios': 'all',
            'technologies': {'set_categories': 't.s'},
            'flows': {'set_categories': 'f.p'},
        },
    },
    'u': {
        'symbol': 'u',
        'name': 'use coefficients matrix',
        'type': 'exogenous',
        'set_headers': 'name',
        'coordinates': {
            'scenarios': 'all',
            'flows': {'set_categories': 'f.p'},
            'technologies': {'set_categories': 't.s'},
        },
    },
    'Y': {
        'symbol': 'Y',
        'name': 'total final demand matrix',
        'type': 'exogenous',
        'set_headers': 'name',
        'coordinates': {
            'scenarios': 'all',
            'flows': {'set_categories': 'f.p'},
            'technologies': {'set_categories': 't.d'},
        },
    },
}
