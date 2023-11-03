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
        'variables_shape': False
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
        'variables_shape': True,
    },
    'flows': {
        'symbol': 'f',
        'table_name': '_set_FLOWS',
        'table_headers': {
            'id': ['f_ID', 'INTEGER PRIMARY KEY'],
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
        'shape': {
            'rows': {'set': 'technologies', 'set_category': 't.s'},
            'cols': {'set': 'flows', 'set_category': 'f.p'},
        },
    },
    'u': {
        'symbol': 'u',
        'name': 'use coefficients matrix',
        'type': 'exogenous',
        'shape': {
            'rows': {'set': 'flows', 'set_category': 'f.p'},
            'cols': {'set': 'technologies', 'set_category': 't.s'},
        },
    },
    'Y': {
        'symbol': 'Y',
        'name': 'total final demand matrix',
        'type': 'exogenous',
        'shape': {
            'rows': {'set': 'flows', 'set_category': 'f.p'},
            'cols': {'set': 'technologies', 'set_category': 't.d'},
        },
    },
}
