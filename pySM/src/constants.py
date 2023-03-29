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
    'SCENARIOS': {
        'Symbol': 'sc',
        'Headers': [
            'ID',
            'Name',
            'Acronym'
        ]
    },
    'SYSTEMS': {
        'Symbol': 'sy',
        'Headers': [
            'ID',
            'Category',
            'Name',
            'Acronym',
            'Cluster_1'
        ],
        'Categories': [
            'Productive system',
            'Other systems',
            'Environment'
        ],
    },
    'TECHNOLOGIES': {
        'Symbol': 'tc',
        'Headers': [
            'ID',
            'Category',
            'Category_spec',
            'Name',
            'Acronym',
            'Cluster_1'
        ],
        'Categories': {
            'Supply': ['Production', 'Storage', 'Transmission'],
            'Demand': ['Demand']
        },
    },
    'FLOWS': {
        'Symbol': 'fl',
        'Headers': [
            'ID',
            'Category',
            'Unit',
            'Name',
            'Acronym',
            'Cluster_1'
        ],
        'Categories': [
            'Product flow',
            'Production factor',
            'Environmental transaction'
        ],
    }
}

# structure of the generic case study folder
_FOLDERS = ['']
