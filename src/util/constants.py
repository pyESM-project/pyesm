"""Basic constants for definition of model structure"""

# basic package information
INFO = {
    'Package name': 'pySM',
    'Description': 'Python-based general purpose Systems Modeller',
    'Version': 'v.0.1',
    'Author': 'Matteo V. Rocco'
}

# index of constants dictionaries
_INDEX_HEADERS = {
    'id': ['ID', 'INTEGER PRIMARY KEY'],
    'name': ['Name', 'TEXT'],
    'acronym': ['Acronym', 'TEXT'],
    'stock_unit': ['Stock_unit', 'TEXT'],
    'flow_unit': ['Flow_unit', 'TEXT'],
    'category': ['Category', 'TEXT'],
    'cluster_1': ['Cluster_1', 'TEXT']
}

# structure of the sets of the model
_SETS = {

    'technologies': {
        'symbol': 't',
        'table_name': '_set_TECHNOLOGIES',
        'table_headers': {
            key: _INDEX_HEADERS[key] for key in [
                'name', 'acronym', 'category',
            ]
        },
        'categories': {
            't.p': 'Production technology',
            't.d': 'Demand technology',
        }
    },

    'flows': {
        'symbol': 'f',
        'table_name': '_set_FLOWS',
        'table_headers': {
            key: _INDEX_HEADERS[key] for key in [
                'name', 'acronym', 'category',
            ]
        },
        'categories': {
            'f.p': 'Product flow',
            'f.e': 'Environmental flow',
        }
    }
}

# structure of the generic case study folder
_FOLDERS = ['']


#
_INDEX_VARS = {
    0: 'name',
    1: 'rows',
    2: 'columns',
    3: 'type',
    4: 'description'
}

# definition of model variables
_VARIABLES = {
    'I_ft': {}
}
