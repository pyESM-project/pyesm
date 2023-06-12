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

_INDEX_VARS = {
    0: 'name',
    1: 'rows',
    2: 'columns',
    3: 'type',
    4: 'description'
}

# structure of the sets of the model
_SETS = {

    'scenarios': {
        'symbol': 'sc',
        'table_name': '_set_SCENARIOS',
        'table_headers': {
            key: _INDEX_HEADERS[key] for key in ['id', 'name', 'acronym']
        }
    },


    'systems': {
        'symbol': 's',
        'table_name': '_set_SYSTEMS',
        'table_headers': {
            key: _INDEX_HEADERS[key] for key in [
                'id', 'name', 'acronym', 'category', 'cluster_1'
            ]
        },
        'categories': {
            's.p': 'Productive system',
            's.o': 'Other systems',
            's.e': 'Environment',
        }
    },

    'technologies': {
        'symbol': 't',
        'table_name': '_set_TECHNOLOGIES',
        'table_headers': {
            key: _INDEX_HEADERS[key] for key in [
                'id', 'name', 'acronym', 'stock_unit', 'category', 'cluster_1'
            ]
        },
        'categories': {
            't.p': 'Production technology',
            't.s': 'Storage technology',
            't.t': 'Transmission technology',
            't.d': 'Demand technology',
        }
    },

    'flows': {
        'symbol': 'f',
        'table_name': '_set_FLOWS',
        'table_headers': {
            key: _INDEX_HEADERS[key] for key in [
                'id', 'name', 'acronym', 'flow_unit', 'category', 'cluster_1'
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


# definition of model variables
_VARIABLES = {
    'I_ft': {}
}
