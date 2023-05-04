"""Basic constants for definition of model structure"""

# basic package information
_INFO = {
    'Package name': 'pySM',
    'Description': 'Python-based general purpose Systems Modeller',
    'Version': 'v.0.1',
    'Author': 'Matteo V. Rocco'
}

# structure of the sets of the model
_SETS = {

    '_set_SCENARIOS': {
        'Symbol': 'sc',
        'Headers': {
            'ID': 'INTEGER PRIMARY KEY',
            'Name': 'TEXT',
            'Acronym': 'TEXT'
        }
    },

    '_set_SYSTEMS': {
        'Symbol': 'sy',
        'Headers': {
            'ID': 'INTEGER PRIMARY KEY',
            'Category': 'TEXT',
            'Name': 'TEXT',
            'Acronym': 'TEXT',
            'Cluster_1': 'TEXT'
        },
        'Categories': [
            'Productive system',
            'Other systems',
            'Environment'
        ],
    },

    '_set_TECHNOLOGIES': {
        'Symbol': 'tc',
        'Headers': {
            'ID': 'INTEGER PRIMARY KEY',
            'Category': 'TEXT',
            'Category_detail': 'TEXT',
            'Stock_unit': 'TEXT',
            'Name': 'TEXT',
            'Acronym': 'TEXT',
            'Cluster_1': 'TEXT'
        },
        'Categories': {
            'Supply': ['Production', 'Storage', 'Transmission'],
            'Demand': ['Demand']
        },
    },

    '_set_FLOWS': {
        'Symbol': 'fl',
        'Headers': {
            'ID': 'INTEGER PRIMARY KEY',
            'Category': 'TEXT',
            'Flow_unit': 'TEXT',
            'Name': 'TEXT',
            'Acronym': 'TEXT',
            'Cluster_1': 'TEXT'
        },
        'Categories': [
            'Product flow',
            'Production factor',
            'Environmental transaction'
        ],
    }

}

# structure of the generic case study folder
_FOLDERS = ['']
